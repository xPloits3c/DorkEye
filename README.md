![537309991-f4f59199-d30f-4628-bb92-e6ccf43a6814](https://github.com/user-attachments/assets/ac547327-8c58-4792-bb0c-7f93798032d0)

<div align="center">
# DorkEye | Advanced OSINT Dorking Tool 🔍
</div>
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


## 🧠 What is DorkEye?
- DorkEye is an advanced automated dorking tool that leverages DuckDuckGo to discover exposed web resources through OSINT (Open Source Intelligence) techniques.
- It can identify indexed directories, sensitive files, admin panels, databases, backups, and other publicly accessible resources—all in an anonymous, efficient, and legal manner.

Why DuckDuckGo?
- Using DuckDuckGo (via the ddgs library) allows DorkEye to:

-  ✅ Bypass CAPTCHA and rate-limiting typical of mainstream search engines
-  ✅ Maintain anonymity and privacy during searches
-  ✅ Avoid IP blocks and detection mechanisms
-  ✅ Access a clean, unfiltered index of web resources
-  ✅ Dorking, analyze, extract metadata, test sqli vulnerability.

## What's New in v3.1? 🎉
-  🎯 File Analysis & Categorization - Automatically categorizes results by file type (documents, archives, databases, configs, etc.)
-  🧠 SQL Param Vuln - --Automatically Testing for SQL vulnerabilty after Potenzial SQLi Found 
-  🚫 Blacklist/Whitelist System - Filter results by file extensions
-  📊 Enhanced Output Formats - Export results as CSV, JSON, and HTML reports
-  🔍 Advanced File Metadata Analysis - Checks file accessibility, size, and content-type
-  🗂️ Global Deduplication - Removes duplicate URLs across all dorks
-  📈 Detailed Statistics - Comprehensive analytics and category breakdowns
-  ⚙️ Configuration Files - YAML/JSON config support for advanced customization
-  🎨 Rich Terminal UI - Beautiful progress bars and formatted output
-  💾 Multiple Export Formats - CSV, JSON, and interactive HTML reports
-  ✨ Key Features

## Feature	Description
-  🔎 Smart Dorking	Execute single or multiple dorks from files
-  🚫 Extension Filtering	Blacklist/whitelist specific file types
-  📁 Auto-Categorization	7 file categories (documents, archives, databases, backups, configs, scripts, credentials)
-  🔍 File Analysis	Check file size, content-type, and accessibility
-  📊 Triple Export	CSV, JSON, and HTML report generation
-  🎯 Global Deduplication	Intelligent URL hash-based duplicate removal
-  ⚡ Rate Limit Protection	Smart delays to avoid blocking
-  📈 Detailed Statistics	Real-time metrics and category breakdowns
-  ⚙️ Config Support	YAML/JSON configuration files
-  🎨 Beautiful UI	Rich terminal interface with progress tracking
-  📦 Installation

# Quick Install
-  For full installation instructions on all platforms, follow the complete guide:
📦 INSTALL.md

![photo_1_2026-01-18_20-13-17](https://github.com/user-attachments/assets/9d0a2393-cd7b-49fc-a078-5e8bb85b7a7e)
![photo_2_2026-01-18_20-13-17](https://github.com/user-attachments/assets/737f1bc0-a81c-45a0-a3d2-6a74f6c8c666)

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

# Exit Virtual environment:
-     cd DorkEye
-     deactivate
# Remove Virtual environment:
-     cd DorkEye
-     rm -rf venv

# 🚀 Basic Usage

![photo_4_2026-01-18_20-13-17](https://github.com/user-attachments/assets/3f534668-ffb3-4bb5-8005-33e49882ff21)

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
- Command-Line Options
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

<img width="1273" height="401" alt="dehelp" src="https://github.com/user-attachments/assets/9a241a6c-8e61-4188-87b7-3238ce79c8d2" />


📂 Output Formats
-  DorkEye v3.0 generates three comprehensive output files:

1. CSV File (results.csv)
-  Structured data with columns:
-  URL, Title, Snippet, Dork, Timestamp
-  Extension, Category, File Size, Content Type
-  Accessibility Status, HTTP Status Code

2. JSON File (results.json)
- Complete data export including:
- All results with full metadata
-  Search statistics
-  Execution details
-  Category breakdowns
  
![photo_5_2026-01-18_20-13-17](https://github.com/user-attachments/assets/baff38ab-76ec-4080-a002-311e02029ccc)


3. HTML Report (results.html)
-  Interactive web-based report featuring:
-  Visual statistics dashboard
-  Sortable results table
-  Color-coded categories
-  Accessibility indicators
-  Professional presentation

![photo_6_2026-01-18_20-13-17](https://github.com/user-attachments/assets/9429b079-b865-4c48-9f76-b4aa2b232676)
![photo_3_2026-01-18_20-13-17](https://github.com/user-attachments/assets/fc83cc7f-4753-4050-978a-f3f50cced578)

-  Example Output Structure:
-  results/
-  ├── results.csv      # Spreadsheet-friendly data
-  ├── results.json     # Machine-readable format
-  └── results.html     # Visual report

🗂️ File Categories
-  DorkEye automatically categorizes findings into 8 types:

Category	Extensions	Use Case
-  📄 Documents	.pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx	Office documents, reports
-  📦 Archives	.zip, .rar, .tar, .gz, .7z, .bz2	Compressed files, backups
-  🗄️ Databases	.sql, .db, .sqlite, .mdb	Database dumps, exports
-  💾 Backups	.bak, .backup, .old, .tmp	Backup files, temp data
-  ⚙️ Configs	.conf, .ini, .yaml, .json, .xml	Configuration files
-  📜 Scripts	.php, .asp, .jsp, .sh, .bat, .ps1	Server-side scripts
-  🔑 Credentials	.env, .git, .svn, .htpasswd	Sensitive auth files
-  ⚙️ Configuration File

# Create a dorks.txt file with one dork per line:

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
- 
# Find exposed credentials
-     python3 dorkeye.py -d "filetype:env OR filetype:git" -o credentials

# Check for exposed backups
-     python3 dorkeye.py -d "site:company.com filetype:bak OR filetype:backup" -o backups
  
# Find configuration files
-     python3 dorkeye.py -d "site:company.com ext:conf OR ext:ini" -o configs

# Multiple targets from file
-     python3 dorkeye.py -d sqli_dorks.txt --stealth --sqli -c 200 -o dorks
- 
🔒 Best Practices
Ethical Guidelines
- ✅ Always obtain written permission before testing
- ✅ Use only on authorized targets or public data
- ✅ Respect robots.txt and site policies
- ✅ Follow responsible disclosure for findings
- ❌ Never access or download unauthorized data
- ❌ Never use for malicious purposes
Operational Tips
- 🕒 Use appropriate delays to avoid rate limiting
- 🔄 Rotate search terms for better coverage
- 📊 Analyze HTML reports for visual insights
- 🎯 Combine with other OSINT tools (Maltego, theHarvester)
- 💾 Keep dork libraries organized and categorized
- 🔐 Integrate findings with vulnerability scanners (SQLMap, Nuclei, Nikto)

- 📁 Project Structure
DorkEye/
-  ├── dorkeye.py              # Main script
-  ├── requirements.txt        # Python dependencies
-  ├── setup.sh               # Linux/macOS setup script
-  ├── setup.bat              # Windows setup script
-  ├── run_dorkeye.sh         # Quick launcher (Linux/macOS)
-  ├── run_dorkeye.bat        # Quick launcher (Windows)
-  ├── INSTALL.md             # Detailed installation guide
-  ├── README.md              # This file
-  ├── INSTALL.md             # Detailed installation guide
-  ├── dorkeye_config.yaml    # Sample configuration
-  ├── dorks.txt              # Example dorks (optional)
-  ├── dorkeye_env/           # Virtual environment
-  └── Dump/           # Output directory (auto-created)
-   ├── *.csv              # CSV exports
-   ├── *.json             # JSON exports
-   └── *.html             # HTML reports
    
- 🔄 Changelog v3.0.0 (Current)
- ✨ Complete rewrite with enhanced functionality
- 🎯 Added file analysis and categorization
- 🚫 Implemented blacklist/whitelist system
- 📊 Multiple export formats (CSV, JSON, HTML)
- 🔍 Advanced metadata extraction
- 📈 Comprehensive statistics dashboard
- ⚙️ Configuration file support
- 🎨 Rich terminal UI improvements
- v2.4 (Legacy)
- Basic dorking functionality
- Single CSV output
- DuckDuckGo integration
- 🧩 Future Roadmap
-  Multi-threaded searching for faster results
 - Active vulnerability scanner integration
 - Interactive TUI with textual
-  Browser extension for quick dorking
-  Cloud storage integration (AWS S3, Google Drive)
-  Custom search engine support (Bing, Shodan)
-  API endpoint for automation
-  Collaborative sharing platform
-  Machine learning for dork optimization
- 🤝 Contributions are welcome!
Fork the repository:
- Create a feature branch (git checkout -b feature/AmazingFeature)
- Commit your changes (git commit -m 'Add AmazingFeature')
- Push to the branch (git push origin feature/AmazingFeature)
- Open a Pull Request
- Contribution Ideas:
-  New file categories
-  Additional search engines
-  UI/UX improvements
-  Documentation translations
-  Bug fixes and optimizations

## ⚠️ Legal Disclaimer
- READ CAREFULLY BEFORE USE
- This tool is provided for educational, research, and authorized security testing purposes only.

- ⚖️ Unauthorized access to computer systems is illegal in most jurisdictions
- 🔒 Always obtain written permission before testing
- 📜 Users are solely responsible for compliance with local laws
- 🚫 The author disclaims all liability for misuse or damages
- ✅ Use responsibly and ethically at all times
- By using DorkEye, you agree to:
- Use only on authorized targets or public information
- Comply with all applicable laws and regulations
- Not use for malicious, illegal, or unethical purposes
- Take full responsibility for your actions

## 📞 Contact & Support
- Author: xPloits3c
- Email: whitehat.report@onionmail.org
- GitHub: @xPloits3c

## Support the Project
- ⭐ Star this repository
- 🐛 Report bugs via Issues
- 💡 Suggest features via Discussions
- 🤝 Contribute via Pull Requests
- 🔗 Related Projects
<p> <a href="https://github.com/xPloits3c/MetaByte" target="_blank"> <img src="https://img.shields.io/badge/MetaByte-Metadata_Extractor-blue?style=for-the-badge" alt="MetaByte"> </a> </p>
- Check out MetaByte - Advanced metadata extraction tool

📜 MIT License
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
🌟 If you found DorkEye useful, please star the repository! 🌟
</div>
