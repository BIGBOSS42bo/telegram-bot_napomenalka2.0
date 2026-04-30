import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

#8605114997:AAG_II-LnXBlABH_M-0IryIjotplhxJab58

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
    context.job_queue.run_once(send_delayed_message, 30, context=chat_id)


def main():
    # Получаем переменные окружения
    TOKEN = os.getenv('TELEGRAM_API_TOKEN')
    PORT = int(os.getenv('PORT', 8443))
    APP_NAME = os.getenv('APP_NAME')

    if not TOKEN:
        raise ValueError("Не указан TELEGRAM_API_TOKEN")

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Регистрируем обработчик команды /start
    dispatcher.add_handler(CommandHandler("start", start))

    # Запуск через webhook (важно для хостинга)
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
    )
    # Устанавливаем webhook (URL должен быть доступен извне)
    webhook_url = f"https://{APP_NAME}.bothost.me/{TOKEN}"
    updater.bot.set_webhook(url=webhook_url)

    logger.info(f"Бот запущен и слушает порт {PORT}")
    updater.idle()


if __name__ == '__main__':
    main()
