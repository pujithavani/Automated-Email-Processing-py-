import sqlite3
import base64
from googleapiclient.discovery import build
from authenticate import authenticate

def setup_database(db_path='emails.db'):
    """
    Creates the emails table if it does not exist and returns a (connection, cursor) pair.
    """
    conn = sqlite3.connect(db_path)
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
    return conn, cursor

def fetch_emails(credentials_file="credentials.json", db_path="emails.db", retrieval_method="number", number_or_date="10", log_callback=print):
    """
    Fetches emails from Gmail using the specified retrieval method:
      - "number": fetch up to `number_or_date` emails.
      - "timestamp": fetch emails after the given date (YYYY-MM-DD).
    Stores them in the SQLite database located at `db_path` and logs progress via `log_callback`.
    """
    # Setup the database.
    conn, cursor = setup_database(db_path)

    # Authenticate and build the Gmail API service.
    creds = authenticate(credentials_file)
    service = build('gmail', 'v1', credentials=creds)

    # Build query parameters.
    query_params = {'userId': 'me'}
    if retrieval_method == "number":
        try:
            max_results = int(number_or_date)
        except ValueError:
            max_results = 10
        query_params['maxResults'] = max_results
    elif retrieval_method == "timestamp":
        query_params['q'] = f'after:{number_or_date}'
    else:
        log_callback(f"Invalid retrieval method: {retrieval_method}")
        return

    # Fetch messages.
    results = service.users().messages().list(**query_params).execute()
    messages = results.get('messages', [])

    if not messages:
        log_callback("No emails found.")
        return

    log_callback(f"{len(messages)} emails fetched and stored successfully!")

    # Process each message.
    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()

        sender = ''
        subject = ''
        received_at = message.get('internalDate', '')
        message_body = ''
        label_ids = message.get('labelIds', [])
        is_read = 0
        if 'UNREAD' not in label_ids:
            is_read = 1

        headers = message['payload'].get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                sender = header['value']
            elif header['name'] == 'Subject':
                subject = header['value']

        payload = message.get('payload', {})
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        message_body += decoded
        else:
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                message_body = decoded

        log_callback(f"Storing Email - ID: {msg_id}, Sender: {sender}, Subject: {subject}, Date: {received_at}")

        cursor.execute(
            'INSERT OR IGNORE INTO emails (id, sender, subject, received_at, message, is_read) VALUES (?, ?, ?, ?, ?, ?)',
            (msg_id, sender, subject, received_at, message_body, is_read)
        )

    conn.commit()
    conn.close()
    log_callback("Emails stored successfully in the database!")
