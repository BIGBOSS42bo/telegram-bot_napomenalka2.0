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
# Используем MemoryJobStore, чтобы избежать проблем с записью на диск на хостингах
SCHEDULER_CONFIG = {'apscheduler.jobstores.default': {'type': 'memory'}}

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
# Словарь для хранения напоминаний: {user_id: {job_id: {'msg': str, 'count': str/int}}}
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
    """Парсит строку с напоминанием. Возвращает кортеж или None."""
    # \s* позволяет использовать пробелы в строке, например: "Выйти, 3:30, 1:00, inf"
    match = re.match(r'\s*(.+?)\s*,\s*(\d{1,2}:\d{2})\s*,\s*(\d{1,2}:\d{2}|0)\s*,\s*(\d+|inf)\s*', text)
    return match.groups() if match else None

def validate_time(time_str: str):
    """Проверяет формат времени ЧЧ:ММ."""
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
/list - Показать список ваших напоминаний
/del [номер] - Удалить напоминание по номеру (номер можно увидеть в /list)
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

    # Игнорируем команды в этом обработчике
    if update.message.text.startswith('/'):
        return

    parsed = parse_reminder(update.message.text)
    
    if not parsed:
        update.message.reply_text(
            "❌ **Неверный формат.**\nИспользуйте шаблон без кавычек:\n`Текст, ЧЧ:ММ, ЧЧ:ММ|0, число|inf`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    msg, first_time, interval, count = parsed

    if not validate_time(first_time) or (interval != '0' and not validate_time(interval)):
        update.message.reply_text("❌ Ошибка в формате времени. Используйте ЧЧ:ММ.")
        return

    if count != 'inf':
        try:
            count = int(count)
            if count < 1:
                raise ValueError
        except ValueError:
            update.message.reply_text("❌ Количество повторов должно быть целым числом > 0 или 'inf'.")
            return

    # Планируем первое напоминание на сегодня или завтра
    now = datetime.datetime.now()
    first_target_dt = now.replace(hour=int(first_time[:2]), minute=int(first_time[3:]), second=0, microsecond=0)
    if first_target_dt < now:
        first_target_dt += datetime.timedelta(days=1)
    
    first_delta = (first_target_dt - now).total_seconds()

    def send_and_schedule_inner(user_id_inner, msg_inner, interval_inner, count_inner, prev_job_id=None):
        """
        Внутренняя функция. Отправляет сообщение и планирует следующее.
        Принимает prev_job_id для удаления предыдущей записи из словаря.
        """
        # Отправляем сообщение пользователю
        try:
            context.bot.send_message(chat_id=user_id_inner, text=msg_inner)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id_inner}: {e}")
            return

        # Логика повтора
        if interval_inner == '0' or count_inner == 0 or count_inner == 'inf' and False:
            return

        # Уменьшаем счетчик повторов, если он не бесконечный
        next_count = count_inner if count_inner == 'inf' else int(count_inner) - 1

        # Если счетчик стал 0 (или был 1), выходим
        if next_count == 0:
            # Удаляем запись о предыдущем джобе из словаря пользователя
            if user_id_inner in user_reminders and prev_job_id in user_reminders[user_id_inner]:
                del user_reminders[user_id_inner][prev_job_id]
                if not user_reminders[user_id_inner]: # Если список пуст, удаляем пользователя из словаря
                    del user_reminders[user_id_inner]
            return

        # Планируем следующее напоминание ОТ ВРЕМЕНИ ТЕКУЩЕГО СРАБАТЫВАНИЯ (это важно!)
        h_int, m_int = map(int, interval_inner.split(':'))
        
        # Используем run_date относительно текущего момента выполнения функции + интервал.
        # Это гарантирует точность повтора.
        next_dt = datetime.datetime.now() + datetime.timedelta(hours=h_int, minutes=m_int)
        
        job = scheduler.add_job(
            send_and_schedule_inner,
            'date',
            run_date=next_dt,
            args=[user_id_inner, msg_inner, interval_inner, next_count, job.id] # Передаем id новой задачи как prev_job_id для будущей итерации
        )
        
        # Сохраняем ID задачи в словарь пользователя для возможности удаления через /del и /delall
        if user_id_inner not in user_reminders:
            user_reminders[user_id_inner] = {}
            
        # Удаляем старый ID (предыдущей задачи) и добавляем новый.
        # Это позволяет /del работать с актуальным ID.
        if prev_job_id and prev_job_id in user_reminders.get(user_id_inner, {}):
            del user_reminders[user_id_inner][prev_job_id]
            
        user_reminders[user_id_inner][job.id] = {'msg': msg_inner}
        
    # Планируем самую первую задачу. Для нее prev_job_id не нужен (None).
    job_first = scheduler.add_job(
        send_and_schedule_inner,
        'date',
        run_date=first_target_dt,
        args=[user_id, msg, interval, count]
    )
    
    # Сохраняем первую задачу в словарь пользователя
    if user_id not in user_reminders:
        user_reminders[user_id] = {}
        
    user_reminders[user_id][job_first.id] = {'msg': msg}
    
    update.message.reply_text(f"✅ Напоминание добавлено:\n> {msg}\n> Первое в {first_time}")

