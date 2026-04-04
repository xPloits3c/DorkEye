<div align="center">
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/cceb7da1-c8cc-4a42-836e-30acc9443ff6" />

</div>

---

```json
" 🦅 DorkEye | OSINT Dorking Tool "
> I don't hack systems, i expose their secrets <
```

<!-- ── Row 1: Project identity ── -->
![Python](https://img.shields.io/badge/Python-3.9%2B-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)
![Search](https://img.shields.io/badge/Search-DuckDuckGo-FF6600?style=flat-square&logo=duckduckgo&logoColor=white)
![Version](https://img.shields.io/badge/Version-4.8-brightgreen?style=flat-square)

<!-- ── Row 2: Live stats ── -->
![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat-square&logo=github&label=Stars&color=yellow)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye?style=flat-square&logo=github&label=Forks&color=lightgrey)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye?style=flat-square&logo=github&label=Issues&color=brightgreen)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye?style=flat-square&logo=github&label=Last+Commit&color=informational)

<!-- ── Row 3: Community ── -->
[![Telegram](https://img.shields.io/badge/Join-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white)](#)

---

## What is DorkEye
**DorkEye** is an advanced automated dorking and OSINT recon tool that leverages DuckDuckGo to discover exposed web resources through intelligent search queries.
- It combines a powerful dork generator, a full SQL injection detection engine, a 11-step autonomous analysis pipeline, and an adaptive recursive crawler — all without requiring any external AI or cloud services.

- It can identify indexed directories, sensitive files, admin panels, databases, backups, configuration files, credentials, PII data, subdomains, and technology fingerprints — efficiently and with stealth controls.

<img width="1212" height="880" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/6ee12cbe-fd40-40dd-8684-0dba594b1a67" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Why DorkEye

- Bypass CAPTCHA and rate‑limiting
- Advanced .html report interactive
- Maintain anonymity and avoid IP blocking
- Clean and unfiltered search results
- Advanced analysis and automated SQLi testing
- Continue Dorking for hours, DorkEye won’t get banned.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## What’s New 🥇

| Feature | Details |
|---------|---------|
| 🧙 Wizard | [Interactive guided session — all options](Docs/wizard.md) |
| ⚙️ Dork Generator | [YAML template modes: `soft` / `medium` / `aggressive`](Docs/dork_generator.md) |
| 🎯 Direct SQLi Test | [Test a single URL directly with `-u`](Docs/sqli.md) |
| 📂 File Re-Processing | [Re-run SQLi / analysis / crawl on saved result files with `-f`](Docs/cli.md) |
| 💉 SQL Injection | [4 methods: error-based, UNION, boolean blind, time-based](Docs/sqli.md) |
| 💉 XSS Injection | [4 methods: reflected, stored, DOM-based, header-based](Docs/xss.md) |
| 🤖 Agents v3.1 Pipeline | [11-step autonomous analysis](Docs/agents.md) |
| 🛡️ HeaderIntelAgent | [Info leaks, missing security headers, outdated server](Docs/agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 technologies detected, CVE dorks generated](Docs/agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Collects and categorizes emails: admin / security / info..](Docs/agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Phone, IBAN, fiscal code, credit card, SSN, DOB](Docs/agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Extracts subdomains and generates `queries`](Docs/agents.md#subdomainharvesteragent) |
| 🔄 Adaptive Crawl | [Recursive multi-round dorking](Docs/crawler.md) |
| 🔑 HTTP Fingerprinting | [22 browser/OS profiles — Chrome,Firefox,Safari,mobile..](Docs/fingerprinting.md) |
| 📊 Output Formats | [HTML interactive report — all saved to `Dump/`](Docs/output_formats.md) |
| 🗂️ File Categories | [7 auto-detected categories - whitelist / blacklist filtering](Docs/file_categories.md) |
| 🖥️ Full CLI Reference | [All 31 flags and every possible combination](Docs/cli.md) |

---

## Quick Install
```json
"Update:"
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git

"Git Clone:"
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye

"Create environment:"
  python -m venv dorkeye_env

"Activate environment:"
  source dorkeye_env/bin/activate

"Install requirements:"
  pip install -r requirements.txt

"WIZARD MODE:"
  python dorkeye.py --wizard
```

<img width="1175" height="982" alt="dev5 0wiz" src="https://github.com/user-attachments/assets/79253966-b2ed-431e-9d46-aaa8d8297c82" />

---

```json
"Help:"
  python dorkeye.py -h

"Deactivate environment:"
  deactivate

"Remove environment:"
  rm -rf dorkeye_env
```
---

## Usage 

<img width="1141" height="948" alt="de-h" src="https://github.com/user-attachments/assets/99fe8d3a-822a-4bfe-97b1-62897db6db1d" />

🔹 # WIZARD Mode
```json
  python dorkeye.py --wizard
```
🔹 # Basic search
```json
  python dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Dork Generator + Detection
```json
  python dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + stealth
```json
  python dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Fast scan
```json
  python dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Direct SQLi test on a URL
  ```json
python dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Re-process a saved result file
```json
  python dorkeye.py -f Dump/results.json --sqli --analyze -o retest.html
```

<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 Project Structure
```
DorkEye/
│ ├── dorkeye.py               ← DorkEye Engine
│ ├── requirements.txt
│ ├── http_fingerprints.json
│ ├── README.md
│ /Tools/
│    ├── dork_generator.py     ← Dork Generator Queries
│    ├── dorkeye_agents.py     ← Agents v3.1 pipeline
│    ├── dorkeye_patterns.py   ← Shared pattern library
│    ├── dorkeye_analyze.py    ← Standalone analysis CLI
│    ├── sqli.py     ← 4 method sqli injection(14 payloads)
│    └── xss.py     ← 4 method xss injection (51 payloads)
│ /Templates/
│    ├── dorks_templates.yaml
│    ├── sqli.yaml
│    ├── osint.yaml
│    ├── intel_dorks.yaml
│    ├── epstein_files.yaml
│    └── example.yaml
│ /.github/
│    ├── CODE_OF_CONDUCT.md
│    ├── CONTRIBUTING.md
│    ├── SECURITY.md
│    ├── pull_request_template.md
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md
│        └── feature_request.md
│     /workflows
│        └── claude-dorkeye.yml
│ /Dump/
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    └── *.html
│ /Docs/
│    ├── cli.md
│    ├── wizard.md
│    ├── sqli.md
│    ├── agents.md
│    ├── crawler.md
│    ├── fingerprinting.md
│    ├── output_formats.md
│    ├── file_categories.md
│    ├── dork_generator.md
│    ├── INSTALL.md
│    ├── REPORT_HTML.md
│    ├── USAGE.md
│    └── DDGSEE.md
```
---

## Example HTML Report
<img width="1682" height="847" alt="report" src="https://github.com/user-attachments/assets/b35069a4-b457-4cd4-8158-84caddf9b658" />


## Example final Report
![image](https://github.com/user-attachments/assets/20055807-2f9d-4979-b221-e0cfad32828a)

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
