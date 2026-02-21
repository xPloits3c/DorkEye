<div align="center">

```
     ___
 __H__       xploits3c.github.io/DorkEye
  [,]
  [)]
  [;]    DorkEye  |  OSINT & Security Dorking Framework
  |_|                          v4.2.6
   V
```

# DorkEye

**Advanced OSINT & Security Dorking Framework**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Version](https://img.shields.io/badge/Version-4.2.6-green?style=flat-square)](https://github.com/xPloits3c/DorkEye)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square)](https://github.com/xPloits3c/DorkEye)
[![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat-square)](https://github.com/xPloits3c/DorkEye/stargazers)
[![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye?style=flat-square)](https://github.com/xPloits3c/DorkEye/network/members)

*Automates Google Dork queries through DuckDuckGo to discover exposed resources, sensitive files, admin panels, SQL injection points and web misconfigurations — stealthily, at scale, with professional reporting.*

[**Quick Start**](#-quick-start) · [**Features**](#-features) · [**Usage**](#-usage) · [**Dork Generator**](#-dork-generator) · [**Output**](#-output-formats) · [**Docs**](Docs/)

</div>

---

## 🔍 What is DorkEye?

**DorkEye** is a Python-based OSINT and security reconnaissance framework that turns [Google Dork](https://www.exploit-db.com/google-hacking-database) queries into an automated, scalable, stealthy pipeline. Instead of manually typing search queries one by one, DorkEye:

- **Generates** hundreds of targeted dork queries automatically from YAML templates
- **Searches** through DuckDuckGo (no CAPTCHA, no API key required)
- **Analyzes** results for SQL injection vulnerabilities, file metadata and server fingerprints
- **Reports** findings in a professional interactive HTML report, JSON, CSV or plain text

Built for ethical security researchers, penetration testers and bug bounty hunters operating on authorized targets.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **Dork Generator** | Auto-generates dork queries from YAML templates by category and intensity mode |
| 🔎 **DuckDuckGo Engine** | No CAPTCHA, no API key — unlimited bulk searches via `DDGS()` |
| 💉 **SQLi Detection** | Real injection testing: error-based, differential analysis, POST/JSON/path-based |
| 🕵️ **Stealth Mode** | Extended delays, rate-limit protection, per-request fingerprint rotation |
| 🖥️ **HTTP Fingerprinting** | Realistic browser profiles (Chrome/Firefox/Safari/Edge) with accurate headers |
| 🔄 **User-Agent Rotation** | Pools of real UA strings rotated per request |
| 🗂️ **Category Filtering** | Results auto-tagged: documents, scripts, databases, credentials, webpages |
| 📊 **Interactive HTML Report** | Matrix-themed UI with sub-filter dropdowns, badge counters and download links |
| 💾 **Multiple Output Formats** | `.html` · `.json` · `.csv` · `.txt` |
| ⚙️ **YAML Configuration** | Customize extensions, timeouts, retries, stealth settings and more |
| 🚫 **Deduplication** | MD5-based URL deduplication across all dorks |
| ⬛ **Blacklist / Whitelist** | Filter results by file extension before analysis |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git
- Linux / macOS / Windows (WSL recommended on Windows)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

# 2. Create and activate virtual environment
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate        # Linux / macOS
# dorkeye_env\Scripts\activate         # Windows

# 3. Run setup (installs all dependencies)
chmod +x setup.sh
./setup.sh

# 4. Verify installation
python3 dorkeye.py -h
```

For detailed installation instructions (Windows, Kali, Docker) see [INSTALL.md](INSTALL.md).

---

## 📖 Usage

### Basic Syntax

```bash
python3 dorkeye.py [OPTIONS] -o OUTPUT
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `-d`, `--dork` | — | Single dork string or path to a `.txt` file of dorks |
| `-o`, `--output` | — | Output filename (`results.html`, `results.json`, etc.) |
| `-c`, `--count` | `50` | Max results per dork query |
| `--dg` | — | Enable Dork Generator (`--dg=sqli`, `--dg=all`, etc.) |
| `--mode` | `soft` | Generator intensity: `soft` · `medium` · `aggressive` |
| `--templates` | `dorks_templates.yaml` | Template file or `all` to load every template |
| `--sqli` | off | Enable live SQL injection testing |
| `--stealth` | off | Enable stealth mode (rate limiting, extended delays) |
| `--no-fingerprint` | off | Disable HTTP fingerprinting for faster scans |
| `--no-analyze` | off | Disable file metadata analysis (HEAD requests) |
| `--config` | — | Path to custom YAML/JSON config file |
| `--blacklist` | — | Skip URLs with these extensions: `--blacklist .pdf .doc` |
| `--whitelist` | — | Only keep URLs with these extensions: `--whitelist .php .asp` |
| `--create-config` | — | Generate a sample `dorkeye_config.yaml` |

---

## 💡 Examples

### Single Dork Search

```bash
# Simple search, HTML output
python3 dorkeye.py -d "inurl:admin" -o results.html

# From a dork list file
python3 dorkeye.py -d dorks.txt -c 100 -o results.html

# Targeted domain + file type
python3 dorkeye.py -d "site:example.com filetype:pdf" -o docs.html

# Real-world OSINT example
python3 dorkeye.py -d "site:.ru inurl:russian_cv filetype:pdf" -o russian_cvs.html -c 100
```

### SQL Injection Discovery

```bash
# Dork search + live SQLi testing
python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o sqli_report.html

# Full pipeline: generate dorks + test + stealth + aggressive
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o sqli_full.html

# PHP-only focus with whitelist
python3 dorkeye.py --dg=sqli --mode=medium --sqli --whitelist .php -o php_sqli.html
```

### Using the Dork Generator

```bash
# All categories, default mode
python3 dorkeye.py --dg=all -o recon.html

# Specific category, medium intensity
python3 dorkeye.py --dg=admin --mode=medium -o admin_panels.html

# Aggressive with all templates loaded
python3 dorkeye.py --dg=all --templates=all --mode=aggressive --stealth -o deep.html
```

### Fast & Lightweight Scans

```bash
# Disable analysis for maximum speed
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.html

# No fingerprinting, no analysis — raw URL collection
python3 dorkeye.py --dg=all --no-fingerprint --no-analyze -o urls.txt

# CSV output for spreadsheet analysis
python3 dorkeye.py --dg=all --mode=medium -o findings.csv
```

---

## 🤖 Dork Generator

The `--dg` flag activates DorkEye's **automated query generation engine**. It reads YAML templates and produces batches of targeted dork queries — eliminating the need to write queries manually.

### How it works

```
YAML Templates → Query Expansion → DuckDuckGo Search → Analysis → Report
```

### Available Categories *(default template)*

| Category | Targets |
|---|---|
| `sqli` | SQL-injectable URLs with GET parameters |
| `admin` | Admin panels and login interfaces |
| `backups` | Exposed backup files (`.bak`, `.old`, `.zip`) |
| `databases` | Database files indexed publicly (`.sql`, `.db`) |
| `configs` | Configuration files (`.env`, `.conf`, `.yaml`) |
| `credentials` | Credential files (`.htpasswd`, `.git`, `.env`) |
| `documents` | Sensitive documents (PDF, DOCX, XLSX) |
| `logs` | Server and application log files |
| `open_dirs` | Open directory listings |
| `errors` | Verbose error pages with stack traces |

### Generation Modes

| Mode | Volume | Recommended For |
|---|---|---|
| `soft` | Low | Quick recon, rate-sensitive environments |
| `medium` | Moderate | Standard assessments |
| `aggressive` | High | Thorough coverage — always pair with `--stealth` |

> 📄 See [Docs/DORK_GENERATOR.md](Docs/DORK_GENERATOR.md) for the full template syntax, custom template guide and advanced usage.

---

## 💉 SQLi Detection Engine

When `--sqli` is enabled, DorkEye runs real injection probes on every discovered URL — not just keyword matching.

**Detection methods:**

- **Error-based** — matches MySQL, PostgreSQL, MSSQL, SQLite and Oracle error signatures
- **Differential analysis** — compares baseline vs. injected response using similarity scoring
- **GET parameter probing** — tests each `?param=value` individually
- **POST & JSON injection** — probes form data and API endpoints
- **Path-based injection** — tests numeric/slug path segments

**Confidence levels:** `LOW` · `MEDIUM` · `HIGH` · `CRITICAL`

Results are split in the HTML report into **SQLi VULN**, **SQLi SAFE** and **SQLi ALL** sub-filters for immediate triage.

---

## 🕵️ Stealth & Fingerprinting

DorkEye is built to avoid detection and rate-limiting from the ground up.

**HTTP Fingerprinting** — Rotates realistic browser profiles loaded from `http_fingerprints.json`. Each profile includes accurate `User-Agent`, `Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-*`, `Cache-Control` and `Pragma` headers — indistinguishable from real browser traffic.

**Stealth Mode** (`--stealth`) adds:

- Base delay: `5–8s` between requests
- Extended delay: `120–150s` every 2nd request (rate-limit avoidance pattern)
- Retry logic with exponential backoff on `429` / `503` responses
- Per-request fingerprint rotation

---

## 📊 Output Formats

### Interactive HTML Report

The HTML report is DorkEye's flagship output — a Matrix-themed interface with:

- **Stats dashboard** — total results, duplicates filtered, SQLi count, execution time
- **Filter bar** with sub-menus:
  - `DOC ▾` → ALL · PDF · DOCX · XLSX · PPT · ARCHIVES
  - `SQLi ▾` → SQLi ALL · SQLi VULN · SQLi SAFE
  - `SCRIPTS ▾` → ALL · PHP · ASP · SH/BAT · CONFIGS · CREDS
  - `PAGE` → web pages
- **Badge counters** on every filter and sub-filter
- **Active filter info bar** — shows how many results are currently visible
- **Direct download buttons** on file URLs
- **Animated Matrix background** (pure CSS/JS, no dependencies)

### Other Formats

| Format | Best For |
|---|---|
| `.json` | Pipeline integration, scripting, further processing |
| `.csv` | Spreadsheet analysis, sharing with stakeholders |
| `.txt` | Quick URL lists, feed into other tools |

All results are saved to the `Dump/` directory automatically.

---

## ⚙️ Configuration

Generate a sample config file:

```bash
python3 dorkeye.py --create-config
```

`dorkeye_config.yaml`:

```yaml
extensions:
  documents:   [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
  archives:    [".zip", ".rar", ".tar", ".gz", ".7z"]
  databases:   [".sql", ".db", ".sqlite", ".mdb"]
  backups:     [".bak", ".backup", ".old"]
  configs:     [".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".xml"]
  scripts:     [".php", ".asp", ".jsp", ".sh"]
  credentials: [".env", ".git", ".htpasswd"]

blacklist:             []
whitelist:             []
analyze_files:         true
sqli_detection:        false
http_fingerprinting:   true
stealth_mode:          false
request_timeout:       10
max_retries:           3
user_agent_rotation:   true
```

---

## 📁 Project Structure

```
DorkEye/
├── dorkeye.py                  ← Main framework
├── dork_generator.py           ← Dork Generator engine
├── requirements.txt            ← Python dependencies
├── setup.sh / setup.bat        ← Automated setup scripts
├── dorkeye_config.yaml         ← Default configuration
├── http_fingerprints.json      ← Browser fingerprint profiles
├── Templates/
│   ├── dorks_templates.yaml            ← Default dork templates
│   └── dorks_templates_research.yaml   ← Research-focused templates
├── Dump/                       ← Output directory (auto-created)
│   ├── *.html
│   ├── *.json
│   └── *.csv
└── Docs/
    ├── INSTALL.md
    └── DORK_GENERATOR.md
```

---

## 🔗 Tool Integration

DorkEye is designed to feed directly into other security tools:

```bash
# Generate SQLi targets → pass to sqlmap
python3 dorkeye.py --dg=sqli --sqli -o sqli.json
# → Parse sqli.json, extract VULN URLs → sqlmap -u "URL" --dbs

# Generate admin panels → feed to Nikto
python3 dorkeye.py --dg=admin -o admin.txt
# → nikto -h "URL"

# Exposed scripts → XSStrike
python3 dorkeye.py --dg=scripts --whitelist .php -o scripts.txt
# → python3 xsstrike.py -u "URL"

# Full recon → Nuclei template scan
python3 dorkeye.py --dg=all -o recon.json
# → nuclei -l urls.txt -t templates/
```

---

## ⚠️ Legal Disclaimer

> **This tool is intended strictly for educational, research and authorized security testing.**
>
> Attacking targets without prior mutual written consent is illegal. It is the end user's sole responsibility to comply with all applicable local, state and federal laws. The author accepts no liability for improper or unauthorized use of this software.
>
> - ✅ Only use on systems you own or have explicit written authorization to test
> - ✅ Always operate within the scope of your engagement
> - ✅ Use isolated environments and VPNs for operational security
> - ❌ Never test on live production systems without a signed scope agreement

---

## 📚 Documentation

| Document | Description |
|---|---|
| [INSTALL.md](INSTALL.md) | Detailed installation guide for all platforms |
| [Docs/DORK_GENERATOR.md](Docs/DORK_GENERATOR.md) | Full Dork Generator reference — templates, modes, custom templates |
| [dorkeye_config.yaml](dorkeye_config.yaml) | Configuration file reference |
| [http_fingerprints.json](http_fingerprints.json) | Browser fingerprint profile format |
| [Exploit-DB GHDB](https://www.exploit-db.com/google-hacking-database) | Google Hacking Database — dork inspiration |

---

## 🤝 Contributing

Contributions are welcome. If you have new dork templates, detection improvements or bug fixes:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit your changes: `git commit -m 'Add: description of change'`
4. Push and open a Pull Request

For template contributions, follow the YAML structure documented in [Docs/DORK_GENERATOR.md](Docs/DORK_GENERATOR.md).

---

<div align="center">

**DorkEye v4.2.6** · Built by [xPloits3c](https://github.com/xPloits3c) · MIT License

*For authorized security research only.*

---

*If DorkEye saved you time, consider leaving a ⭐ — it helps the project grow.*

</div>

---

<!-- GitHub discoverability hashtags -->
#osint #google-dorks #dorking #ethical-hacking #cybersecurity #recon #reconnaissance #sqli #sql-injection #penetration-testing #pentest #bug-bounty #security-research #duckduckgo #python #information-gathering #hacking-tools #google-hacking #google-hacking-database #ghdb #open-source #vulnerability-detection #dork-generator #web-security #red-team
