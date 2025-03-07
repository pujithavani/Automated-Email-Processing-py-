import customtkinter as ctk
import tkinter.filedialog as fd
from fetch import fetch_emails
from rules import apply_rules, add_rule

class MailManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mail Manager (SQLite Edition)")
        self.geometry("750x550")
        ctk.set_appearance_mode("dark")  # Options: "dark", "light", "system"
        ctk.set_default_color_theme("blue")
        self.build_ui()

    def build_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # ------------------- CONFIGURATION SECTION -------------------
        config_frame = ctk.CTkFrame(main_frame)
        config_frame.pack(pady=5, fill="x")

        # Credentials JSON
        ctk.CTkLabel(config_frame, text="Credentials JSON:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.creds_var = ctk.StringVar(value="credentials.json")
        self.creds_entry = ctk.CTkEntry(config_frame, textvariable=self.creds_var)
        self.creds_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        browse_btn = ctk.CTkButton(config_frame, text="Browse", command=self.browse_credentials)
        browse_btn.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # SQLite DB Path
        ctk.CTkLabel(config_frame, text="SQLite DB Path:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.db_var = ctk.StringVar(value="emails.db")
        self.db_entry = ctk.CTkEntry(config_frame, textvariable=self.db_var)
        self.db_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        # Retrieval Method
        ctk.CTkLabel(config_frame, text="Retrieval Method:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.method_var = ctk.StringVar(value="number")
        self.method_option = ctk.CTkOptionMenu(config_frame, values=["number", "timestamp"], variable=self.method_var)
        self.method_option.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Number of Emails / Date
        ctk.CTkLabel(config_frame, text="Number or Date:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.num_var = ctk.StringVar(value="10")
        self.num_entry = ctk.CTkEntry(config_frame, textvariable=self.num_var)
        self.num_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")

        # Fetch Emails Button
        fetch_btn = ctk.CTkButton(config_frame, text="Fetch Emails", command=self.on_fetch_emails)
        fetch_btn.grid(row=4, column=1, padx=5, pady=5, sticky="we")

        config_frame.columnconfigure(1, weight=1)

        # ------------------- RULE SECTION -------------------
        rule_frame = ctk.CTkFrame(main_frame)
        rule_frame.pack(pady=5, fill="x")

        # Sender Email for rule condition
        ctk.CTkLabel(rule_frame, text="Sender Email:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.sender_var = ctk.StringVar()
        self.sender_entry = ctk.CTkEntry(rule_frame, textvariable=self.sender_var)
        self.sender_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        # Action for rule
        ctk.CTkLabel(rule_frame, text="Action:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.action_var = ctk.StringVar(value="Mark as Read")
        self.action_option = ctk.CTkOptionMenu(rule_frame, values=["Mark as Read", "Mark as Unread", "Move to Label"], variable=self.action_var)
        self.action_option.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Folder/Label Name for Move action
        ctk.CTkLabel(rule_frame, text="Folder/Label Name:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.label_var = ctk.StringVar()
        self.label_entry = ctk.CTkEntry(rule_frame, textvariable=self.label_var)
        self.label_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # Add Rule and Apply Rules Buttons
        add_rule_btn = ctk.CTkButton(rule_frame, text="Add Rule", command=self.on_add_rule)
        add_rule_btn.grid(row=3, column=0, padx=5, pady=5, sticky="we")
        apply_rules_btn = ctk.CTkButton(rule_frame, text="Apply Rules", command=self.on_apply_rules)
        apply_rules_btn.grid(row=3, column=1, padx=5, pady=5, sticky="we")

        rule_frame.columnconfigure(1, weight=1)

        # ------------------- LOG / OUTPUT AREA -------------------
        self.log_text = ctk.CTkTextbox(main_frame, height=200)
        self.log_text.pack(pady=5, fill="both", expand=True)

    # ------------------------------------------------------------------
    # EVENT HANDLERS
    # ------------------------------------------------------------------
    def browse_credentials(self):
        file_path = fd.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if file_path:
            self.creds_var.set(file_path)
            self.log(f"Selected credentials file: {file_path}")

    def on_fetch_emails(self):
        credentials_file = self.creds_var.get()
        db_path = self.db_var.get()
        method = self.method_var.get()
        number_val = self.num_var.get()
        fetch_emails(
            credentials_file=credentials_file,
            db_path=db_path,
            retrieval_method=method,
            number_or_date=number_val,
            log_callback=self.log
        )

    def on_add_rule(self):
        sender_email = self.sender_var.get().strip()
        action_text = self.action_var.get()
        label_name = self.label_var.get().strip()

        if not sender_email:
            self.log("Please enter a Sender Email before adding a rule.")
            return

        # Build a single-condition rule: 'from' contains sender_email.
        conditions = [{"field": "from", "operator": "contains", "value": sender_email}]
        if action_text == "Mark as Read":
            final_action = "mark_as_read"
        elif action_text == "Mark as Unread":
            final_action = "mark_as_unread"
        else:  # "Move to Label"
            final_action = f"move_to_label:{label_name if label_name else 'Inbox'}"
        actions = [final_action]

        # Use add_rule function from rules.py
        add_rule("All", conditions, actions, log_callback=self.log)
        self.log("Rule added successfully.")

    def on_apply_rules(self):
        credentials_file = self.creds_var.get()
        db_path = self.db_var.get()
        apply_rules(credentials_file=credentials_file, db_path=db_path, log_callback=self.log)

    def log(self, msg):
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")

if __name__ == '__main__':
    app = MailManagerApp()
    app.mainloop()
