<div align="center">
<img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/2d41cfd5-cd4d-49ab-b5bf-3306966ed0c5" />
</div>

# 🔍 DorkEye — Advanced OSINT Dorking Tool

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

**DorkEye** is an advanced, automated **OSINT dorking tool** that leverages **DuckDuckGo** to identify exposed web resources using Open Source Intelligence techniques.

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

<img width="1024" height="1536" alt="whatisde" src="https://github.com/user-attachments/assets/f9fbd30b-60cb-4343-ae47-24e07b751c4c" />

---

## ✨ What’s New

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

### 💾 Export Formats
- CSV
- JSON
- Interactive HTML reports

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

![image](https://github.com/user-attachments/assets/15ac9798-7cf3-487b-9a75-bd52b9de3eec)


```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
sudo chmod +x setup.sh
./setup.sh
```

---

## ▶️ Test

<img width="1547" height="755" alt="de-h" src="https://github.com/user-attachments/assets/4b33c089-8502-4408-95be-d401e852c380" />

```bash
# Help:
python dorkeye.py -h
# Deactivate:
deactivate
# Remove environment:
rm -rf dorkeye_env
```
---

## 🚀 Usage 

[![USAGE](https://img.shields.io/badge/READ%20FULL-USAGE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/USAGE.md)

![00](https://github.com/user-attachments/assets/bb038de4-e822-491c-9862-c39008bdf6c9)
![01](https://github.com/user-attachments/assets/5bb193fd-5265-4ac7-9b27-1a8ffcd84ad1)

```bash
# Basic search
python3 dorkeye.py -d "inurl:admin" -o results

# SQLi + stealth
python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan

# Fast scan
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results
```

---

## 📁 Project Structure

```
DorkEye/
├── dorkeye.py
├── requirements.txt
├── http_fingerprints.json
├── setup.sh / setup.bat
├── INSTALL.md
├── dorkeye_config.yaml
├── Dump/
│   ├── *.csv
│   ├── *.json
│   └── *.html
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

## ⚠️ ![WARNING](https://img.shields.io/badge/Legal%20Disclaimer-red)

This tool is for **educational, research, and authorized security testing only**.  
Unauthorized access is illegal. The author is not responsible for misuse.

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
