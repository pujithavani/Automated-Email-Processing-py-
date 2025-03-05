import json
import sqlite3
from googleapiclient.discovery import build
from authenticate import authenticate

# Function to update rules.json dynamically
def update_rules(sender_email, action, label_name=None):
    with open('rules.json', 'r') as file:
        rules_data = json.load(file)
    
    new_rule = {
        "predicate": "All",
        "conditions": [
            {
                "field": "from",
                "operator": "contains",
                "value": sender_email
            }
        ],
        "actions": [action] if action != "move_to_label" else [f"move_to_label:{label_name}"]
    }

    rules_data["rules"].append(new_rule)

    with open('rules.json', 'w') as file:
        json.dump(rules_data, file, indent=4)

    print(f"Rule added: {new_rule}")


# Function to apply email rules
def apply_rules():
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)

    with open('rules.json', 'r') as file:
        rules_data = json.load(file)

    cursor.execute('SELECT id, sender FROM emails WHERE is_read = 0')
    emails = cursor.fetchall()

    for email_data in emails:
        email_id, sender = email_data
        for rule in rules_data['rules']:
            if any(condition["value"] in sender for condition in rule["conditions"]):
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
                    
                    elif action == "add_star":
                        service.users().messages().modify(userId='me', id=email_id, body={"addLabelIds": ["STARRED"]}).execute()
                        print(f"Starred email {email_id}.")

    conn.close()


# User menu to add new rules
if __name__ == '__main__':
    print("Select an action:")
    print("1: Mark emails from a sender as read")
    print("2: Mark emails from a sender as unread")
    print("3: Move emails from a sender to a label")
    print("4: Star emails from a sender")

    choice = input("Enter your choice (1/2/3/4): ")

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
