
# Dork-Eye — Advanced Dorking Tool 
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg) 
![License](https://img.shields.io/badge/license-MIT-green.svg) 
![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg) 
![DuckDuckGo](https://img.shields.io/badge/search-DuckDuckGo-orange.svg)

> **V1.0**

---

## 🧠 What is Dork-Eye?

`Dork-Eye` is an automated **dorking** tool that uses **DuckDuckGo** to find web resources exposed via OSINT techniques. It can identify indexed directories, restricted files, admin panels and other public vulnerabilities, all in an **anonymous and legal** way, avoiding CAPTCHAs and blocks typical of mainstream engines.

---

## ⚠️ Legal Disclaimer

> **This tool is intended for educational, research and authorized testing purposes only.**

Use of it unethically or against local laws may constitute a crime. The author **disclaims all liability** for improper use.

---

## ✨ Features

- Search via **DuckDuckGo** (no CAPTCHA block)
- Single input or from **dork file**
- Save results to **.txt file**
- **Advanced visualization** with `rich`
- Simple and powerful **CLI interface**
- Completely written in **Python 3**

---

## ⚙️ Requirements

- Python 3.8 or higher
- Required modules:
```bash
pip install -r requirements.txt

requirements.txt

rich
duckduckgo-search

🚀 How to use

Single dork search

python3 dork-eye.py -d "inurl:admin login" -o admin_panels -c 100

Dork file search

python3 dork-eye.py -d dorks.txt -o results -c 50

Options

Flag Description Mandatory
-d / --dork Single dork or .txt file with dork Yes
-o / --output Output file name (without extension) No
-c / --count Number of results per dork (default 50) No

📂 Output Example

File results.txt:

1. https://example.com/admin/login.php
2. https://vulnerable.site/index.php?id=1
3. https://ftp.example.org/files/
...

📌 Project Structure

dork-eye/
├── dork-eye.py
├── requirements.txt
├── README.md
├── dorks.txt # (optional)
└── results.txt # (generated output)

🔒 Best Practice
• Use in test environments or with written permission
• Integrate with vulnerability scanners (e.g. Nikto, Nuclei)
• Automate with cronjob for periodic OSINT tests

🧩 Future Ideas
• CSV / JSON export
• Active scanner of found URLs
• Support for Bing / Brave / Qwant
• Advanced filters by file type or domain
• Interactive GUI or TUI with textual

🧑‍💻 Author

xPloits3c
Contact: anon@protonmail.com (fictitious, you can edit it)

📜 License

Distributed under MIT License

⭐ Support the project

Do you like this tool? Leave a ⭐ on GitHub and contribute!

---

Let me know if you want me to also generate the `requirements.txt` file, the MIT LICENSE
