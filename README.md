![image](https://github.com/user-attachments/assets/989dc234-2c32-4280-9165-42ebd87b53bc)

# DorkEye | Advanced Dorking Tool 
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg) 
![License](https://img.shields.io/badge/license-MIT-green.svg) 
![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg) 
![DuckDuckGo](https://img.shields.io/badge/search-DuckDuckGo-orange.svg)
![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye)
---

## 🧠 What is Dork-Eye?
- Is an automated **dorking** tool that uses **DuckDuckGo** to find web resources exposed via OSINT techniques.
-  It can identify indexed directories, restricted files, admin panels and other public vulnerabilities, all in an **anonymous and legal** way, avoiding CAPTCHAs and blocks typical of mainstream engines.
> Search Engine
-  Using DuckDuckGo (via DDGS()) allows to bypass limitations imposed by Google, making the tool more resilient and anonymous.
> Why DorkEye?
-  It supports multiple dorks per command string allowing you to get better result in less time, also saves results without double links, fast, secure!

![image](https://github.com/user-attachments/assets/d2d9699b-f649-47c6-9fc2-7ac1a6213ba0)



## ✨ Features

- Search via **DuckDuckGo** (no CAPTCHA block)
- Single input or from **dork file**
- Save results to **.csv file**
- **Advanced visualization** with `rich`

---

## ⚙️ Install DorkEye 
```bash
 git clone https://github.com/xPloits3c/DorkEye.git
 cd DorkEye
 pip install -r requirements.txt
```
## ⚙️ Requirements

- Python 3.9+ > "Make sure you have the latest version of python installed."
-  If not installed, you can do it with:
       `sudo apt update`
       `sudo apt install python3`
- Modules:
 `rich` and `duckduckgo-search`

## 🚀 How to use

•  Single Dork search
```
python3 dorkeye.py -d "inurl:admin login" -o admin_panels -c 100
```
•  Multiple Dork search
```
python3 dorkeye.py -d "site:.ru inurl:russian_cv filetype:pdf" -o RusCV -c 100
python3 dorkeye.py -d dorkeye_dorks.txt -c 60 -o dorkResults
```
•  Options
 - `-d` / --dork Single dork or .txt file with dork
 - `-o` / --output Output file name
 - `-c` / --count Number of results per dork 

![image](https://github.com/user-attachments/assets/3773f7d4-60a4-4a70-90c6-5b44b5281d3f)


## 📂 Output Example
 File `results.csv`:

1. https://example.com/admin/login.php
2. https://vulnerable.site/index.php?id=1
3. https://ftp.example.org/files/

![image](https://github.com/user-attachments/assets/790f4edf-1ec7-4dcc-8735-2adbf4766eb5)

## 📌 Project Structure

- `DorkEye/`
- `├── dorkeye.py`
- `├── requirements.txt`
- `├── README.md`
- `├── dorks.txt # (optional)`
- `└── results.csv # (generated output)`

## 🔒 Best Practice
- Use in test environments or with written permission
- Integrate with vulnerability scanners (e.g. SQLMap, XSStrike, Nikto, Nuclei)
- Automate with cronjob for periodic OSINT tests

## 🧩 Future Ideas
- Active scanner on file output
- Advanced filters by file type or domain
- Interactive GUI or TUI with textual

---

## ⚠️ Legal Disclaimer

-  This tool is intended for educational, research and authorized testing purposes only.
-  Use of it unethically or against local laws may constitute a crime.
-  The author disclaims all liability for improper use.

---


## 🧑‍💻 Author

- xPloits3c
- Contact: whitehat.report@onionmail.org

## 📜 License
Distributed under MIT License

<p><a href="https://github.com/xPloits3c/MetaByte" target="_blank">
  <button style="padding:10px 15px; font-size:16px; background-color:#0366d6; color:white; border:none; border-radius:5px;">
    Visit MetaByte on GitHub
  </button>
</a></p>
---
