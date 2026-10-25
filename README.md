<div align="center">
<img width="1280" height="640" alt="image" src="https://github.com/user-attachments/assets/648a142b-34ed-4762-b309-a51e9f9cd53d" />

</div>

---

# DorkEye – OSINT Google Dorking Tool

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
| 🎯 SQLi-XSS | [Test URL’s directly with `-u` and `-f`](Docs/sqli.md) |
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

## One-command install — Alpine / iOS (iSH)
Recommended for **iOS users via [iSH](https://ish.app)** (Alpine Linux) and any Alpine-based system.<br>
`install.sh` auto-detects the environment and runs the matching setup.
[![Docs](https://img.shields.io/badge/📖_Docs-blue)](Docs/ish.md)

```sh
apk add git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
sh install.sh
source dorkeye_env/bin/activate
python dorkeye.py —wizard
```
> Using Debian, Ubuntu or Kali? Follow the **Quick Install** below.

## Update
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
## AUTOMATIC Quick Install
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py —wizard
```
## MANUAL Quick Install
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
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

🔹 # WIZARD Mode &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # Basic search &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Dork Generator + Detection &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + stealth &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Fast scan &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Direct SQLi test on a URL &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Re-process a saved result file &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # Web Console &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](Docs/webconsole.md)
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
│ ├── dorkeye.py                      ← DorkEye Engine
│ ├── requirements.txt                ← Python dependencies
│ ├── http_fingerprints.json          ← 22 browser/OS HTTP profiles
│ ├── install.sh                      ← Device detect + dispatch (Linux/macOS/Termux/iSH)
│ ├── install.bat                     ← Windows installer (double-click)
│ ├── README.md                       ← This file (you are here)
│ ├── LICENSE                         ← MIT license
│ ├── .gitignore                      ← Git ignore rules
│ /Devices/                           ← Per-device installers
│    /iOS/
│        ├── install_ish.sh           ← iSH (iOS) lite installer — no lxml
│        └── ddg_lite.py              ← lxml-free DuckDuckGo backend
│    /Android/
│        └── install_termux.sh        ← Termux installer (libxml2/libxslt + venv)
│    /Linux/
│        └── install_linux.sh         ← Linux / macOS installer (venv)
│ /Tools/
│    ├── __init__.py                  ← Package initializer
│    ├── dork_generator.py            ← Dork Generator Queries
│    ├── dorkeye_agents.py            ← Agents pipeline
│    ├── dorkeye_patterns.py          ← Shared pattern library
│    ├── dorkeye_analyze.py           ← Standalone analysis CLI
│    ├── db_portscan.py               ← Scans exposed database ports
│    ├── dorkeye_web.py               ← Local web interface
│    ├── sqli.py                      ← 5 Method sqli injection (105 payloads)
│    └── xss.py                       ← 4 Method xss injection (111 payloads)
│ /Templates/
│    ├── dorks_templates.yaml         ← Default template 
│    ├── example.yaml                 ← Example template
│    └── sql.yaml                     ← SQLi dork template
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← Community guidelines
│    ├── CONTRIBUTING.md              ← Contribution guide
│    ├── SECURITY.md                  ← Security policy
│    ├── FUNDING.yml                  ← Sponsor configuration
│    ├── pull_request_template.md     ← PR template
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Bug report template
│        └── feature_request.md       ← Feature request template
│     /workflows/
│        └── claude-dorkeye.yml       ← GitHub Actions AI agent
│ /Docs/
│    ├── cli.md                       ← Full CLI reference (38 flags)
│    ├── wizard.md                    ← Interactive wizard guide
│    ├── sqli.md                      ← SQL injection reference
│    ├── xss.md                       ← XSS injection reference
│    ├── agents.md                    ← Agents pipeline guide
│    ├── crawler.md                   ← Adaptive crawler guide
│    ├── dbscan.md                    ← DB port scan guide
│    ├── fingerprinting.md            ← HTTP fingerprinting guide
│    ├── http_fingerprints.md         ← Fingerprint profiles reference
│    ├── webconsole.md                ← Web Console guide
│    ├── termux.md                    ← Termux / Android setup
│    ├── ish.md                       ← iSH / iOS setup (lite mode)
│    ├── windows.md                   ← Windows setup (install.bat)
│    ├── output_formats.md            ← Output formats guide
│    ├── file_categories.md           ← File categories guide
│    ├── dork_generator.md            ← Dork generator guide
│    ├── INSTALL.md                   ← Installation guide
│    ├── REPORT_HTML.md               ← HTML report guide
│    ├── USAGE.md                     ← Usage examples
│    ├── DDGSEE.md                    ← DuckDuckGo engine notes
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← Curated dork collection
│        ├── JSON_exposure_dork.txt   ← JSON exposure dorks
│        └── sql_dorks.txt            ← SQLi-oriented dorks
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← runtime output, not versioned (see .gitignore)
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    └── *.html
```
---

## Example DorkEye Report

![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

## ![WARNING](https://img.shields.io/badge/Legal%20Disclaimer-red)

**DorkEye is provided for educational and authorized security-testing purposes only.**

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
[MIT License](LICENSE) © 2026 I.C.W.T xPloits3c



## Contributors
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
