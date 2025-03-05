import sys
sys.path.append(r"C:\Users\pujit\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages")  # Replace with actual path
import json
import sqlite3
#import pyforms
from pyforms.basewidget import BaseWidget 
from pyforms.controls import ControlList, ControlButton, ControlCombo, ControlText
from fetch import fetch_emails
from rules import apply_rules

class EmailManagerGUI(BaseWidget):
    def __init__(self):
        super().__init__('Email Manager')

        self.email_list = ControlList('Fetched Emails', add_function=False)
        self.fetch_button = ControlButton('Fetch Emails')
        self.action_combo = ControlCombo('Select Action')
        self.email_input = ControlText('Enter Sender Email')
        self.label_input = ControlText('Enter Label (if moving)')
        self.apply_button = ControlButton('Apply Action')

        self.action_combo.add_item('Mark as Read', 'mark_as_read')
        self.action_combo.add_item('Mark as Unread', 'mark_as_unread')
        self.action_combo.add_item('Move to Label', 'move_to_label')
        self.action_combo.add_item('Star Email', 'star_email')

        self.formset = [
            ('fetch_button', 'email_list'),
            ('email_input', 'action_combo', 'label_input', 'apply_button')
        ]

        self.fetch_button.value = self.fetch_emails
        self.apply_button.value = self.apply_action

    def fetch_emails(self):
        fetch_emails()
        self.load_emails()

    def load_emails(self):
        self.email_list.clear()
        conn = sqlite3.connect('emails.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, subject FROM emails")
        for email in cursor.fetchall():
            self.email_list += email
        conn.close()

    def apply_action(self):
        email = self.email_input.value
        action = self.action_combo.value
        label = self.label_input.value if action == 'move_to_label' else None
        apply_rules(email, action, label)
        self.load_emails()

if __name__ == '__main__':
    from pyforms import start_app
    start_app(EmailManagerGUI)
