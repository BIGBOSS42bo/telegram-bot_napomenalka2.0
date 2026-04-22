from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from storage import Storage
from config import BOT_TOKEN
from datetime import datetime, timedelta
import re

# Состояния для ConversationHandler
TIMEZONE, REMINDER_TIME, REMINDER_TEXT = range(3)

storage = Storage()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    timezone = storage.get_user_timezone(user_id)

    if not timezone:
        await update.message.reply_text(
            "Привет! Для начала работы укажи свой часовой пояс (например, +3 для Москвы):"
        )
        return TIMEZONE
    else:
        await update.message.reply_text(
            f"Привет! Твой часовой пояс: UTC{timezone}.\n"
            "Используй команды:\n"
            "/set_timezone — изменить часовой пояс\n"
            "/add_reminder — добавить напоминание\n"
            "/list_reminders — посмотреть напоминания\n"
            "/delete_reminder — удалить конкретное напоминание\n"
            "/clear_all — удалить все напоминания"
        )

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Укажи свой часовой пояс (например, +3):")
    return TIMEZONE

async def receive_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    timezone_input = update.message.text.strip()
    # Проверка формата: +N или -N, где N от 0 до 12
    if re.match(r'^[+-]?\d{1,2}$', timezone_input):
        storage.set_user_timezone(update.effective_user.id, timezone_input)
        await update.message.reply_text(f"Часовой пояс установлен: UTC{timezone_input}")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Неверный формат. Укажи смещение в часах (например, +3 или -5):")
        return TIMEZONE

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи время напоминания в формате ЧЧ:ММ (например, 14:30):")
    return REMINDER_TIME

async def receive_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_input = update.message.text.strip()
    if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_input):
        context.user_data['reminder_time'] = time_input
        await update.message.reply_text("Теперь введи текст напоминания:")
        return REMINDER_TEXT
    else:
        await update.message.reply_text("Неверный формат времени. Используй ЧЧ:ММ (например, 09:15 или 21:45):")
        return REMINDER_TIME

async def receive_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    time = context.user_data.get('reminder_time')
    user_id = update.effective_user.id

    storage.add_reminder(user_id, time, text)
    await update.message.reply_text(f"Напоминание на {time} добавлено: {text}")
    return ConversationHandler.END

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = storage.get_reminders(user_id)

    if not reminders:
        await update.message.reply_text("У тебя нет активных напоминаний.")
        return

    response = "Твои напоминания:\n"
    for i, r in enumerate(reminders, 1):
        response += f"{i}. {r['time']} — {r['text']}\n"
    await update.message.reply_text(response)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = storage.get_reminders(user_id)

    if not reminders:
        await update.message.reply_text("У тебя нет напоминаний