def list_reminders(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if not user_reminders.get(user_id):
        update.message.reply_text("📭 У вас нет активных напоминаний.")
        return

    text = "📝 *Ваши активные напоминания:*"
    
    for i, (job_id, data) in enumerate(user_reminders[user_id].items(), start=1):
         # Выводим только первые 25 символов сообщения для компактности + ID задачи для /del
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
        
         # Удаляем из словаря пользователя
         del user_reminders[user_id][job_key]
         
         # Чистим словарь пользователя если он пуст
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

     # Получаем список ID задач для удаления из планировщика и словаря
     jobs_to_remove = list(user_reminders[user_id].keys())
     
     for job_key in jobs_to_remove:
         try:
             scheduler.remove_job(job_key)
         except JobLookupError:
             continue # Игнорируем ошибку "задача уже не существует"
     
     del user_reminders[user_id]
     update.message.reply_text("🗑️ Все напоминания удалены.")

def error_handler(update: object, context: CallbackContext):
     """Логирует ошибки."""
     logger.error(msg="Exception while handling an update:", exc_info=context.error)
     # Также отправим сообщение об ошибке в чат разработчика (если указан)
     # context.bot.send_message(chat_id=CHAT_ID_DEV, text=f"Error: {context.error}")
     
# --- ЗАПУСК БОТА ---
def main():
     # Получаем токен из переменной окружения (безопасно)
     token = os.environ.get('8605114997:AAG_II-LnXBlABH_M-0IryIjotplhxJab58')
     if not token:
         logger.error("Ошибка: Переменная окружения TELEGRAM_TOKEN не установлена.")
         return

     updater = Updater(token)
     dispatcher = updater.dispatcher

     # Регистрация обработчиков команд и сообщений
     dispatcher.add_handler(CommandHandler("start", start))
     dispatcher.add_handler(CommandHandler("help", help_command))
     dispatcher.add_handler(CommandHandler("list", list_reminders))
     dispatcher.add_handler(CommandHandler("del", delete_reminder))
     dispatcher.add_handler(CommandHandler("delall", delete_all))
     
     # Обработчик для создания напоминаний по тексту сообщения (не команда)
     dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_reminder))
     
     # Регистрируем обработчик ошибок (важно для стабильной работы на хостингах)
     dispatcher.add_error_handler(error_handler)
     
     # Запуск через Polling (для локального теста) или Webhook (для продакшена)
     mode = os.environ.get('MODE', 'polling')
     
     try:
         if mode == 'webhook':
             PORT = int(os.environ.get("PORT", 5000))
             updater.start_webhook(
                 listen="0.0.0.0",
                 port=PORT,
                 url_path=token,
             )
             updater.bot.set_webhook(f"https://{os.environ['HEROKU_APP_NAME']}.herokuapp.com/{token}")
             print("Бот запущен в режиме Webhook.")
         else:
             updater.start_polling()
             print("Бот запущен в режиме Polling.")
         
         updater.idle()
         
     except Exception as e:
         logger.error(f"Фатальная ошибка при запуске бота: {e}")
