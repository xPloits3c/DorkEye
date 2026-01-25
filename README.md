![537309991-f4f59199-d30f-4628-bb92-e6ccf43a6814](https://github.com/user-attachments/assets/ac547327-8c58-4792-bb0c-7f93798032d0)

## DorkEye | Advanced OSINT Dorking Tool 🔍

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg) 
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

## 🐧 Hello, i don't break system, i search for their secrets.

## What is DorkEye? 🧠
- DorkEye is an advanced osint automated dorking tool that leverages DuckDuckGo to discover exposed web resources through OSINT (Open Source Intelligence) techniques.
- It can identify indexed directories, sensitive files, admin panels, databases, backups, and other publicly accessible resources—all in an anonymous, efficient, and legal manner.

## Why DorkEye?
-  ✅ Bypass CAPTCHA and rate-limiting typical of mainstream search engines.
-  ✅ Maintain anonymity and privacy during searches, avoided IP blocks and detection mechanisms.
-  ✅ Access a clean, unfiltered index of web resources.
-  ✅ Dorking, analyze, extract metadata, test sqli vulnerability.

## What's New in v3? 
-  🧠 SQL Param Vuln Automatically Testing for SQL vulnerabilty after Potenzial SQLi Found 
-  🔍 Advanced File Metadata Analysis - Checks file accessibility, size, and content-type
-  🗂️ Global Deduplication - Removes duplicate URLs across all dorks
-  📈 Detailed Statistics - Comprehensive analytics and category breakdowns
-  ⚙️ Configuration Files - YAML/JSON config support for advanced customization
-  🎨 Rich Terminal UI - Beautiful progress bars and formatted output
-  🎯 File Analysis & Categorization - Automatically categorizes results by file type (documents, archives, databases, backups, configs, scripts, credentials)
-    --  📄 Documents	.pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx	Office documents, reports
-    --  📦 Archives	.zip, .rar, .tar, .gz, .7z, .bz2	Compressed files, backups
-    --  🗄️ Databases	.sql, .db, .sqlite, .mdb	Database dumps, exports
-    --  💾 Backups	.bak, .backup, .old, .tmp	Backup files, temp data
-    --  ⚙️ Configs	.conf, .ini, .yaml, .json, .xml	Configuration files
-    --  📜 Scripts	.php, .asp, .jsp, .sh, .bat, .ps1	Server-side scripts
-    --  🔑 Credentials	.env, .git, .svn, .htpasswd	Sensitive auth files
-  💾 Multiple Export Formats - CSV, JSON, and interactive HTML reports structured data with columns
-    -- URL, Title, Snippet, Dork, Timestamp
-    -- Extension, Category, File Size, Content Type
-    -- Accessibility Status, HTTP Status Code

## Feature	Description
-  🔎 Smart Dorking	Execute single or multiple dorks from files
-  🚫 Extension Filtering	Blacklist/whitelist specific file types
-  🔍 File Analysis	Check file size, content-type, and accessibility
-  🎯 Global Deduplication	Intelligent URL hash-based duplicate removal
-  ⚡ Rate Limit Protection	Smart delays to avoid blocking
-  📈 Detailed Statistics	Real-time metrics and category breakdowns
-  ⚙️ Config Support	YAML/JSON configuration files
-  🎨 Beautiful UI	Rich terminal interface with progress tracking
-  📦 Automatic Installation

