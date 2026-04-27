from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import re

# Словарь для хранения напоминаний: user_id -> список напоминаний
reminders = {}

def parse_reminder(text):
    match = re.match(r'(.+),(\d{1,2}:\d{2}),(\d{1,2}:\d{2}|0),(\d+|inf)', text)
    if not match:
        return None
    msg, first_time, interval, count = match.groups()
    return msg, first_time, interval, count

def schedule_reminder(user_id, msg, first_time, interval, count):
    # Преобразование времени в секунды от текущего момента
    now = datetime.datetime.now()
    first_dt = datetime.datetime.strptime(first_time, "%H:%M")
    first_delta = (first_dt - now.time()).total_seconds()
    if first_delta < 0:
        first_delta += 86400  # +24 часа

    # Планирование первого сообщения
    scheduler.add_job(send_reminder, 'date', run_date=now + datetime.timedelta(seconds=first_delta),
                      args=[user_id, msg, interval, count])

def send_reminder(user_id, msg, interval, count_left):
    # Отправка сообщения пользователю
    updater.bot.send_message(chat_id=user_id, text=msg)
    if interval != '0' and count_left != '0':
        # Планирование следующего напоминания
        h, m = map(int, interval.split(':'))
        delta = datetime.timedelta(hours=h, minutes=m)
        new_count = 'inf' if count_left == 'inf' else int(count_left) - 1
        scheduler.add_job(send_reminder, 'date', run_date=datetime.datetime.now() + delta,
                          args=[user_id, msg, interval, new_count])

def add_reminder(update, context):
    user_id = update.message.chat_id
    parsed = parse_reminder(update.message.text)
    if not parsed:
        update.message.reply_text("Неверный формат. Пример: Выйти на улицу,3:30,14:40,3")
        return
    msg, first_time, interval, count = parsed
    schedule_reminder(user_id, msg, first_time, interval, count)
    update.message.reply_text(f"Напоминание добавлено: {msg}")

# Остальные обработчики команд (/help, /list, /del и т.д.) реализуются аналогично

updater = Updater(token='8605114997:AAG_II-LnXBlABH_M-0IryIjotplhxJab58', use_context=True)
dispatcher = updater.dispatcher

# Регистрация обработчиков
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_reminder))
# Добавить обработчики для /help, /list, /del [номер], /delall

scheduler = BackgroundScheduler()
scheduler.start()

updater.start_polling()
updater.idle()
