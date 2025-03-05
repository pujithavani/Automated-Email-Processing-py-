import sqlite3
import base64
import json
from googleapiclient.discovery import build
from authenticate import authenticate

def setup_database():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            sender TEXT,
            subject TEXT,
            received_at TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def fetch_emails():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()

        sender = ''
        subject = ''
        received_at = message['internalDate']
        message_body = ''

        headers = message['payload'].get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
            if header['name'] == 'Subject':
                subject = header['value']

        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    message_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        cursor.execute('INSERT OR IGNORE INTO emails (id, sender, subject, received_at, message) VALUES (?, ?, ?, ?, ?)',
                       (msg_id, sender, subject, received_at, message_body))

    conn.commit()
    conn.close()
    print("Emails fetched and stored successfully!")

def apply_rules():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)

    with open('rules.json', 'r') as file:
        rules_data = json.load(file)

    cursor.execute('SELECT id, sender, subject, message FROM emails WHERE is_read = 0')
    emails = cursor.fetchall()

    for email_data in emails:
        email_id, sender, subject, message = email_data
        for rule in rules_data['rules']:
            conditions_met = []

            for condition in rule['conditions']:
                field = condition['field']
                operator = condition['operator']
                value = condition['value']

                field_value = sender if field == "from" else subject if field == "subject" else message

                if operator == "contains" and value in field_value:
                    conditions_met.append(True)
                elif operator == "equals" and value == field_value:
                    conditions_met.append(True)
                elif operator == "does_not_contain" and value not in field_value:
                    conditions_met.append(True)
                elif operator == "does_not_equal" and value != field_value:
                    conditions_met.append(True)

            predicate = rule["predicate"]
            if (predicate == "All" and all(conditions_met)) or (predicate == "Any" and any(conditions_met)):
                for action in rule["actions"]:
                    if action.startswith("move_to_label:"):
                        label_name = action.split(":")[1]
                        
                        labels = service.users().labels().list(userId='me').execute().get('labels', [])
                        label_id = next((label['id'] for label in labels if label['name'] == label_name), None)

                        if label_id:
                            service.users().messages().modify(userId='me', id=email_id, body={"addLabelIds": [label_id]}).execute()
                            print(f"Moved email {email_id} to label {label_name}.")
                        else:
                            print(f"Label '{label_name}' not found. Create it manually in Gmail.")
                    
                    elif action == "mark_as_read":
                        service.users().messages().modify(userId='me', id=email_id, body={"removeLabelIds": ["UNREAD"]}).execute()
                        print(f"Marked email {email_id} as read.")
                    
                    elif action == "mark_as_unread":
                        service.users().messages().modify(userId='me', id=email_id, body={"addLabelIds": ["UNREAD"]}).execute()
                        print(f"Marked email {email_id} as unread.")

    conn.close()

if __name__ == '__main__':
    setup_database()
    choice = input("Enter 'fetch' to fetch emails or 'rules' to apply rules: ").strip().lower()
    if choice == 'fetch':
        fetch_emails()
    elif choice == 'rules':
        apply_rules()
    else:
        print("Invalid choice! Please enter 'fetch' or 'rules'.")
