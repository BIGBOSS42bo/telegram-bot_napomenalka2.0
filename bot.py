import os
import logging
import re
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from telegram import Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

# --- НАСТРОЙКИ ---
SCHEDULER_CONFIG = {'apscheduler.jobstores.default': {'type': 'memory'}}

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
user_reminders = {}
scheduler = BackgroundScheduler(SCHEDULER_CONFIG)
scheduler.start()

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def parse_reminder(text: str):
    match = re.match(r'\s*(.+?)\s*,\s*(\d{1,2}:\d{2})\s*,\s*(\d{1,2}:\d{2}|0)\s*,\s*(\d+|inf)\s*', text)
    return match.groups() if match else None

def validate_time(time_str: str):
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

# --- КОМАНДЫ БОТА ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет! Я бот-напоминалка. Напиши мне сообщение в формате:\n`Текст, ЧЧ:ММ, ЧЧ:ММ|0, число|inf`\nИли используй /help."
    )

def help_command(update: Update, context: CallbackContext):
    help_text = """
*Доступные команды:*
/start - Начать диалог
/help - Показать это сообщение
/list - Показать список ваших напоминаний (с ID для удаления)
/del [ID] - Удалить напоминание по ID
/delall - Удалить все ваши напоминания

*Формат создания напоминания (просто напишите в чат):*
`[Текст], [Время первого (ЧЧ:ММ)], [Интервал повтора (ЧЧ:ММ или 0)], [Кол-во раз (число) или inf]`

*Пример:*
`Выйти на улицу, 3:30, 14:40, 3`
`Купить хлеб, 10:00, 1:00, inf`
"""
    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


def add_reminder(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if update.message.text.startswith('/'):
        return

    parsed = parse_reminder(update.message.text)
    
    if not parsed:
        update.message.reply_text(
            "❌ **Неверный формат.**\nИспользуйте шаблон без кавычек:\n`Текст, ЧЧ:ММ, ЧЧ:ММ|0, число|inf`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    msg, first_time_str, interval_str, count_str = parsed

    if not validate_time(first_time_str) or (interval_str != '0' and not validate_time(interval_str)):
        update.message.reply_text("❌ Ошибка в формате времени. Используйте ЧЧ:ММ.")
        return

    try:
        if count_str != 'inf':
            count = int(count_str)
            if count < 1:
                raise ValueError
    except ValueError:
        update.message.reply_text("❌ Количество повторов должно быть целым числом > 0 или 'inf'.")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    h_first, m_first = map(int, first_time_str.split(':'))
    first_target_dt = now.replace(hour=h_first, minute=m_first, second=0, microsecond=0)
    
    if first_target_dt <= now:
        first_target_dt += datetime.timedelta(days=1)
    
    count = count_str if count_str == 'inf' else int(count_str)
    
    if interval_str == '0':
        interval_seconds = 0
    else:
        h_int, m_int = map(int, interval_str.split(':'))
        interval_seconds = h_int * 3600 + m_int * 60

    def send_and_schedule(user_id_inner, msg_inner, interval_sec_inner, count_inner, prev_job_id=None):
        try:
            context.bot.send_message(chat_id=user_id_inner, text=msg_inner)
            logger.info(f"Отправлено напоминание пользователю {user_id_inner}: {msg_inner}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id_inner}: {e}")
            return

        if interval_sec_inner == 0:
            return

        if count_inner != 'inf':
            next_count = int(count_inner) - 1
            if next_count <= 0:
                return
        else:
            next_count = 'inf'
        
        next_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=interval_sec_inner)
        
        job = scheduler.add_job(
            send_and_schedule,
            'date',
            run_date=next_dt,
            args=[user_id_inner, msg_inner, interval_sec_inner, next_count, job.id]
        )
        
        if user_id_inner not in user_reminders:
            user_reminders[user_id_inner] = {}
            
        if prev_job_id and prev_job_id in user_reminders.get(user_id_inner, {}):
            del user_reminders[user_id_inner][prev_job_id]
            
        user_reminders[user_id_inner][job.id] = {'msg': msg_inner}
        
    job_first = scheduler.add_job(
        send_and_schedule,
        'date',
        run_date=first_target_dt,
        args=[user_id, msg, interval_seconds, count]
    )
    
    if user_id not in user_reminders:
         user_reminders[user_id] = {}
    user_reminders[user_id][job_first.id] = {'msg': msg}
    
    update.message.reply_text(f"✅ Напоминание добавлено:\n> {msg}\n> Первое в {first_time_str}")


def list_reminders(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not user_reminders.get(user_id):
         update.message.reply_text("📭 У вас нет активных напоминаний.")
         return

    text = "📝 *Ваши активные напоминания:*"
    
    for i, (job_id, data) in enumerate(user_reminders[user_id].items(), start=1):
         short_msg = (data['msg'][:22] + '...') if len(data['msg']) > 25 else data['msg']
         text += f"\n{i}. `{job_id}` - {short_msg}"
        
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def delete_reminder(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if len(context.args) != 1:
         update.message.reply_text("⚠️ Используйте формат: /del [ID_напоминания]. ID можно увидеть в команде /list.")
         return

    job_key = context.args[0]
    
    if not user_reminders.get(user_id) or job_key not in user_reminders[user_id]:
         update.message.reply_text("❌ Напоминание с таким ID не найдено.")
         return

    try:
         scheduler.remove_job(job_key)
         del user_reminders[user_id][job_key]
         if not user_reminders[user_id]:
             del user_reminders[user_id]
         update.message.reply_text("🗑️ Напоминание удалено.")
        
    except JobLookupError:
         update.message.reply_text("❌ Ошибка при удалении. Напоминание могло уже сработать или быть удалено.")


def delete_all(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not user_reminders.get(user_id):
         update.message.reply_text("📭 У вас нет активных напоминаний для удаления.")
         return

     # ИСПРАВЛЕННЫЙ БЛОК (ОТСТУПЫ В НОРМЕ)
     jobs_to_remove = list(user_reminders[user_id].keys())
     
     for job_key in jobs_to_remove:
         try:
             scheduler.remove_job(job_key)
             del user_reminders[user_id][job_key]
         except JobLookupError:
             continue 
     
     del user_reminders[user_id]
     update.message.reply_text("🗑️ Все напоминания удалены.")


def error_handler(update: object, context: CallbackContext):
     logger.error(msg="Exception while handling an update:", exc_info=context.error)
     
# --- ЗАПУСК БОТА ---
def main():
     token = os.environ.get('8605114997:AAG_II-LnXBlABH_M-0IryIjotplhxJab58')
     if not token:
         logger.error("Ошибка: Переменная окружения TELEGRAM_TOKEN не установлена.")
         print("Пожалуйста, установите переменную окружения TELEGRAM_TOKEN.")
         return

     updater = Updater(token)
     dispatcher = updater.dispatcher

     dispatcher.add_handler(CommandHandler("start", start))
     dispatcher.add_handler(CommandHandler("help", help_command))
     dispatcher.dispatcher.add_handler(CommandHandler("list", list_reminders))
     dispatcher.add_handler(CommandHandler("del", delete_reminder))
     dispatcher.add_handler(CommandHandler("delall", delete_all))
     
     dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_reminder))
     
     dispatcher.add_error_handler(error_handler)
     
     try:
         updater.start_polling()
         print("Бот запущен в режиме Polling.")
         
     except Exception as e:
         logger.error(f"Фатальная ошибка при запуске бота: {e}")
