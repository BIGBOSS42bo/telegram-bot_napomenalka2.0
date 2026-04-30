from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция, которая будет вызвана через 30 секунд
def send_delayed_message(context: CallbackContext):
    chat_id = context.job.context
    context.bot.send_message(chat_id=chat_id, text="Это сообщение отправлено через 30 секунд!")

# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    update.message.reply_text("Привет! Через 30 секунд я отправлю тебе это же сообщение.")
    # Ставим задачу на отправку сообщения через 30 секунд
    context.job_queue.run_once(send_delayed_message, 30, context=chat_id)

def main() -> None:
    # Вставьте сюда токен вашего бота
    updater = Updater("8605114997:AAG_II-LnXBlABH_M-0IryIjotplhxJab58")

    dispatcher = updater.dispatcher

    # Регистрируем обработчик команды /start
    dispatcher.add_handler(CommandHandler("start", start))

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
