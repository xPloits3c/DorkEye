<div align="center">
<img width="2048" height="2048" alt="image" src="https://github.com/user-attachments/assets/6c253be8-f8ce-445e-bc3d-1c21eacbf567" />
</div>

---

# 🦅 DorkEye 

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg)
![DuckDuckGo](https://img.shields.io/badge/search-DuckDuckGo-orange.svg)
![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye)
[![Join Telegram](https://img.shields.io/badge/Join%20Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/DorkEye)

---

> 🐲 *I don't hack systems, i expose their secrets.*

## 🧠 What is DorkEye

**DorkEye** is an advanced, automated **Dorking** script in python language that leverages **DuckDuckGo** to identify exposed web resources using Open Source Intelligence techniques.

![de_start_sql](https://github.com/user-attachments/assets/a34627b6-0862-4c02-91f2-3fe75fdbb516)

It helps discover:
- Indexed directories  
- Sensitive files  
- Admin panels  
- Databases & backups  
- Misconfigurations and leaked credentials  

![image](https://github.com/user-attachments/assets/6609eed1-cb04-48b4-909a-802ec0055b96)
---

## ❓ Why DorkEye

- ✅ Bypass CAPTCHA and rate‑limiting
- ✅ Maintain anonymity and avoid IP blocking
- ✅ Clean and unfiltered search results
- ✅ Advanced analysis and automated SQLi testing
- ✅ Continue Dorking for hours, DorkEye won’t get banned.
---

## ✨ What’s New

### DORK GENERATOR
Generates structured Google dorks using a modular YAML template engine.

### 🧠 Automated SQL Injection Testing
- Error‑based SQLi  
- Boolean‑based blind SQLi  
- Time‑based blind SQLi  
- Vulnerability confidence scoring  

### 🔍 Advanced Analysis
- File metadata inspection (size, type, accessibility)
- Intelligent deduplication
- YAML / JSON configuration support

### 🎯 Stealth & Fingerprinting
- Realistic browser fingerprint rotation
- Dynamic delays to evade rate limits

### 📊 File Categorization
- 📄 Documents: `.pdf .doc .xls`
- 📦 Archives: `.zip .rar .7z`
- 🗄️ Databases: `.sql .sqlite`
- 💾 Backups: `.bak .old`
- ⚙️ Configs: `.conf .ini .yaml`
- 📜 Scripts: `.php .jsp`
- 🔑 Credentials: `.env .git`

### 💾 Export Formats available
- 📄 `.csv .json .txt .html`
---

## 🚀 Features

- 🔎 Smart single/multi‑dork execution
- 🚫 Extension blacklist & whitelist
- ⚡ Stealth mode & rate‑limit protection
- 📈 Real‑time statistics
- 🎨 Rich terminal UI
- 📦 Automatic installation
---

## 📦 Quick Install

[![INSTALL GUIDE](https://img.shields.io/badge/READ%20FULL-INSTALL%20GUIDE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/INSTALL.md)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
pip install -r requirements.txt
```
---
## Test
<img width="1468" height="896" alt="dev4 2 6_h" src="https://github.com/user-attachments/assets/9b7fb026-d052-44e2-a504-98a7ccb82d56" />

```bash
# Help:
python dorkeye.py -h
# Deactivate environment:
deactivate
# Remove environment:
rm -rf dorkeye_env
```
---

## 🚀 Usage 

[![USAGE](https://img.shields.io/badge/READ%20FULL-USAGE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/USAGE.md)

<img width="1013" height="596" alt="dg_search_priv" src="https://github.com/user-attachments/assets/b85bd006-4d73-484f-9dae-5ebf86e4968e" />

# 🔹 Basic search
```bash
python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # DORKS GENERATOR + DETECTION
```bash
python dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + stealth
```bash
python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Fast scan
```bash
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
---

## 📁 Project Structure
```
DorkEye/
│ ├── dorkeye.py
│ ├── dork_generator.py
│ ├── requirements.txt
│ ├── http_fingerprints.json
│ ├── INSTALL.md
│ ├── README.md
│ ├── dorkeye_config.yaml
│ /Templates/
│    ├── dorks_templates.yaml
│    ├── dorks_templates_research.yaml
│ /Dump/
│    ├── *.csv 
│    ├── *.json
│    ├── *.txt
│    └── *.html
```
---

## 🧩 Roadmap

- Multi‑threaded search
- Interactive TUI
- Browser extension
- Cloud integrations
- API support
- ML‑based dork optimization
---

## ⚠️  ![WARNING](https://img.shields.io/badge/Legal%20Disclaimer-red)
   🔹 This tool is for **educational, research, and authorized security testing only.**
   🔹 **Unauthorized access is illegal.**
   🔹 The **author is not responsible** for misuse.

---

## 📞 Contact

- **Author:** xPloits3c  
- **Email:** whitehat.report@onionmail.org  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Support

If you find DorkEye useful, please consider starring the repository 🌟
---

## 📜 License

MIT License © 2026 xPloits3c I.C.W.T
