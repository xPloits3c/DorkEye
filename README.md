<div align="center">
<img width="1280" height="640" alt="image" src="https://github.com/user-attachments/assets/648a142b-34ed-4762-b309-a51e9f9cd53d" />

</div>

---

<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>

<!-- ── Row 1: Project identity ── -->
![Python](https://img.shields.io/badge/Python-3.9%2B-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)
![Search](https://img.shields.io/badge/Search-DuckDuckGo-FF6600?style=flat-square&logo=duckduckgo&logoColor=white)
![Version](https://img.shields.io/badge/Version-5.0-brightgreen?style=flat-square)

<!-- ── Row 2: Live stats ── -->
![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat-square)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye?style=flat-square)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye?style=flat-square&logo=github)

<!-- ── Row 3: Community ── -->

[![Telegram](https://img.shields.io/badge/Join-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/DorkEye) 

<img width="980" height="640" alt="image" src="https://github.com/user-attachments/assets/13dea163-578c-41ad-9e2b-497bb373ab77" />

---

## What is DorkEye?
**DorkEye** is an automated `OSINT DORKING TOOL` that discovers exposed web assets through intelligent search queries.
- It combines a dork generator driven by YAML templates (`soft` / `medium` / `aggressive` modes), an SQL and XSS testing module, a 13-step autonomous analysis pipeline, an adaptive recursive crawler, and a database port scanner.

- It can identify indexed directories, sensitive files, admin panels, databases, backups, configuration files, credentials, PII data, subdomains, and technology fingerprints — efficiently and with stealth controls.

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Why DorkEye

- Bypass CAPTCHA and rate-limiting
- Advanced, interactive HTML report
- Maintain anonymity and avoid IP blocking
- Clean and unfiltered search results
- Keep dorking for hours — DorkEye won't get banned.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## What's New 🥇

| Feature | Details |
|---------|---------|
| 🧙 Wizard | [Interactive guided session — all options](Docs/wizard.md) |
| ⚙️ Dork Generator | [YAML template modes: `soft` / `medium` / `aggressive`](Docs/dork_generator.md) |
| 🎯 Direct SQLi-XSS Test | [Test URL’s directly with `-u` and `-f`](Docs/sqli.md) |
| 📂 File Re-Processing | [Re-run SQLi/XSS/analysis/crawl on saved result files with `-f`](Docs/cli.md) |
| 💉 SQL Injection | [5 methods: 105 payloads](Docs/sqli.md) |
| 💉 XSS Injection | [4 methods: 111 payloads](Docs/xss.md) |
| 🖥️ Web Console | [Matrix-Style local dashboard via browser `--ui`](Docs/webconsole.md) |
| 🚪 DB Port Scan | [15 services, no-auth probes, 3 severity levels `--dbscan`](Docs/dbscan.md) |
| 🤖 Agents Pipeline | [13-step autonomous analysis](Docs/agents.md) |
| 🛡️ HeaderIntelAgent | [Info leaks, missing security headers, outdated server](Docs/agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 technologies detected, CVE dorks generated](Docs/agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Collects and categorizes emails: admin / security / info..](Docs/agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Phone, IBAN, fiscal code, credit card, SSN, DOB](Docs/agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Extracts subdomains and generates `queries`](Docs/agents.md#subdomainharvesteragent) |
| 🔄 Adaptive Crawl | [Recursive multi-round dorking](Docs/crawler.md) |
| 🔑 HTTP Fingerprinting | [22 browser/OS profiles — Chrome, Firefox, Safari, mobile, etc.](Docs/fingerprinting.md) |
| 📊 Output Formats | [HTML interactive report — all saved to `Dump/`](Docs/output_formats.md) |
| 🗂️ File Categories | [7 auto-detected categories - whitelist / blacklist filtering](Docs/file_categories.md) |
| 🖥️ Full CLI Reference | [All 38 flags and every possible combination](Docs/cli.md) |

---

## Quick Install
```bash
"Update:"
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git

"Git Clone:"
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye

"Create environment:"
  python3 -m venv dorkeye_env

"Activate environment:"
  source dorkeye_env/bin/activate

"Install requirements:"
  pip install -r requirements.txt

"WIZARD MODE:"
  python3 dorkeye.py --wizard
```

<img width="1175" height="982" alt="dev5 0wiz" src="https://github.com/user-attachments/assets/79253966-b2ed-431e-9d46-aaa8d8297c82" />

---

```bash
"Help:"
  python3 dorkeye.py -h

"Deactivate environment:"
  deactivate

"Remove environment:"
  rm -rf dorkeye_env
```
---

## Usage 

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # WIZARD Mode
```bash
  python3 dorkeye.py --wizard
```
🔹 # Basic search
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Dork Generator + Detection
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + stealth
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Fast scan
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Direct SQLi test on a URL
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Re-process a saved result file
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```

🔹 # Web Console
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## Examples
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
│    ├── db_portscan.py   ← Scans exposed database ports
│    ├── dorkeye_web.py   ← Local web interface
│    ├── sqli.py     ← 5 Method sqli injection (105 payloads)
│    └── xss.py     ← 4 Method xss injection (111 payloads)
│ /Templates/
│    ├── dorks_templates.yaml
│    ├── sql.yaml
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
│ /Screenshots/
│    ├── img0
│    └── img1
```
---

## Example DorkEye Report

![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

## ![WARNING](https://img.shields.io/badge/Legal%20Disclaimer-red)

**DorkEye is provided for educational and authorized security-testing purposes only.**
<img width="1408" height="768" alt="image" src="https://github.com/user-attachments/assets/e3eb4dca-51e9-4d4c-a2e4-afa057564b74" />

- You are solely responsible for complying with all applicable laws and for obtaining explicit, written authorization before scanning, testing, or probing any system, domain, or network you do not own.
- The authors and contributors accept no liability for misuse or for any damage resulting from the use of this tool.

---

## 📞 Contact

- **Author:** I.C.W.T / xPloits3c  
- **Email:** dorkeye@protonmail.com  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Support
 - **Feel free to contribute. please do.**
 - **If you find DorkEye useful, please consider starring the repository 🌟**
 - **Buy me a coffee and keep the development caffeinated ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 License
MIT License © 2026 I.C.W.T xPloits3c


## Contributor
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
