import json
import sqlite3
from googleapiclient.discovery import build
from authenticate import authenticate

def add_rule(predicate, conditions, actions, log_callback=print):
    """
    Adds a new rule to rules.json. The rule consists of an overall predicate (e.g. "All"),
    a list of conditions, and a list of actions.
    """
    rule_file = "rules.json"
    try:
        with open(rule_file, "r") as file:
            rules_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        rules_data = {"rules": []}
    
    new_rule = {
        "predicate": predicate,
        "conditions": conditions,
        "actions": actions
    }
    rules_data["rules"].append(new_rule)
    
    with open(rule_file, "w") as file:
        json.dump(rules_data, file, indent=4)
    
    log_callback(f"Rule added: {new_rule}")

def update_rules(sender_email, action, label_name=None):
    """
    Convenience function (for backward compatibility) to add a rule based on sender_email.
    """
    if action == "move_to_label":
        final_action = f"move_to_label:{label_name}"
    else:
        final_action = action

    condition = {
        "field": "from",
        "operator": "contains",
        "value": sender_email
    }
    add_rule("All", [condition], [final_action])
    print(f"Rule added via update_rules: {sender_email} -> {final_action}")

def apply_rules(credentials_file="credentials.json", db_path="emails.db", log_callback=print):
    """
    Applies rules from rules.json to all unread emails in the SQLite database.
    Uses the provided credentials file and database path.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    creds = authenticate(credentials_file)
    service = build('gmail', 'v1', credentials=creds)

    rule_file = "rules.json"
    try:
        with open(rule_file, "r") as file:
            rules_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        log_callback("No valid rules found in rules.json.")
        conn.close()
        return

    cursor.execute('SELECT id, sender FROM emails WHERE is_read = 0')
    emails = cursor.fetchall()

    for email_id, sender in emails:
        for rule in rules_data.get("rules", []):
            # Check if any condition is met (case-insensitive)
            if any(condition.get("value", "").lower() in sender.lower() 
                   for condition in rule.get("conditions", [])):
                for action in rule.get("actions", []):
                    if action.startswith("move_to_label:"):
                        label_name = action.split(":", 1)[1]
                        labels_response = service.users().labels().list(userId='me').execute()
                        labels = labels_response.get('labels', [])
                        label_id = next((label['id'] for label in labels 
                                         if label['name'].lower() == label_name.lower()), None)
                        if label_id:
                            service.users().messages().modify(
                                userId='me', id=email_id, body={"addLabelIds": [label_id]}
                            ).execute()
                            log_callback(f"Moved email {email_id} to label {label_name}.")
                        else:
                            log_callback(f"Label '{label_name}' not found. Create it manually in Gmail.")
                    elif action == "mark_as_read":
                        service.users().messages().modify(
                            userId='me', id=email_id, body={"removeLabelIds": ["UNREAD"]}
                        ).execute()
                        log_callback(f"Marked email {email_id} as read.")
                    elif action == "mark_as_unread":
                        service.users().messages().modify(
                            userId='me', id=email_id, body={"addLabelIds": ["UNREAD"]}
                        ).execute()
                        log_callback(f"Marked email {email_id} as unread.")
                    elif action == "add_star":
                        service.users().messages().modify(
                            userId='me', id=email_id, body={"addLabelIds": ["STARRED"]}
                        ).execute()
                        log_callback(f"Starred email {email_id}.")
    conn.close()

if __name__ == '__main__':
    print("Select an action:")
    print("1: Mark emails from a sender as read")
    print("2: Mark emails from a sender as unread")
    print("3: Move emails from a sender to a label")
    print("4: Star emails from a sender")

    choice = input("Enter your choice (1/2/3/4): ").strip()

    if choice in ["1", "2", "3", "4"]:
        sender_email = input("Enter sender email to filter: ").strip()

        if choice == "1":
            update_rules(sender_email, "mark_as_read")
        elif choice == "2":
            update_rules(sender_email, "mark_as_unread")
        elif choice == "3":
            label_name = input("Enter label name to move emails to: ").strip()
            update_rules(sender_email, "move_to_label", label_name)
        elif choice == "4":
            update_rules(sender_email, "add_star")
        
        apply_rules()
    else:
        print("Invalid choice. Please enter 1, 2, 3, or 4.")
