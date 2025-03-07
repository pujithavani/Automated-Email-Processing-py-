

A brief and clear description of your project.
<h1 align="center"> Automated Email Processing  using Python</h1>

<p align="center">
  <img src="image.png" width="200">
</p>

<p align="center">
  <b>A brief description of the project, its purpose, and what it aims to achieve.</b>
</p>

---

## 📖 Table of Contents
1. [Introduction]
2. [Features]
3. [Installation]
4. [Usage]
5. [Technologies Used]


---

## 🚀 Introduction
<p>This project is a standalone Python application that integrates with the Gmail API using OAuth for authentication. It fetches emails from your Gmail inbox and stores them in a local SQLite database. The application also allows you to process these emails based on a set of dynamic, rule-based operations defined in a JSON file. A graphical user interface (GUI) is provided using CustomTkinter for easy interaction, and a comprehensive test suite is included for ensuring the functionality of the system.</p>

## 🔥 Features
- ✅ Gmail API Integration:Authenticate to Gmail using OAuth (credentials obtained from GCP)
- ✅ Email Fetching:Retrieve a list of emails from your Gmail inbox and store them in an SQLite database.
- ✅ Rule-Based Email Processing:Define dynamic rules (conditions and actions) stored in a JSON file. Supported    actions include marking emails as read/unread and moving emails to specified labels.
- ✅ Testing:A set of unit and integration tests (in test.py) validate core functionalities.
- ✅Graphical User Interface (GUI):A modern GUI built with CustomTkinter allows users to configure credentials, set fetching parameters, add rules, and apply them directly.

---

## 💻 Installation
Follow these steps to install and set up the project:

```sh
# Clone the repository

git clone https://github.com/pujithavani/Automated-Email-Processing-py-

# Navigate to the project directory
cd https://github.com/pujithavani/Automated-Email-Processing-py-

# Install dependencies (for Python projects)
pip install -r requirements.txt

# Install dependencies (for Node.js projects)
npm install


#Obtain Credentials: go to google cloud platform
Create OAuth credentials and download the credentials.json file.
Place the credentials.json file in the project root (or browse to it using the GUI).
```

---

## 🛠 Usage
How to run the project:

```sh
# Run the Python script
python gui.py

-Browse and select your credentials.json.
-Specify the SQLite database path (default: emails.db).
-Choose the retrieval method (either by number of emails or a timestamp).
-Click Fetch Emails to retrieve emails from your inbox.
-Define rules by entering a sender email and selecting an action (mark as read/unread or move to a label).
-Click Add Rule to save the rule, then Apply Rules to process unread emails accordingly.
-CLI Mode:python fetch.py
-python rules.py
-Running Tests: Execute the test suite by running:python test.py
```

---

## ⚙️ Technologies Used
- **Programming Languages:** Python 3.12: The primary programming language.
- **Gmail API & OAuth:** Integration with Gmail using Google's official API client for authentication and email operations.
- **SQLite:** A lightweight relational database to store fetched emails.
- **CustomTkinter:**A modern UI library built on Tkinter for creating an attractive and functional GUI.
- **Unit/Integration:** Implemented using Python’s built-in unittest framework.

---

## 📸 Screenshots
Include screenshots of your project:

![Screenshot](C:\my proj\screenshots)
---

## 🏷 Contact
For any questions or feedback, contact me at 221501108@rajalakshmi.edu.in@example.com**.

