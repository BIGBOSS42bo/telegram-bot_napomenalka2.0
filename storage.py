# storage.py
import json
import os
from typing import Dict, List, Optional

REMINDERS_FILE = 'data/reminders.json'

def ensure_data_dir():
    """Создаёт директорию data, если её нет."""
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)

def load_data() -> Dict:
    """Загружает данные из JSON‑файла."""
    ensure_data_dir()
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data: Dict) -> None:
    """Сохраняет данные в JSON‑файл."""
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id: str) -> Dict:
    """Возвращает данные пользователя или создаёт новые."""
    data = load_data()
    user_data = data.get(user_id, {'timezone': None, 'reminders': []})
    data[user_id] = user_data
    save_data(data)
    return user_data

def set_user_timezone(user_id: str, timezone: str) -> None:
    """Устанавливает часовой пояс пользователя."""
    data = load_data()
    if user_id not in data:
        data[user_id] = {'timezone': None, 'reminders': []}
    data[user_id]['timezone'] = timezone
    save_data(data)

def add_reminder(user_id: str, reminder_time: str, text: str) -> int:
    """Добавляет напоминание и возвращает его ID."""
    data = load_data()
    if user_id not in data:
        data[user_id] = {'timezone': None, 'reminders': []}

    reminders = data[user_id]['reminders']
    reminder_id = len(reminders) + 1
    reminders.append({
        'id': reminder_id,
        'time': reminder_time,
        'text': text
    })
    save_data(data)
    return reminder_id

def get_user_reminders(user_id: str) -> List[Dict]:
    """Возвращает список напоминаний пользователя."""
    user_data = get_user_data(user_id)
    return user_data['reminders']

def delete_reminder_by_id(user_id: str, reminder_id: int) -> bool:
    """Удаляет напоминание по ID. Возвращает True, если успешно."""
    data = load_data()
    if user_id in data:
        reminders = data[user_id]['reminders']
        for i, reminder in enumerate(reminders):
            if reminder['id'] == reminder_id:
                del reminders[i]
                save_data(data)
                return True
    return False

def clear_all_reminders(user_id: str) -> None:
    """Удаляет все напоминания пользователя."""
    data = load_data()
    if user_id in data:
        data[user_id]['reminders'] = []
        save_data(data)
