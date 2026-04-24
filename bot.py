import logging
from datetime import datetime
import pytz
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт конфигурации
from config import BOT_TOKEN

# Путь к файлу с напоминаниями
REMINDERS_FILE = 'data/reminders.json'

# Загрузка напоминаний из файла
def load_reminders():
    try:
        with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Сохранение напоминаний в файл
def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=4)

# Инициализация хранилища напоминаний
reminders = load_reminders()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in reminders:
        reminders[user_id] = {'timezone': None, 'reminders': []}
        save_reminders(reminders)
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
        if user_id in reminders:
            reminders[user_id]['timezone'] = timezone_str
            save_reminders(reminders)
            await update.message.reply_text(f"Часовой пояс установлен: {timezone_str}")
        else:
            await update.message.reply_text("Сначала используйте /start")
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

        # Получаем часовой пояс пользователя
        user_timezone = reminders.get(user_id, {}).get('timezone', 'UTC')
        tz = pytz.timezone(user_timezone)

        # Формируем дату напоминания (сегодня + указанное время)
        now = datetime.now(tz)
        reminder_datetime = now.replace(hour=int(time_str.split(':')[0]),
                                     minute=int(time_str.split(':')[1]),
                                     second=0, microsecond=0)

        # Если время уже прошло, ставим на следующий день
        if reminder_datetime <= now:
            reminder_datetime += timedelta(days=1)

        # Сохраняем напоминание
        reminder = {
            'id': len(reminders[user_id]['reminders']) + 1,
            'time': reminder_datetime.isoformat(),
            'text': text
        }
        reminders[user_id]['reminders'].append(reminder)
        save_reminders(reminders)

        context.user_data.clear()
        await update.message.reply_text(f"Напоминание установлено на {reminder_datetime.strftime('%d.%m.%Y %H:%M')}.")

# Список напоминаний
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_reminders = reminders.get(user_id, {}).get('reminders', [])
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
            user_reminders = reminders.get(user_id, {}).get('reminders', [])
            for i, r in enumerate(user_reminders):
                if r['id'] == reminder_id:
                    del user_reminders[i]
                    save_reminders(reminders)
                    await update.message.reply_text(f"Напоминание {reminder_id} удалено.")
                    break
            else:
                await update.message.reply_
