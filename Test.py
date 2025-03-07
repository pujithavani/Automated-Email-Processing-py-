import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import json
import os
import base64
from io import StringIO

# Import the modules to be tested.
import fetch
import rules

#####################################
# DummyConnection: Subclass sqlite3.Connection to override close()
#####################################
class DummyConnection(sqlite3.Connection):
    def close(self):
        # Override close() so that our in-memory DB stays accessible during tests.
        pass

#####################################
# Integration Test for fetch.py
#####################################
class TestFetchEmails(unittest.TestCase):

    def setUp(self):
        # Create an in-memory SQLite DB using DummyConnection.
        self.conn = sqlite3.connect(':memory:', factory=DummyConnection)
        self.cursor = self.conn.cursor()
        # Create the emails table as in fetch.py.
        self.cursor.execute('''
            CREATE TABLE emails (
                id TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                received_at TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
        
        # Patch sqlite3.connect in fetch so it always returns our in-memory DB.
        self.sqlite_patcher = patch('fetch.sqlite3.connect', lambda db_name="emails.db": self.conn)
        self.sqlite_patcher.start()

        # Patch os.path.exists globally so that token.pickle is not found.
        self.exists_patcher = patch('os.path.exists', return_value=False)
        self.exists_patcher.start()

        # Create a fake Gmail API service.
        self.fake_service = MagicMock()
        # Fake messages.list response: one message with id 'test_id'
        self.fake_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            'messages': [{'id': 'test_id'}]
        }
        # Fake messages.get response: simulate an email message.
        fake_message = {
            'id': 'test_id',
            'internalDate': '1234567890',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'}
                ],
                'parts': [{
                    'mimeType': 'text/plain',
                    'body': {'data': base64.urlsafe_b64encode(b'This is a test email body').decode('utf-8')}
                }]
            }
        }
        self.fake_service.users.return_value.messages.return_value.get.return_value.execute.return_value = fake_message

        # Patch fetch.authenticate and fetch.build so that fetch.fetch_emails() uses our fake service.
        self.auth_patcher = patch('fetch.authenticate', return_value=MagicMock())
        self.auth_patcher.start()
        self.build_patcher = patch('fetch.build', return_value=self.fake_service)
        self.build_patcher.start()

    def tearDown(self):
        self.sqlite_patcher.stop()
        self.exists_patcher.stop()
        self.auth_patcher.stop()
        self.build_patcher.stop()
        self.conn.close()

    def test_fetch_emails_number_option(self):
        """
        Integration Test for fetch.py:
        - Simulates user input for the 'number' option.
        - Calls fetch.fetch_emails() which should fetch a fake email and store it in the DB.
        - Verifies the email is stored correctly.
        """
        # Simulate choosing "number" and then "1" for the number of emails.
        with patch('builtins.input', side_effect=["number", "1"]):
            output = StringIO()
            import sys
            original_stdout = sys.stdout
            sys.stdout = output

            fetch.fetch_emails()

            sys.stdout = original_stdout

            # Query the DB for the email with id 'test_id'
            self.cursor.execute("SELECT * FROM emails WHERE id='test_id'")
            row = self.cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 'test_id')
            self.assertEqual(row[1], 'test@example.com')
            self.assertEqual(row[2], 'Test Subject')
            # Fixed assertion: check for the exact confirmation message.
            self.assertIn("Emails stored successfully in the database!", output.getvalue())

#####################################
# Unit and Integration Tests for rules.py
#####################################
class TestRules(unittest.TestCase):

    def setUp(self):
        # Create an in-memory SQLite DB for testing rules.py.
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        # Drop the emails table if it exists, then create it.
        self.cursor.execute("DROP TABLE IF EXISTS emails")
        self.cursor.execute('''
            CREATE TABLE emails (
                id TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0
            )
        ''')
        # Insert a dummy unread email.
        self.cursor.execute(
            "INSERT INTO emails (id, sender, subject, message, is_read) VALUES (?, ?, ?, ?, ?)",
            ('1', 'test@example.com', 'Test', 'Dummy message', 0)
        )
        self.conn.commit()

        # Create a temporary rules.json file for testing.
        self.test_rules_path = 'test_rules.json'
        with open(self.test_rules_path, 'w') as f:
            json.dump({"rules": []}, f, indent=4)

        # Replace the existing rules.json with our test file.
        self.original_rules_path = 'rules.json'
        if os.path.exists(self.original_rules_path):
            os.remove(self.original_rules_path)
        os.rename(self.test_rules_path, self.original_rules_path)

        # Patch sqlite3.connect in rules.py to use our in-memory DB.
        self.sqlite_patcher = patch('rules.sqlite3.connect', lambda db_name="emails.db": self.conn)
        self.sqlite_patcher.start()

        # Create a fake Gmail API service for rules.py.
        self.fake_service = MagicMock()
        # Simulate a successful modify() call for mark_as_read.
        self.fake_service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {}

        # Patch rules.authenticate and rules.build so that apply_rules() uses our fake service.
        self.auth_patcher = patch('rules.authenticate', return_value=MagicMock())
        self.auth_patcher.start()
        self.build_patcher = patch('rules.build', return_value=self.fake_service)
        self.build_patcher.start()

    def tearDown(self):
        self.sqlite_patcher.stop()
        self.auth_patcher.stop()
        self.build_patcher.stop()
        self.conn.close()
        if os.path.exists('rules.json'):
            os.remove('rules.json')

    def test_update_rules_mark_as_read(self):
        """
        Unit Test:
        - Tests that update_rules() correctly adds a rule to mark emails as read.
        """
        rules.update_rules('test@example.com', 'mark_as_read')
        with open('rules.json', 'r') as f:
            data = json.load(f)
        self.assertTrue(any(rule['actions'][0] == 'mark_as_read' for rule in data['rules']))

    def test_apply_rules_mark_as_read(self):
        """
        Integration Test:
        - Inserts a dummy unread email.
        - Adds a rule for marking emails as read.
        - Calls apply_rules(), which should trigger the Gmail API modify() call.
        - Verifies that modify() is called with the expected parameters.
        """
        rules.update_rules('test@example.com', 'mark_as_read')
        rules.apply_rules()
        self.fake_service.users.return_value.messages.return_value.modify.assert_called_with(
            userId='me', id='1', body={"removeLabelIds": ["UNREAD"]}
        )

if __name__ == '__main__':
    unittest.main()
