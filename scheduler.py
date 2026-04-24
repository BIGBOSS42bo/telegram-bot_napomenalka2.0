# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
from storage import get_user_reminders, get_user_data
from telegram import Bot
import asyncio

class ReminderScheduler:
    def __init__(self, bot_token: str):
        self.scheduler = BackgroundScheduler()
        self.bot = Bot(token=bot_token)

    def start(self):
        # Проверяем каждую минуту
        self.scheduler.add_job(self.check_reminders, 'interval', minutes=1)
        self.scheduler.start()

    async def check_reminders(self):
        now = datetime.now(pytz.UTC)

        # Получаем всех пользователей
        data = load_data()  # Импортируйте load_data из storage.py
        for user_id, user_data in data.items():
            timezone_str = user_data.get('timezone', 'UTC')
            try:
                user_tz = pytz.timezone(timezone_str)
                # Конвертируем текущее время в часовой пояс пользователя
                now_user = now.astimezone(user_tz)
                current_time = now_user.strftime('%H:%M')

                # Проверяем напоминания пользователя
                for reminder in user_data['reminders']:
                    if reminder['time'] == current_time:
                        # Отправляем напоминание
                        await self.bot.send_message(
                            chat_id=int(user_id),
                            text=f"⏰ Напоминание: {reminder['text']}"
                        )
            except pytz.UnknownTimeZoneError:
                logger.error(f"Неизвестный часовой пояс для пользователя {user_id}: {timezone_str}")
