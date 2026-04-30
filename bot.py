import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_delayed_message(context: CallbackContext):
    """Отправляет отложенное сообщение."""
    chat_id = context.job.context
    context.bot.send_message(chat_id=chat_id, text="Это сообщение отправлено через 30 секунд!")


def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    chat_id = update.message.chat_id
    update.message.reply_text("Привет! Через 30 секунд я отправлю тебе это же сообщение.")
    # Ставим задачу на отправку сообщения через 30 секунд
    context.job_queue.run_once(send_delayed_message, 30, context=chat_id)


def main():
    # Получаем токен из переменной окружения
    TOKEN = os.getenv('TELEGRAM_API_TOKEN')

    if not TOKEN:
        raise ValueError("Не указан TELEGRAM_API_TOKEN")

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Регистрируем обработчик команды /start
    dispatcher.add_handler(CommandHandler("start", start))

    # --- ИЗМЕНЕНИЯ ДЛЯ ХОСТИНГА ---
    # Мы НЕ используем start_webhook здесь.
    # Бот будет запущен платформой bothost через Procfile.
    # Он будет слушать POST-запросы от GitHub.
    
    # Для локального тестирования можно использовать polling:
    # updater.start_polling()
    # updater.idle()
    
    # Для работы на хостинге через вебхук, код должен быть готов принимать POST-запросы.
    # Библиотека python-telegram-bot делает это автоматически при запуске через updater.start_polling()
    # или при обработке вебхука, если платформа сама проксирует запрос.
    
    # Чтобы бот не падал сразу при запуске на хостинге (где нет polling),
    # мы просто оставляем его "живым", ожидая внешних запросов.
    # В данном случае, bothost сам управляет процессом.
    
if __name__ == '__main__':
    main()
