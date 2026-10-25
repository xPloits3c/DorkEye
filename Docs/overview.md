# DorkEye — OSINT Dorking Tool

**DorkEye** is an automated **OSINT** and **Google Dorking** tool written in Python.
It generates and runs advanced search queries to discover exposed web assets, then
tests them for common vulnerabilities such as **SQL injection (SQLi)** and
**Cross-Site Scripting (XSS)**, and extracts metadata and sensitive information —
all with built-in stealth controls.

- **Repository:** https://github.com/xPloits3c/DorkEye
- **Website / Docs:** https://xploits3c.github.io/DorkEye/
- **License:** MIT
- **Language:** Python 3.9+ (3.8 compatible)
- **Search backend:** DuckDuckGo (lxml-free lite mode available for iSH / iOS)

---

## What is DorkEye?

DorkEye is an automated OSINT dorking tool that discovers exposed web assets through
intelligent search queries. It combines:

- a **dork generator** driven by YAML templates (`soft` / `medium` / `aggressive` modes),
- an **SQLi and XSS testing module**,
- a **13-step autonomous analysis pipeline** (the Agents pipeline),
- an **adaptive recursive crawler**, and
- a **database port scanner**.

It can identify indexed directories, sensitive files, admin panels, databases,
backups, configuration files, leaked credentials, PII data, subdomains, and
technology fingerprints — efficiently and with stealth controls.

Typical uses: reconnaissance for authorized penetration testing, bug-bounty recon,
attack-surface discovery, and OSINT investigations.

---

## Why use DorkEye?

- Bypasses CAPTCHA and rate-limiting during searches
- Produces an advanced, interactive HTML report
- Keeps your scanning anonymous and avoids IP blocking
- Returns clean, unfiltered search results
- Runs for hours without getting banned

---

## Key features

| Feature | What it does |
|---|---|
| **Wizard mode** | Interactive guided session exposing every option (`--wizard`) |
| **Dork generator** | Builds dork queries from YAML templates in `soft` / `medium` / `aggressive` modes |
| **SQL injection scanner** | 5 detection methods, 105 payloads |
| **XSS scanner** | 4 detection methods, 111 payloads |
| **Direct URL testing** | Test a single URL with `-u`, or re-process saved results with `-f` |
| **Web console** | Matrix-style local dashboard in the browser (`--ui`) |
| **DB port scan** | Probes 15 database services with no-auth checks, 3 severity levels (`--dbscan`) |
| **Agents pipeline** | 13-step autonomous analysis of discovered targets |
| **HeaderIntelAgent** | Finds info leaks, missing security headers, outdated servers |
| **TechFingerprintAgent** | Detects 35 technologies and generates CVE-oriented dorks |
| **EmailHarvesterAgent** | Collects and categorizes emails (admin / security / info) |
| **PiiDetectorAgent** | Detects phone numbers, IBAN, fiscal codes, credit cards, SSN, DOB |
| **SubdomainAgent** | Extracts subdomains and generates follow-up queries |
| **Adaptive crawl** | Recursive, multi-round dorking |
| **HTTP fingerprinting** | 22 browser/OS profiles (Chrome, Firefox, Safari, mobile, and more) |
| **Output formats** | Interactive HTML report plus CSV / JSON / TXT, saved to `Dump/` |
| **File categories** | 7 auto-detected categories with whitelist / blacklist filtering |
| **Full CLI** | 38 flags covering every combination |

---

## Supported platforms

DorkEye runs on Linux, macOS, Windows, Android (Termux), and iOS (iSH):

- **Linux / macOS** — standard install via `venv` + `requirements.txt`
- **Debian / Ubuntu / Kali** — Quick Install (see below)
- **Android (Termux)** — dedicated installer with `libxml2` / `libxslt`
- **iOS (iSH, Alpine Linux)** — lite installer with an `lxml`-free DuckDuckGo backend
- **Windows** — double-click `install.bat`

---

## Installation

### One-command install — Alpine / iOS (iSH)

```sh
apk add git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
sh install.sh
```

`install.sh` auto-detects the environment and runs the matching setup.

### Quick Install — Debian / Ubuntu / Kali

```sh
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
pip install -r requirements.txt

python3 dorkeye.py --wizard
```

---

## Usage examples

```sh
# Interactive wizard
python3 dorkeye.py --wizard

# Basic search
python3 dorkeye.py -d "inurl:admin" -o results.txt

# Dork generator + detection
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json

# SQLi with stealth
python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html

# Fast scan
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv

# Direct SQLi test on a single URL
python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json

# Re-process a saved result file
python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html

# Web console
python3 dorkeye.py --ui
```

See the [full CLI reference](https://github.com/xPloits3c/DorkEye/blob/master/Docs/cli.md)
for all 38 flags.

---

## Documentation

- [Full CLI reference](https://github.com/xPloits3c/DorkEye/blob/master/Docs/cli.md)
- [Wizard guide](https://github.com/xPloits3c/DorkEye/blob/master/Docs/wizard.md)
- [SQL injection reference](https://github.com/xPloits3c/DorkEye/blob/master/Docs/sqli.md)
- [XSS injection reference](https://github.com/xPloits3c/DorkEye/blob/master/Docs/xss.md)
- [Agents pipeline](https://github.com/xPloits3c/DorkEye/blob/master/Docs/agents.md)
- [Adaptive crawler](https://github.com/xPloits3c/DorkEye/blob/master/Docs/crawler.md)
- [DB port scan](https://github.com/xPloits3c/DorkEye/blob/master/Docs/dbscan.md)
- [HTTP fingerprinting](https://github.com/xPloits3c/DorkEye/blob/master/Docs/fingerprinting.md)
- [Web console](https://github.com/xPloits3c/DorkEye/blob/master/Docs/webconsole.md)
- [Termux / Android setup](https://github.com/xPloits3c/DorkEye/blob/master/Docs/termux.md)
- [iSH / iOS setup](https://github.com/xPloits3c/DorkEye/blob/master/Docs/ish.md)
- [HTML report guide](https://github.com/xPloits3c/DorkEye/blob/master/Docs/REPORT_HTML.md)

---

## Legal disclaimer

DorkEye is provided for **educational and authorized security-testing purposes only.**
You are solely responsible for complying with all applicable laws and for obtaining
explicit, written authorization before scanning, testing, or probing any system,
domain, or network you do not own. The authors and contributors accept no liability
for misuse.

---

<!--
  SEO / SOCIAL KEYWORDS — not for Google ranking, but handy when you share DorkEye
  on Telegram, X/Twitter, Reddit, forums. Pick a few relevant ones per post;
  do NOT dump them all. Hashtags only make sense on social platforms, not here.

  Keywords: OSINT tool, Google dorking, Google dorks, dork generator, SQL injection
  scanner, XSS scanner, vulnerability scanner, recon tool, bug bounty recon,
  attack surface discovery, DuckDuckGo search, subdomain enumeration, metadata
  extraction, PII detection, database port scan, penetration testing, Python
  security tool, Termux, iSH, Kali Linux.

  Social hashtags: #OSINT #GoogleDorking #CyberSecurity #InfoSec #BugBounty
  #PenTest #SQLi #XSS #Python #Hacking #Recon #Termux #KaliLinux
-->
