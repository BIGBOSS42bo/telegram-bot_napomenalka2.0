import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import Session, Reminder
from scheduler import schedule_reminder
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для напоминаний.\n"
        "Формат сообщения: [текст],[время],[интервал],[количество]\n"
        "Пример: Выйти на улицу,3:30,14:40,3\n"
        "Команды:\n"
        "/help — справка\n"
        "/list — список напоминаний\n"
        "/del [номер] — удалить напоминание\n"
        "/delall — удалить все напоминания"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Формат: [текст],[время],[интервал],[количество]\n"
        "Время — в формате ЧЧ:ММ (например, 3:30)\n"
        "Интервал — через сколько повторить (0 — не повторять)\n"
        "Количество — сколько раз повторить (inf — бесконечно)\n\n"
        "Команды:\n"
        "/list — показать напоминания\n"
        "/del [номер] — удалить конкретное\n"
        "/delall — удалить все"
    )

def parse_time(time_str):
    """Парсит время в формате ЧЧ:ММ и возвращает секунды"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 3600 + minutes * 60
    except:
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if ',' not in text:
        await update.message.reply_text("Неверный формат. Используйте: [текст],[время],[интервал],[количество]")
        return
    
    parts = text.split(',')
    if len(parts) != 4:
        await update.message.reply_text("Должно быть 4 параметра через запятую")
        return
    
    message, time_str, interval_str, count_str = parts
    
    # Парсим время
    first_delay = parse_time(time_str)
    if first_delay is None:
        await update.message.reply_text("Неверный формат времени (должно быть ЧЧ:ММ)")
        return
    
    interval = parse_time(interval_str)
    if interval is None:
        await update.message.reply_text("Неверный формат интервала (должно быть ЧЧ:ММ)")
        return
    
    # Обрабатываем количество повторений
    if count_str.lower() == 'inf':
        count = -1  # специальное значение для бесконечных напоминаний
    else:
        try:
            count = int(count_str)
            if count < 0:
                await update.message.reply_text("Количество должно быть положительным числом или 'inf'")
                return
        except:
            await update.message.reply_text("Количество должно быть числом или 'inf'")
            return
    
    # Сохраняем в БД
    session = Session()
    reminder = Reminder(
        user_id=update.message.from_user.id,
        message=message.strip(),
        first_delay=first_delay,
        interval=interval,
        count=count,
        created_at=datetime.now()
    )
    session.add(reminder)
    session.commit()
    
    # Планируем напоминание
    schedule_reminder(context.bot, reminder)
    
    await update.message.reply_text(f"Напоминание сохранено! ID: {reminder.id}")
    session.close()

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    reminders = session.query(Reminder).filter(Reminder.user_id == update.message.from_user.id).all()
    if not reminders:
        await update.message.reply_text("У вас нет активных напоминаний")
        session.close()
        return
    
    response = "Ваши напоминания:\n"
    for r in reminders:
        count_text = "бесконечно" if r.count == -1 else r.count
        response += f"{r.id}. {r.message} (первое через {r.first_delay//3600}ч {(r.first_delay%3600)//60}м, интервал {r.interval//3600}ч {(r.interval%3600)//60}м, повторений: {count_text})\n"
    
    await update.message.reply_text(response)
    session.close()

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите номер напоминания: /del [номер]")
        return
    
    try:
        reminder_id = int(context.args[0])
