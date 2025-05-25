![image](https://github.com/user-attachments/assets/989dc234-2c32-4280-9165-42ebd87b53bc)

# DorkEye — Advanced Dorking Tool 
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg) 
![License](https://img.shields.io/badge/license-MIT-green.svg) 
![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg) 
![DuckDuckGo](https://img.shields.io/badge/search-DuckDuckGo-orange.svg)

---
![Repo View Counter](https://profile-counter.glitch.me/DorkEye/count.svg)
## 🧠 What is Dork-Eye?

> `Dork-Eye` is an automated **dorking** tool that uses **DuckDuckGo** to find web resources exposed via OSINT techniques.
-  It can identify indexed directories, restricted files, admin panels and other public vulnerabilities, all in an **anonymous and legal** way, avoiding CAPTCHAs and blocks typical of mainstream engines.
> Search Engine
-  Using DuckDuckGo (via DDGS()) allows to bypass limitations imposed by Google, making the tool more resilient and anonymous.

![image](https://github.com/user-attachments/assets/fcfced00-9c36-4f55-b1a7-34b7fa76096a)

## ✨ Features

- Search via **DuckDuckGo** (no CAPTCHA block)
- Single input or from **dork file**
- Save results to **.txt file**
- **Advanced visualization** with `rich`
- Simple and powerful **CLI interface**
- Completely written in **Python 3**

---

## ⚙️ Requirements

- Python 3.8+
- Install modules:
```bash
 pip install -r requirements.txt
```
- Modules:
 `rich` and `duckduckgo-search`

## 🚀 How to use

•  Single Dork search
```
python3 dorkeye.py -d "inurl:admin login" -o admin_panels -c 100
```
•  Multiple Dork search
```
python3 dorkeye.py -d "site:.ru inurl:uploads/cv filetype:pdf" -o RusCV -c 100
python3 dorkeye.py -d "site:.ru intext:email intext:password filetype:txt" -o RusEP -c 100
```
•  Dork file search
```
python3 dorkeye.py -d dorks.txt -o results -c 50
```
Options

Flag Description Mandatory
  `-d` / --dork Single dork or .txt file with dork Yes
  `-o` / --output Output file name
  `-c` / --count Number of results per dork 

![image](https://github.com/user-attachments/assets/7df8b28a-c02e-40cf-a85f-96ca395bccb2)

## 📂 Output Example
 File `results.txt`:

1. https://example.com/admin/login.php
2. https://vulnerable.site/index.php?id=1
3. https://ftp.example.org/files/
...

## 📌 Project Structure

- `dork-eye/`
- `├── dork-eye.py`
- `├── requirements.txt`
- `├── README.md`
- `├── dorks.txt # (optional)`
- `└── results.txt # (generated output)`

## 🔒 Best Practice
- Use in test environments or with written permission
- Integrate with vulnerability scanners (e.g. Nikto, Nuclei)
- Automate with cronjob for periodic OSINT tests

## 🧩 Future Ideas
- CSV / JSON export
- Active scanner of found URLs
- Support for Bing / Brave / Qwant
- Advanced filters by file type or domain
- Interactive GUI or TUI with textual

---

## ⚠️ Legal Disclaimer

> This tool is intended for educational, research and authorized testing purposes only.
> Use of it unethically or against local laws may constitute a crime. The author disclaims all liability for improper use.

---


## 🧑‍💻 Author

- xPloits3c
Contact: whitehat.report@onionmail.org

## 📜 License
Distributed under MIT License

## ⭐ Support the project
Do you like this tool? Leave a ⭐

## ! You might be interested in: **MetaByte** for cleaning and extracted urls with parameters.
 https://github.com/xPloits3c/MetaByte
---