# Quick Install
-  📦 For full installation instructions on all platforms, follow the complete guide:
    [![INSTALL GUIDE](https://img.shields.io/badge/READ%20THE-INSTALL%20GUIDE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/INSTALL.md)
  
<img width="1918" height="1000" alt="install_dorkeye" src="https://github.com/user-attachments/assets/ff0c7db3-ff46-42d6-9f14-6044a0957639" />
<img width="1918" height="972" alt="install_dorkeye0" src="https://github.com/user-attachments/assets/2d6e195f-2b83-40f6-91e4-4b3934cd365a" />

-     sudo apt update
-     sudo apt install -y python3 python3-pip python3-venv git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate
-     sudo chmod +x setup.sh
-     ./setup.sh

# Test:
-     cd DorkEye
-     source dorkeye_env/bin/activate
-     python dorkeye.py --help
<img width="1713" height="611" alt="help_dorkeye" src="https://github.com/user-attachments/assets/69bfea2f-08a6-400b-a501-e6e69cd3b521" />

# Exit Virtual environment:
-     cd DorkEye
-     deactivate
# Remove Virtual environment:
-     cd DorkEye
-     rm -rf venv

# 🚀 Usage
![result_dorkeye](https://github.com/user-attachments/assets/552a370e-3382-44d7-b1ca-fe5cb44d8500)

# Basic search
-     python3 dorkeye.py -d "inurl:admin" -o results
# Advanced search with SQLi testing
-     python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o scan
# Stealth mode for sensitive targets
-     python3 dorkeye.py -d dorks.txt --stealth --sqli -c 100 -o stealth_scan
# Filter specific file types
-     python3 dorkeye.py -d "site:target.com" --whitelist .pdf .doc .xls -o documents
# Fast search without file analysis
-     python3 dorkeye.py -d dorks.txt --no-analyze -c 50 -o quick_scan
# Generate config file
-     python3 dorkeye.py --create-config
## Simple search ##
-     python3 dorkeye.py -d "site:example.com filetype:pdf" -o results
## Multiple dorks from file ##
-     python3 dorkeye.py -d dorks.txt -c 100 -o output
## With file analysis
-     python3 dorkeye.py -d "inurl:admin" -o admin_pages

## Advanced Usage ##
# SQL Injection Test + Stealth
-     python dorkeye.py -d dorks.txt --stealth --sqli -o results
-     python dorkeye.py -d "site:example.com .php?id=" --sqli -o results
-     python dorkeye.py -d dorks.txt --sqli --stealth -c 100 -o scan
# Only PDF and Excel files
-     python3 dorkeye.py -d "filetype:pdf OR filetype:xls" --whitelist .pdf .xls .xlsx -o documents
# Exclude images
-     python3 dorkeye.py -d "site:.com" --blacklist .jpg .png .gif .svg -o no_images
# Custom configuration
-     python3 dorkeye.py -d dorks.txt --config custom_config.yaml -o results
# Fast mode (no file analysis)
-     python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results
-     -d, --dork	Single dork or file with dorks	-d "inurl:admin"
-     -o, --output	Output filename (no extension)	-o results
-     -c, --count	Results per dork (default: 50)	-c 100
-     --sqli Enable SQL Injection testing
-     --stealth Enable stealth mode (slower, safer)
-     --config	Configuration file (YAML/JSON)	--config config.yaml
-     --blacklist	Extensions to exclude	--blacklist .jpg .png
-     --whitelist	Only include these extensions	--whitelist .pdf .doc
-     --no-analyze	Skip file analysis (faster)	--no-analyze
-     --create-config	Generate sample config file	--create-config
-     --help	Show help message	--help
  
![photo_5_2026-01-18_20-13-17](https://github.com/user-attachments/assets/baff38ab-76ec-4080-a002-311e02029ccc) 

# Admin panels
-     inurl:admin intitle:login
-     inurl:administrator
-     site:.com inurl:wp-admin
# Sensitive files
-     filetype:sql "MySQL dump"
-     filetype:env DB_PASSWORD
-     filetype:log inurl:access.log
# Documents
-     site:.edu filetype:pdf "confidential"
-     site:.gov filetype:xls
-     inurl:uploads filetype:pdf
# Configuration files
-     filetype:conf intext:password
-     filetype:ini "database"
-     ext:xml inurl:config
#  Search for database dumps
-     python3 dorkeye.py -d "filetype:sql" --whitelist .sql -o database_dumps
# Gather leaked documents
-     python3 dorkeye.py -d "site:.com filetype:pdf confidential" -o leaked_docs
# Find exposed credentials
-     python3 dorkeye.py -d "filetype:env OR filetype:git" -o credentials
# Check for exposed backups
-     python3 dorkeye.py -d "site:company.com filetype:bak OR filetype:backup" -o backups
# Find configuration files
-     python3 dorkeye.py -d "site:company.com ext:conf OR ext:ini" -o configs
# Multiple targets from file
-     python3 dorkeye.py -d sqli_dorks.txt --stealth --sqli -c 200 -o dorks
![photo_6_2026-01-18_20-13-17](https://github.com/user-attachments/assets/9429b079-b865-4c48-9f76-b4aa2b232676)
![photo_3_2026-01-18_20-13-17](https://github.com/user-attachments/assets/fc83cc7f-4753-4050-978a-f3f50cced578)

## 🔒 Best Practices
- ✅ Always obtain written permission before testing
- ✅ Use only on authorized targets or public data
- ✅ Respect robots.txt and site policies
- ✅ Follow responsible disclosure for findings
- ❌ Never access or download unauthorized data
- ❌ Never use for malicious purposes

## 🚀 Operational Tips
- 🕒 Use appropriate delays to avoid rate limiting
- 🔄 Rotate search terms for better coverage
- 📊 Analyze HTML reports for visual insights
- 🎯 Combine with other OSINT tools (Maltego, theHarvester)
- 💾 Keep dork libraries organized and categorized
- 🔐 Integrate findings with vulnerability scanners (SQLMap, Nuclei, Nikto)

## 📁 Project Structure
DorkEye/
-  ├── dorkeye.py              # Main script
-  ├── requirements.txt        # Python dependencies
-  ├── setup.sh               # Linux/macOS setup script
-  ├── setup.bat              # Windows setup script
-  ├── run_dorkeye.sh         # Quick launcher (Linux/macOS)
-  ├── run_dorkeye.bat        # Quick launcher (Windows)
-  ├── INSTALL.md             # Detailed installation guide
-  ├── README.md              # This file
-  ├── dorkeye_config.yaml    # Sample configuration
-  ├── Dorks4SecTest.txt      # Example dorks (security test)
-  ├── dorks.txt              # Your dorks (optional)
-  ├── dorkeye_env/           # Virtual environment
-  └── Dump/           # Output directory (auto-created)
-   ├── *.csv              # CSV exports
-   ├── *.json             # JSON exports
-   └── *.html             # HTML reports
    
## 🧩 Future Roadmap
-  Multi-threaded searching for faster results
 - Active vulnerability scanner integration
 - Interactive TUI with textual
-  Browser extension for quick dorking
-  Cloud storage integration (AWS S3, Google Drive)
-  Custom search engine support (Bing, Shodan)
-  API endpoint for automation
-  Collaborative sharing platform
-  Machine learning for dork optimization

## ⚠️ Legal Disclaimer
- READ CAREFULLY BEFORE USE
- This tool is provided for educational, research, and authorized security testing purposes only.

- ⚖️ Unauthorized access to computer systems is illegal in most jurisdictions
- 🔒 Always obtain written permission before testing
- 📜 Users are solely responsible for compliance with local laws
- 🚫 The author disclaims all liability for misuse or damages
- ✅ Use responsibly and ethically at all times

## 📜 By using DorkEye, you agree to:
- Use only on authorized targets or public information
- Comply with all applicable laws and regulations
- Not use for malicious, illegal, or unethical purposes
- Take full responsibility for your actions

## 📞 Contact & Support
- Author: xPloits3c
- Email: whitehat.report@onionmail.org
- GitHub: @xPloits3c

## ✅ Support the Project
- ⭐ Star this repository
- 🐛 Report bugs via Issues
- 💡 Suggest features via Discussions
- 🤝 Fork the repository:

## 📜 MIT License
- Copyright (c) 2026 xPloits3c I.C.W.T

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

<div align="center">
🌟If you found DorkEye useful, please star the repository🌟
</div>
