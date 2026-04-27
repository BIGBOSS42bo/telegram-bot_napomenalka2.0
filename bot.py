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

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Глобальные переменные ---
# Словарь для хранения напоминаний: {user_id: {job_id: {'msg': str, 'count': str/int}}}
user_reminders = {}
scheduler = BackgroundScheduler()
scheduler.start()

# --- Вспомогательные функции ---

def parse_reminder(text: str):
    """
    Парсит строку с напоминанием.
    Возвращает кортеж (msg, first_time, interval, count) или None при ошибке.
    """
    match = re.match(r'(.+),(\d{1,2}:\d{2}),(\d{1,2}:\d{2}|0),(\d+|inf)', text)
    if not match:
        return None
    return match.groups()

def validate_time(time_str: str):
    """Проверяет, что строка времени в формате ЧЧ:ММ."""
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def get_next_datetime(now: datetime.datetime, time_str: str):
    """Возвращает объект datetime для следующего срабатывания."""
    h, m = map(int, time_str.split(':'))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target < now:
        target += datetime.timedelta(days=1)
    return target

# --- Основные функции бота ---

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет! Я бот-напоминалка. Используй команду /help, чтобы узнать, как со мной работать."
    )

def help_command(update: Update, context: CallbackContext):
    help_text = """
*Доступные команды:*
/start - Начать диалог
/help - Показать это сообщение
/list - Показать список ваших напоминаний
/del [номер] - Удалить напоминание по номеру
/delall - Удалить все ваши напоминания

*Формат создания напоминания:*
Просто напишите сообщение в чат в формате:
`[Текст], [Время первого напоминания (ЧЧ:ММ)], [Интервал повтора (ЧЧ:ММ или 0)], [Количество повторов (число или inf)]`

*Пример:*
`Выйти на улицу, 3:30, 14:40, 3`
"""
    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

def add_reminder(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    # Проверяем, что это не команда
    if update.message.text.startswith('/'):
        return

    parsed = parse_reminder(update.message.text)
    
    if not parsed:
        update.message.reply_text(
            "❌ Неверный формат сообщения.\n"
            "Используйте шаблон: `Текст, ЧЧ:ММ, ЧЧ:ММ|0, число|inf`\n"
            "Пример: `Выйти на улицу, 3:30, 14:40, 3`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    msg, first_time, interval, count = parsed

    if not validate_time(first_time) or (interval != '0' and not validate_time(interval)):
        update.message.reply_text("❌ Ошибка в формате времени. Используйте ЧЧ:ММ.")
        return

    try:
        if count != 'inf':
            count = int(count)
            if count < 1:
                raise ValueError
    except ValueError:
        update.message.reply_text("❌ Количество повторов должно быть целым положительным числом или 'inf'.")
        return

    now = datetime.datetime.now()
    
    # Планируем первое напоминание
    first_target_dt = get_next_datetime(now, first_time)
    
    def send_and_schedule(user_id_inner, msg_inner, interval_inner, count_inner):
        """Внутренняя функция для отправки и планирования следующих шагов."""
        context.bot.send_message(chat_id=user_id_inner, text=msg_inner)
        
        # Если интервал 0 или количество повторов исчерпано - выходим
        if interval_inner == '0':
            return
            
        if count_inner == 'inf':
            next_count = 'inf'
        else:
            next_count = int(count_inner) - 1
            if next_count <= 0:
                return

        # Планируем следующее напоминание через интервал
        h_int, m_int = map(int, interval_inner.split(':'))
        delta = datetime.timedelta(hours=h_int, minutes=m_int)
        
        next_dt = datetime.datetime.now() + delta

        job = scheduler.add_job(
            send_and_schedule,
            'date',
            run_date=next_dt,
            args=[user_id_inner, msg_inner, interval_inner, next_count]
        )
        
        # Сохраняем ID задачи для возможности удаления пользователем
        if user_id_inner not in user_reminders:
            user_reminders[user_id_inner] = {}
        user_reminders[user_id_inner][job.id] = {'msg': msg_inner}

    # Планируем самую первую задачу
    job_first = scheduler.add_job(
        send_and_schedule,
        'date',
        run_date=first_target_dt,
        args=[user_id, msg, interval, count]
    )
    
    if user_id not in user_reminders:
        user_reminders[user_id] = {}
        
    user_reminders[user_id][job_first.id] = {'msg': msg}
    
    update.message.reply_text(f"✅ Напоминание добавлено:\n> {msg}\n> Первое в {first_time}")

def list_reminders(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        update.message.reply_text("📭 У вас нет активных напоминаний.")
        return

    text = "📝 *Ваши активные напоминания:*"
    
    for i, (job_id, data) in enumerate(user_reminders[user_id].items(), start=1):
        text += f"\n{i}. `{job_id}` - {data['msg']}"
        
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def delete_reminder(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    
    if len(context.args) != 1:
        update.message.reply_text("⚠️ Используйте формат: /del [номер_напоминания]")
        return

    job_key = context.args[0]
    
    if user_id not in user_reminders or job_key not in user_reminders[user_id]:
        update.message.reply_text("❌ Напоминание с таким номером не найдено.")
        return

    try:
        scheduler.remove_job(job_key)
        del user_reminders[user_id][job_key]
        
        # Если словарь пользователя пуст - удаляем его из общего словаря
        if not user_reminders[user_id]:
            del user_reminders[user_id]
            
        update.message.reply_text("🗑️ Напоминание удалено.")
        
    except JobLookupError:
        update.message.reply_text("❌ Ошибка при удалении. Напоминание могло уже сработать.")

def delete_all(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if user_id not in user_reminders or not user_reminders[user_id]:
        update.message.reply_text("📭 У вас нет активных напоминаний для удаления.")
        return

    for job_key in list(user_reminders[user_id].keys()):
        try:
            scheduler.remove_job(job_key)
        except JobLookupError:
            continue

    del user_reminders[user_id]
    
    update.message.reply_text("🗑️ Все напоминания удалены.")

def error_handler(update: object, context: CallbackContext):
    """Логирует ошибки."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --- Запуск бота ---

def main():
    # Замените 'ВАШ_ТОКЕН' на токен от @BotFather
    updater = Updater("ВАШ_ТОКЕН")
    
    dispatcher = updater.dispatcher

    # Регистрация обработчиков команд и сообщений
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("list", list_reminders))
    
    # Обработчики удаления требуют аргументов (номер)
    dispatcher.add_handler(CommandHandler("del", delete_reminder))
    
    dispatcher.add_handler(CommandHandler("delall", delete_all))
    
    # Обработчик для создания напоминаний по тексту сообщения
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_reminder))
    
    # Регистрируем обработчик ошибок (важно для стабильной работы на хостингах)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    
    print("Бот запущен...")
    
if __name__ == '__main__':
    main()
