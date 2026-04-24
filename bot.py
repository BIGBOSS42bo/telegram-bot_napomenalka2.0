import logging
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт конфигурации и функций хранения
from config import BOT_TOKEN
from storage import (
    get_user_data,
    set_user_timezone,
    add_reminder,
    get_user_reminders,
    delete_reminder_by_id,
    clear_all_reminders
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in get_user_data(user_id):
        get_user_data(user_id)  # Инициализация данных пользователя
    await update.message.reply_text(
        "Привет! Я бот-напоминатель.\n\n"
        "Доступные команды:\n"
        "/set_timezone — установить часовой пояс\n"
        "/add_reminder — добавить напоминание\n"
        "/list_reminders — список напоминаний\n"
        "/delete_reminder — удалить напоминание\n"
        "/clear_all — удалить все напоминания"
    )

# Установка часового пояса
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    timezones = ['Europe/Moscow', 'Asia/Novosibirsk', 'Europe/London', 'America/New_York']
    keyboard = [[tz] for tz in timezones]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите ваш часовой пояс:", reply_markup=reply_markup)

async def handle_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    timezone_str = update.message.text
    try:
        pytz.timezone(timezone_str)
        set_user_timezone(user_id, timezone_str)
        await update.message.reply_text(f"Часовой пояс установлен: {timezone_str}")
    except pytz.UnknownTimeZoneError:
        await update.message.reply_text("Неизвестный часовой пояс. Попробуйте ещё раз.")


# Добавление напоминания
async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите время напоминания в формате ЧЧ:ММ (например, 14:30):")
    context.user_data['awaiting_time'] = True

async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_time'):
        time_str = update.message.text
        try:
            datetime.strptime(time_str, '%H:%M')
            context.user_data['reminder_time'] = time_str
            context.user_data['awaiting_time'] = False
            context.user_data['awaiting_text'] = True
            await update.message.reply_text("Теперь введите текст напоминания:")
        except ValueError:
            await update.message.reply_text("Неверный формат времени. Используйте ЧЧ:ММ.")

async def handle_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_text'):
        text = update.message.text
        user_id = str(update.effective_user.id)
        time_str = context.user_data['reminder_time']

        # Сохраняем напоминание (ежедневное)
        reminder_id = add_reminder(user_id, time_str, text)

        context.user_data.clear()
        await update.message.reply_text(f"Напоминание установлено на {time_str} каждый день.")

# Список напоминаний
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_reminders = get_user_reminders(user_id)

    if not user_reminders:
        await update.message.reply_text("У вас нет активных напоминаний.")
        return

    response = "Ваши напоминания:\n"
    for r in user_reminders:
        response += f"{r['id']}. {r['text']} в {r['time']}\n"
    await update.message.reply_text(response)

# Удаление напоминания
async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ID напоминания для удаления:")
    context.user_data['awaiting_delete'] = True

async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_delete'):
        try:
            reminder_id = int(update.message.text)
            user_id = str(update.effective_user.id)
            success = delete_reminder_by_id(user_id, reminder_id)

            if success:
                await update.message.reply_text(f"Напоминание {reminder_id} удалено.")
            else:
                await update.message.reply_text("Напоминание с таким ID не найдено.")
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный ID (число).")
        finally:
            context.user_data['awaiting_delete'] = False

# Очистка всех напоминаний
async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    clear_all_reminders(user_id)
    await update.message.reply_text("Все напоминания удалены.")

# Основная функция запуска бота
def main():
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_timezone", set_timezone))
    application.add_handler(CommandHandler("add_reminder", add_reminder))
    application.add_handler(CommandHandler("list_reminders", list_reminders))
    application.add_handler(CommandHandler("delete_reminder", delete_reminder))
    application.add_handler(CommandHandler("clear_all", clear_all))

    # Обработчики текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_timezone))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_time))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
