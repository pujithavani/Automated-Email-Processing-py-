import sqlite3
import base64
from googleapiclient.discovery import build
from authenticate import authenticate

# Database setup
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

def fetch_emails():
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)

    # Ask user for input: either max emails or timestamp
    choice = input("Enter 'number' to fetch a specific number of emails or 'timestamp' to filter by date: ").strip().lower()

    query_params = {'userId': 'me'}
    
    if choice == "number":
        max_results = int(input("Enter the number of emails to fetch: ").strip())
        query_params['maxResults'] = max_results
    elif choice == "timestamp":
        timestamp = input("Enter timestamp (YYYY-MM-DD) to fetch emails after this date: ").strip()
        query_params['q'] = f'after:{timestamp}'
    else:
        print("Invalid choice! Exiting...")
        return

    results = service.users().messages().list(**query_params).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No emails found.")
        return

    print(f"{len(messages)} emails fetched and stored successfully!")

    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()

        sender = ''
        subject = ''
        received_at = message.get('internalDate', '')
        message_body = ''

        headers = message['payload'].get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
            if header['name'] == 'Subject':
                subject = header['value']

        payload = message.get('payload', {})
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'body' in part:
                    data = part['body'].get('data', '')
                    if data:
                        message_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        print(f"Storing Email - ID: {msg_id}, Sender: {sender}, Subject: {subject}, Date: {received_at}")

        cursor.execute('INSERT OR IGNORE INTO emails (id, sender, subject, received_at, message) VALUES (?, ?, ?, ?, ?)',
                       (msg_id, sender, subject, received_at, message_body))

    conn.commit()
    conn.close()
    print("Emails stored successfully in the database!")

if __name__ == '__main__':
    fetch_emails()
