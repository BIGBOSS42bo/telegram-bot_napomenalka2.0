# storage.py
import json
import os
from typing import Dict, List, Optional

REMINDERS_FILE = 'data/reminders.json'

def ensure_data_dir():
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)

def load_data() -> Dict:
    ensure_data_dir()
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data: Dict) -> None:
    with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id: str) -> Dict:
    data = load_data()
    user_data = data.get(user_id, {'timezone': None, 'reminders': []})
    data[user_id] = user_data
    save_data(data)
    return user_data

def set_user_timezone(user_id: str, timezone: str) -> None:
    data = load_data()
    if user_id not in data:
        data[user_id] = {'timezone': None, 'reminders': []}
    data[user_id]['timezone'] = timezone
    save_data(data)

def add_reminder(user_id: str, reminder_time: str, text: str) -> int:
    data = load_data()
    if user_id not in data:
        data[user_id] = {'timezone': None, 'reminders': []}

    reminders = data[user_id]['reminders']
    reminder_id = len(reminders) + 1
    reminders.append({
        'id': reminder_id,
        'time': reminder_time,  # Сохраняем только время
        'text': text,
        'is_daily': True  # Помечаем как ежедневное
    })
    save_data(data)
    return reminder_id

def get_user_reminders(user_id: str) -> List[Dict]:
    user_data = get_user_data(user_id)
    return user_data['reminders']

def delete_reminder_by_id(user_id: str, reminder_id: int) -> bool:
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
    data = load_data()
    if user_id in data:
        data[user_id]['reminders'] = []
        save_data(data)
