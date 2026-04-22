import json
import os
from datetime import datetime

class Storage:
    def __init__(self, data_file='data/users.json'):
        self.data_file = data_file
        self._ensure_data_dir()
        self.load_data()

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

    def load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_user_timezone(self, user_id):
        return self.data.get(str(user_id), {}).get('timezone', None)

    def set_user_timezone(self, user_id, timezone):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {'reminders': []}
        self.data[user_id]['timezone'] = timezone
        self.save_data()

    def add_reminder(self, user_id, time_str, text):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {'timezone': None, 'reminders': []}
        reminder = {
            'time': time_str,
            'text': text,
            'created_at': datetime.now().isoformat()
        }
        self.data[user_id]['reminders'].append(reminder)
        self.save_data()

    def delete_reminder(self, user_id, reminder_index):
        user_id = str(user_id)
        if (user_id in self.data and
            0 <= reminder_index < len(self.data[user_id]['reminders'])):
            del self.data[user_id]['reminders'][reminder_index]
            self.save_data()
            return True
        return False

    def clear_all_reminders(self, user_id):
        user_id = str(user_id)
        if user_id in self.data:
            self.data[user_id]['reminders'] = []
            self.save_data()
            return True
        return False

    def get_reminders(self, user_id):
        user_id = str(user_id)
        return self.data.get(user_id, {}).get('reminders', [])
