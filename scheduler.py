from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import telegram

def send_reminder(bot, user_id, message):
    bot.send_message(chat_id=user_id, text=f"⏰ Напоминание: {message}")

def schedule_reminder(bot, reminder):
    scheduler = BackgroundScheduler()
    
    # Первое напоминание
    first_time = datetime.now() + timedelta(seconds=reminder.first_delay)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=first_time,
        args=[bot, reminder.user_id, reminder.message]
    )
    
    # Повторные напоминания
    if reminder.count > 0 and reminder.interval > 0:
        for i in range(reminder.count):
            next_time = first_time + timedelta(seconds=reminder.interval * (i + 1))
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=next_time,
                args=[bot, reminder.user_id, reminder.message]
            )
    
    scheduler.start()
