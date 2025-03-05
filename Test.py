# unit.py
import base64
import json
import os
import sqlite3
import tempfile
import unittest
from importlib import reload
from unittest.mock import patch, MagicMock, mock_open

# Dummy rules JSON for tests that only need the mark_as_read rule.
DUMMY_RULES_JSON_READ = json.dumps({
    "rules": [
        {
            "conditions": [
                {"field": "subject", "operator": "contains", "value": "Test"}
            ],
            "predicate": "Any",
            "actions": ["mark_as_read"]
        }
    ]
})

# For integration testing we include an extra rule.
DUMMY_RULES_JSON_INTEGRATION = json.dumps({
    "rules": [
        {
            "conditions": [
                {"field": "subject", "operator": "contains", "value": "Test"}
            ],
            "predicate": "Any",
            "actions": ["mark_as_read"]
        },
        {
            "conditions": [
                {"field": "subject", "operator": "contains", "value": "nykaa-promotions"}
            ],
            "predicate": "Any",
            "actions": ["move_to_label:nykaa-promotions"]
        }
    ]
})


class TestFetchEmails(unittest.TestCase):
    def setUp(self):
        # Patch sqlite3.connect in the fetch module so that when the module is reloaded, 
        # it creates an in-memory database.
        patcher = patch('fetch.sqlite3.connect', return_value=sqlite3.connect(':memory:'))
        self.mock_connect = patcher.start()
        self.addCleanup(patcher.stop)
        # Reload the module so that the module-level connection uses our patched sqlite3.connect.
        import fetch
        reload(fetch)
        self.fetch_mod = fetch

        # Create the emails table in the in-memory DB.
        conn = self.fetch_mod.conn
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

    def tearDown(self):
        # Close the connection to release the in-memory DB.
        self.fetch_mod.conn.close()

    @patch('fetch.build')
    @patch('fetch.authenticate')
    def test_fetch_emails_inserts_email(self, mock_authenticate, mock_build):
        dummy_creds = "dummy_credentials"
        mock_authenticate.return_value = dummy_creds

        # Dummy Gmail API responses.
        dummy_message_id = '12345'
        dummy_list_response = {'messages': [{'id': dummy_message_id}]}
        dummy_message_response = {
            'internalDate': '1610000000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test Email'}
                ],
                'parts': [{
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'Hello, world!').decode('utf-8')
                    }
                }]
            }
        }

        # Setup dummy Gmail API service chain.
        dummy_messages_resource = MagicMock()
        dummy_messages_resource.list.return_value.execute.return_value = dummy_list_response
        dummy_messages_resource.get.return_value.execute.return_value = dummy_message_response
        dummy_users_resource = MagicMock()
        dummy_users_resource.messages.return_value = dummy_messages_resource
        dummy_service = MagicMock()
        dummy_service.users.return_value = dummy_users_resource
        mock_build.return_value = dummy_service

        # Call fetch_emails.
        self.fetch_mod.fetch_emails()

        # Verify that the email was inserted.
        conn = self.fetch_mod.conn
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, subject, received_at, message FROM emails")
        result = cursor.fetchone()

        self.assertIsNotNone(result, "No email record inserted")
        email_id, sender, subject, received_at, message = result
        self.assertEqual(email_id, dummy_message_id)
        self.assertEqual(sender, 'sender@example.com')
        self.assertEqual(subject, 'Test Email')
        self.assertEqual(received_at, '1610000000000')
        self.assertEqual(message, 'Hello, world!')


class TestApplyRules(unittest.TestCase):
    def setUp(self):
        # Create our own in-memory database.
        self.connection = sqlite3.connect(':memory:')
        # Patch sqlite3.connect in the rules module to always return our connection.
        patcher = patch('rules.sqlite3.connect', return_value=self.connection)
        self.mock_connect = patcher.start()
        self.addCleanup(patcher.stop)
        # Patch open so that when rules.json is read at module load time, it uses our dummy JSON.
        patcher_open = patch('rules.open', mock_open(read_data=DUMMY_RULES_JSON_READ))
        self.mock_open = patcher_open.start()
        self.addCleanup(patcher_open.stop)
        import rules
        reload(rules)
        self.rules_mod = rules

        # Create the emails table in our connection.
        cursor = self.connection.cursor()
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
        # Insert a test email whose subject should trigger the rule.
        cursor.execute('INSERT INTO emails (id, sender, subject, received_at, message, is_read) VALUES (?, ?, ?, ?, ?, ?)',
                       ('email_1', 'someone@example.com', 'This is a Test message', '1610000000000', 'Hello', 0))
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    @patch('rules.build')
    @patch('rules.authenticate')
    def test_apply_rules_marks_email_as_read(self, mock_authenticate, mock_build):
        dummy_creds = "dummy_credentials"
        mock_authenticate.return_value = dummy_creds

        # Dummy label for UNREAD.
        dummy_labels = [{'id': 'LABEL_UNREAD', 'name': 'UNREAD'}]

        # Setup dummy Gmail API service.
        dummy_messages_resource = MagicMock()
        dummy_messages_resource.modify.return_value.execute.return_value = {}
        dummy_users_resource = MagicMock()
        dummy_users_resource.labels.return_value.execute.return_value = {'labels': dummy_labels}
        dummy_users_resource.messages.return_value = dummy_messages_resource
        dummy_service = MagicMock()
        dummy_service.users.return_value = dummy_users_resource
        mock_build.return_value = dummy_service

        # Run apply_rules.
        self.rules_mod.apply_rules()

        # Verify that the Gmail API call was made to remove the UNREAD label.
        dummy_messages_resource.modify.assert_called_with(
            userId='me',
            id='email_1',
            body={"removeLabelIds": ["UNREAD"]}
        )


