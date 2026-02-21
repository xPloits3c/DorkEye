<div align="center">
<img width="2048" height="2048" alt="image" src="https://github.com/user-attachments/assets/6c253be8-f8ce-445e-bc3d-1c21eacbf567" />
</div>

---

🦅 *DorkEye* > `*I don't hack systems, I expose their secrets.*` <

<!-- ── Row 1: Project identity ── -->
![Python](https://img.shields.io/badge/Python-3.9%2B-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)
![Search](https://img.shields.io/badge/Search-DuckDuckGo-FF6600?style=flat-square&logo=duckduckgo&logoColor=white)

<!-- ── Row 2: Live stats ── -->
![Views](https://img.shields.io/badge/DorkEye_Views-4%2C791-blue?style=flat-square&logo=github)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat-square&logo=github&label=Stars&color=yellow)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye?style=flat-square&logo=github&label=Forks&color=lightgrey)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye?style=flat-square&logo=github&label=Issues&color=brightgreen)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye?style=flat-square&logo=github&label=Last+Commit&color=informational)

<!-- ── Row 3: Community ── -->
[![Telegram](https://img.shields.io/badge/Join-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white)](#)

---

</div>

## What is DorkEye
**DorkEye** is an advanced, automated **Dorking** script to identify exposed web resources using Open Source Intelligence techniques.
## Read full documents:

[![INSTALL GUIDE](https://img.shields.io/badge/FULL-INSTALL%20GUIDE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/INSTALL.md)
[![USAGE](https://img.shields.io/badge/FULL-USAGE%20GUIDE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/USAGE.md)
[![DORKS_GENERATOR](https://img.shields.io/badge/Dork-Generator%20GUIDE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/DORK_GENERATOR.md)

![de_start_sql](https://github.com/user-attachments/assets/a34627b6-0862-4c02-91f2-3fe75fdbb516)

It helps discover:
- Indexed directories  
- Sensitive files  
- Admin panels  
- Databases & backups  
- Misconfigurations and leaked credentials  

![image](https://github.com/user-attachments/assets/6609eed1-cb04-48b4-909a-802ec0055b96)

---

## Why DorkEye

- ✅ Bypass CAPTCHA and rate‑limiting
- ✅ Maintain anonymity and avoid IP blocking
- ✅ Clean and unfiltered search results
- ✅ Advanced analysis and automated SQLi testing
- ✅ Continue Dorking for hours, DorkEye won’t get banned.
---

## What’s New

### DORK GENERATOR
Generates structured Google dorks using a modular YAML template engine.

### Automated SQL Injection Testing
- Error‑based SQLi  
- Boolean‑based blind SQLi  
- Time‑based blind SQLi  
- Vulnerability confidence scoring  

### Advanced Analysis
- File metadata inspection (size, type, accessibility)
- Intelligent deduplication
- YAML / JSON configuration support

### Stealth & Fingerprinting
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
-    `.csv .json .txt .html`
<img width="1918" height="1013" alt="dorkeye_html_results" src="https://github.com/user-attachments/assets/ecee13e2-3581-4def-8098-52b3d96b805a" />
<img width="1918" height="926" alt="dorkeye_html_results_vuln" src="https://github.com/user-attachments/assets/bc13d89d-5c7f-4c2a-b2a7-cfb194cfa79d" />

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

## 🎯 Usage 
[![USAGE](https://img.shields.io/badge/READ%20FULL-USAGE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/USAGE.md)
<img width="1142" height="906" alt="de_run" src="https://github.com/user-attachments/assets/1968c10d-1241-4f34-bae9-411e49aaccb5" />

🔹 # Basic search
```bash
python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Dork Generator + Detection
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
-   **This tool is for educational, research, and authorized security testing only.**
-   **Unauthorized access is illegal.**
-   **The author is not responsible for misuse.**
    
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