class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory so that emails.db and rules.json are in an isolated location.
        self.test_dir = tempfile.TemporaryDirectory()
        self.orig_dir = os.getcwd()
        os.chdir(self.test_dir.name)

        # Write our dummy rules.json file for integration testing.
        with open('rules.json', 'w') as f:
            f.write(DUMMY_RULES_JSON_INTEGRATION)

        # Save the original sqlite3.connect.
        self.original_sqlite_connect = sqlite3.connect

        # Patch sqlite3.connect in both fetch and rules modules.
        # Use a lambda that creates a file-based DB in our temporary directory.
        self.db_patcher_fetch = patch('fetch.sqlite3.connect',
                                        side_effect=lambda db_name: self.original_sqlite_connect(os.path.join(self.test_dir.name, db_name)))
        self.db_patcher_rules = patch('rules.sqlite3.connect',
                                        side_effect=lambda db_name: self.original_sqlite_connect(os.path.join(self.test_dir.name, db_name)))
        self.mock_connect_fetch = self.db_patcher_fetch.start()
        self.mock_connect_rules = self.db_patcher_rules.start()

        # Reload the modules so that they use the patched sqlite3.connect.
        import importlib
        import fetch
        import rules
        reload(fetch)
        reload(rules)
        self.fetch_mod = fetch
        self.rules_mod = rules

        # Create the emails table in the file-based database.
        conn = self.original_sqlite_connect(os.path.join(self.test_dir.name, 'emails.db'))
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

    def tearDown(self):
        # Close module-level connections if open.
        try:
            self.fetch_mod.conn.close()
        except Exception:
            pass
        try:
            self.rules_mod.conn.close()
        except Exception:
            pass

        self.db_patcher_fetch.stop()
        self.db_patcher_rules.stop()
        os.chdir(self.orig_dir)
        self.test_dir.cleanup()

    @patch('fetch.build')
    @patch('fetch.authenticate')
    @patch('rules.build')
    @patch('rules.authenticate')
    def test_full_flow(self, mock_auth_rules, mock_build_rules, mock_auth_fetch, mock_build_fetch):
        dummy_creds = "dummy_credentials"
        mock_auth_fetch.return_value = dummy_creds
        mock_auth_rules.return_value = dummy_creds

        # Setup dummy Gmail API for fetch_mod.
        dummy_message_id = 'int_msg_1'
        dummy_list_response = {'messages': [{'id': dummy_message_id}]}
        dummy_message_response = {
            'internalDate': '1610000000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'integration@example.com'},
                    {'name': 'Subject', 'value': 'Integration Test Email'}
                ],
                'parts': [{
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'Integration test body').decode('utf-8')
                    }
                }]
            }
        }

        # Setup dummy service for fetch_mod.
        dummy_messages_resource_fetch = MagicMock()
        dummy_messages_resource_fetch.list.return_value.execute.return_value = dummy_list_response
        dummy_messages_resource_fetch.get.return_value.execute.return_value = dummy_message_response
        dummy_users_resource_fetch = MagicMock()
        dummy_users_resource_fetch.messages.return_value = dummy_messages_resource_fetch
        dummy_service_fetch = MagicMock()
        dummy_service_fetch.users.return_value = dummy_users_resource_fetch
        mock_build_fetch.return_value = dummy_service_fetch

        # Setup dummy service for rules_mod.
        dummy_labels = [{'id': 'LABEL_UNREAD', 'name': 'UNREAD'}]
        dummy_messages_resource_rules = MagicMock()
        dummy_messages_resource_rules.modify.return_value.execute.return_value = {}
        dummy_users_resource_rules = MagicMock()
        dummy_users_resource_rules.labels.return_value.execute.return_value = {'labels': dummy_labels}
        dummy_users_resource_rules.messages.return_value = dummy_messages_resource_rules
        dummy_service_rules = MagicMock()
        dummy_service_rules.users.return_value = dummy_users_resource_rules
        mock_build_rules.return_value = dummy_service_rules

        # Run fetch_mod.fetch_emails to insert an email.
        self.fetch_mod.fetch_emails()

        # Verify that the email was inserted.
        conn = self.original_sqlite_connect(os.path.join(self.test_dir.name, 'emails.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, subject, message, is_read FROM emails")
        email_record = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(email_record, "Email record not found in integration test")
        self.assertEqual(email_record[0], dummy_message_id)
        self.assertEqual(email_record[1], 'integration@example.com')
        self.assertEqual(email_record[2], 'Integration Test Email')
        self.assertEqual(email_record[3], 'Integration test body')
        self.assertEqual(email_record[4], 0)

        # Run rules_mod.apply_rules to process the email.
        self.rules_mod.apply_rules()

        # Verify that the rules-modified Gmail API call was made to mark the email as read.
        dummy_messages_resource_rules.modify.assert_called_with(
            userId='me',
            id=dummy_message_id,
            body={"removeLabelIds": ["UNREAD"]}
        )


if __name__ == '__main__':
    unittest.main()
