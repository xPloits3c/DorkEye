![537309991-f4f59199-d30f-4628-bb92-e6ccf43a6814](https://github.com/user-attachments/assets/ade7b159-8cd5-4b7f-980a-2bd76bed5589)

# DorkEye | Advanced OSINT Dorking Tool 🔍

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg)]()
[![DuckDuckGo](https://img.shields.io/badge/search-DuckDuckGo-orange.svg)]()
[![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
[![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat)](https://github.com/xPloits3c/DorkEye/stargazers)
[![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye)](https://github.com/xPloits3c/DorkEye/forks)
[![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye)](https://github.com/xPloits3c/DorkEye/issues)
[![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye)](https://github.com/xPloits3c/DorkEye/commits)
[![Join Telegram](https://img.shields.io/badge/Join%20Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/DorkEye)

---

## 🧠 What is DorkEye?

DorkEye is an advanced automated dorking and OSINT recon tool that leverages DuckDuckGo to discover exposed web resources through intelligent search queries. It combines a powerful dork generator, a full SQL injection detection engine, a 10-step autonomous analysis pipeline (Agents v3.0), and an adaptive recursive crawler — all without requiring any external AI or cloud services.

It can identify indexed directories, sensitive files, admin panels, databases, backups, configuration files, credentials, PII data, subdomains, and technology fingerprints — efficiently and with stealth controls.

### Why DuckDuckGo?

Using DuckDuckGo (via the `ddgs` library) allows DorkEye to:

- ✅ Bypass CAPTCHA and rate-limiting typical of mainstream search engines
- ✅ Maintain anonymity and privacy during searches
- ✅ Avoid IP blocks and detection mechanisms
- ✅ Access a clean, unfiltered index of web resources

---

## ✨ What's New in v4.8

- 🖥️ **3 new CLI modes** — `-u` for direct SQLi URL testing, `-f` for re-processing saved result files, `--dg-max` for configuring the dork generator limit
- 🔍 **ⓘ Detail popup in HTML report** — per-row popup with 11 fields: dork, snippet, SQLi method, payload, WAF, timestamp and more
- 📣 **Verbose SQLi output** — method + evidence printed immediately under each vulnerable URL in the terminal
- 🔄 **3 retry impulses** — dork searches now retry up to 3 times (`Retry 1/3`, `2/3`, `3/3`)
- 🤖 **Agents v3.0 pipeline** — expanded from 5 to 10 steps with 5 brand-new autonomous agents
- 🛡️ **HeaderIntelAgent** — detects info leak headers, outdated server versions, and missing security headers (HSTS, CSP, X-Frame-Options, etc.)
- 🧬 **TechFingerprintAgent** — identifies 35 technologies (CMS, frameworks, JS libraries, servers) and generates targeted CVE dorks
- 📧 **EmailHarvesterAgent** — collects and categorizes emails (admin, security, info, noreply, personal)
- 🔐 **PiiDetectorAgent** — detects PII: phone numbers, IBAN, Italian fiscal codes, credit cards (Luhn-validated), SSN, DOB
- 🌐 **SubdomainHarvesterAgent** — extracts subdomains and generates `site:subdomain` follow-up dorks for the adaptive crawler
- 📦 **Pattern library overhaul** — hash detection (bcrypt, MD5, SHA1/256/512, NTLM), 7 new cloud/SaaS secrets (Twilio, SendGrid, GitLab PAT, Docker PAT, NPM, etc.), centralized severity map, 8 new triage rules

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧙 **Interactive Wizard** | Guided session covering all options — ideal for first use |
| 🔎 **Smart Dorking** | Single dork, file of dorks, or auto-generated from YAML templates |
| ⚙️ **Dork Generator** | Template-based generator with `soft / medium / aggressive` modes and dynamic categories |
| 🎯 **Direct SQLi Test** | `-u URL` tests a single URL for SQL injection with full method + evidence output |
| 📂 **File Re-Processing** | `-f FILE` reloads saved results for fresh SQLi testing, analysis, or crawl |
| 🔒 **SQL Injection Engine** | Error-based, UNION-based, boolean blind, time-based — 4 methods per parameter |
| 🤖 **Agents v3.0 Pipeline** | 10-step autonomous analysis: triage → fetch → headers → tech → secrets → PII → emails → subdomains → report |
| 🌐 **Adaptive Crawler** | Recursive multi-round dorking that refines itself from each round's results |
| 🔐 **HTTP Fingerprinting** | 22 browser/OS fingerprints (Chrome, Firefox, Safari, Edge, mobile) for stealth |
| 📁 **Auto-Categorization** | 7 file categories: documents, archives, databases, backups, configs, scripts, credentials |
| 📊 **4 Output Formats** | HTML (interactive), JSON, CSV, TXT — all saved to `Dump/` |
| 🚫 **Extension Filtering** | Blacklist / whitelist specific file types |
| 📈 **Detailed Statistics** | Real-time metrics and category breakdowns |
| ⚙️ **Config Support** | YAML/JSON configuration files for reusable settings |
| 🎨 **Rich Terminal UI** | Progress bars, colored output, formatted panels |
| 🔄 **Rate Limit Protection** | Smart delays, extended cooldowns, stealth mode, 3 retry impulses |

---

## 📦 Installation

### Quick Install

```bash
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
```

### Linux / macOS — Automatic Setup

```bash
chmod +x setup.sh
./setup.sh
python3 -m venv venv
source venv/bin/activate
```

To exit or remove:

```bash
deactivate          # exit environment
rm -rf venv         # remove environment
```

### Windows — Automatic Setup

```bat
setup.bat
```

### Manual Installation (all platforms)

```bash
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate   # Windows: dorkeye_env\Scripts\activate
pip install -r requirements.txt
```

See [INSTALL.md](INSTALL.md) for detailed platform-specific instructions including Termux/Android.

---

## 🚀 Usage

### Interactive Wizard (recommended for first use)

```bash
python dorkeye.py --wizard
```

### Basic Search

```bash
# Single dork → auto-generates HTML report
python dorkeye.py -d "inurl:admin" -o results.html

# File of dorks, more results
python dorkeye.py -d dorks.txt -c 100 -o results.html

# Fast scan (no HEAD requests on found URLs)
python dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast.csv
```

### SQL Injection Detection

```bash
# Enable SQLi testing during a dork search
python dorkeye.py -d "site:example.com inurl:.php?id=" --sqli -o results.json

# SQLi + stealth mode (longer delays)
python dorkeye.py -d dorks.txt --sqli --stealth -o results.json

# Direct SQLi test on a single URL (NEW in v4.8)
python dorkeye.py -u "https://example.com/page.php?id=1"
python dorkeye.py -u "https://example.com/page.php?id=1" --sqli --stealth -o sqli_result.json
```

Terminal output when vulnerable:

```
[!] Potential SQLi found (critical): https://example.com/page.php?id=1
    ↳ method: error_based [param: id]  evidence: MYSQL error signature matched: extractvalue(0,...
    ↳ method: time_based_blind          evidence: SLEEP(5) triggered: elapsed=5.3s > threshold=5.2s
```

### Dork Generator

```bash
# All categories, soft mode (default)
python dorkeye.py --dg=all -o results.html

# Specific category + aggressive mode + SQLi
python dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o results.json

# Custom template file
python dorkeye.py --dg=backups --templates=dorks_templates_research.yaml -o results.json

# Higher combination limit (default: 800)
python dorkeye.py --dg=all --mode=aggressive --dg-max 10000 -o big.json
```

### Agents v3.0 — Integrated Analysis

```bash
# Automatic analysis when output is .json
python dorkeye.py -d "site:example.com" -o results.json

# Explicit analysis + page content download
python dorkeye.py -d "site:example.com" -o results.json --analyze --analyze-fetch

# All analysis options
python dorkeye.py -d dorks.txt \
  --analyze --analyze-fetch --analyze-fetch-max 50 \
  --analyze-fmt html --analyze-out analysis_report.html \
  -o results.json
```

### Re-Process Saved Results (NEW in v4.8)

```bash
# Re-run SQLi on a saved file
python dorkeye.py -f Dump/results.json --sqli -o retest.json

# Re-analyze with agents (massive fetch)
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch --analyze-fetch-max 5000 -o reanalyzed.json

# Full pipeline on saved file: SQLi + analysis + crawl
python dorkeye.py -f Dump/results.json --sqli --analyze --crawl -o full_retest.json
```

### Adaptive Recursive Crawl

```bash
# Basic crawl after initial search
python dorkeye.py -d "site:example.com inurl:admin" --crawl -o crawl.json

# Configured crawl with report
python dorkeye.py --dg=sqli --crawl --crawl-rounds 5 --crawl-max 400 --crawl-report -o crawl.json

# Full pipeline — generator + SQLi + analysis + crawl
python dorkeye.py --dg=sqli --mode=aggressive \
  --sqli --stealth \
  --analyze --analyze-fetch --analyze-fetch-max 50 \
  --crawl --crawl-rounds 6 --crawl-stealth \
  -o results.json
```

### Filter by Extension

```bash
# Only these extensions
python dorkeye.py -d "filetype:pdf OR filetype:xls" --whitelist .pdf .xls .xlsx -o docs.json

# Exclude extensions
python dorkeye.py -d "site:example.com" --blacklist .jpg .png .gif .svg -o no_images.json
```

---

## 🖥️ Command-Line Reference

### Input Sources (one required, mutually exclusive)

| Flag | Description |
|------|-------------|
| `--wizard` | Launch the interactive guided session |
| `-d DORK`, `--dork` | Single dork string or path to `.txt` file of dorks (one per line) |
| `-u URL`, `--url` | Single URL to test directly for SQL injection |
| `-f FILE`, `--file` | Load saved DorkEye results (`.json` or `.txt`) for re-processing |
| `--dg[=CATEGORY]` | Activate Dork Generator; optional value = category (`all` if omitted) |

### Output

| Flag | Default | Description |
|------|---------|-------------|
| `-o FILE`, `--output` | `report_TIMESTAMP.html` | Output file — extension sets format (`.html` / `.json` / `.csv` / `.txt`) |
| `-c N`, `--count` | `50` | Number of results to request per dork from DuckDuckGo |

### Configuration

| Flag | Description |
|------|-------------|
| `--config FILE` | Custom YAML or JSON configuration file |
| `--create-config` | Generate a sample `dorkeye_config.yaml` and exit |

### Scan Behaviour

| Flag | Description |
|------|-------------|
| `--sqli` | Enable SQL injection detection |
| `--stealth` | Stealth mode — longer delays, safer fingerprinting |
| `--no-analyze` | Skip HEAD requests on found URLs (faster, fewer details) |
| `--no-fingerprint` | Disable HTTP fingerprint rotation |
| `--blacklist EXT…` | Exclude these file extensions (e.g. `--blacklist .pdf .zip`) |
| `--whitelist EXT…` | Include only these file extensions |

### Dork Generator

| Flag | Default | Description |
|------|---------|-------------|
| `--dg[=CATEGORY]` | `all` | Category to generate (`all` = every category in the template) |
| `--dg-max N` | `800` | Max dork combinations per template |
| `--mode MODE` | `soft` | Generation aggressiveness: `soft` / `medium` / `aggressive` |
| `--templates=FILE` | `dorks_templates.yaml` | Template file in `Templates/`; use `all` for every YAML file |

### Agents v3.0 — Integrated Analysis

| Flag | Default | Description |
|------|---------|-------------|
| `--analyze` | off | Run the post-search analysis pipeline (auto-enabled with `.json` output) |
| `--analyze-fetch` | off | Download actual page content for HIGH/CRITICAL results |
| `--analyze-fetch-max N` | `20` | Maximum pages to download |
| `--analyze-fmt FORMAT` | `html` | Analysis report format: `html` / `md` / `json` / `txt` |
| `--analyze-out FILE` | auto | Path for the analysis report (default: next to the `-o` file) |

### Adaptive Recursive Crawl

| Flag | Default | Description |
|------|---------|-------------|
| `--crawl` | off | Enable adaptive recursive crawl after the initial search |
| `--crawl-rounds N` | `4` | Maximum crawl rounds |
| `--crawl-max N` | `300` | Total result limit across all crawl rounds |
| `--crawl-per-dork N` | `20` | DuckDuckGo results per dork per round |
| `--crawl-stealth` | off | Longer delays between crawl searches |
| `--crawl-report` | off | Generate a dedicated HTML crawl report |
| `--crawl-out FILE` | auto | Path for the crawl report |

---

## 🤖 Agents v3.0 — Analysis Pipeline

When `--analyze` is active (or `-o` is `.json`), DorkEye runs a 10-step autonomous analysis pipeline with no external AI required.

| Step | Agent | What it does |
|------|-------|-------------|
| 1 | **TriageAgent** | Scores every result 0–100 using regex + runtime bonuses (SQLi confirmed, accessible, GET params) |
| 2 | **PageFetchAgent** | Downloads page content for HIGH/CRITICAL results (retry, UA rotation, saves response headers) |
| 3 | **HeaderIntelAgent** | Analyzes saved headers: info leaks (Server, X-Powered-By), missing security headers (HSTS, CSP, X-Frame-Options), outdated versions |
| 4 | **TechFingerprintAgent** | Identifies 35 technologies with version extraction; generates targeted CVE dorks |
| 5 | **SecretsAgent** | Scans for 50+ secret patterns (API keys, JWTs, hashes, cloud credentials) with severity scoring |
| 6 | **PiiDetectorAgent** | Detects PII: email, phone (IT/EU/US), IBAN, fiscal code, credit card (Luhn-validated), SSN, DOB |
| 7 | **EmailHarvesterAgent** | Collects and categorizes emails (admin / security / info / noreply / personal) |
| 8 | **SubdomainHarvesterAgent** | Extracts subdomains and generates `site:subdomain` follow-up dorks |
| 9 | **LLM Analysis** | Optional — summary, patterns, recommendations (requires `dorkeye_llm_plugin.py`) |
| 10 | **ReportAgent** | Generates HTML/MD/JSON report with all sections: secrets, PII, emails, subdomains, CVE dorks |

---

## 🔒 SQL Injection Detection

DorkEye runs four complementary test methods on every URL parameter:

| Method | How it works |
|--------|-------------|
| **Error-based** | Injects payloads that trigger SQL error signatures (MySQL, PostgreSQL, MSSQL, SQLite, Oracle) |
| **UNION-based** | Probes column count and detects UNION response anomalies |
| **Boolean blind** | Compares response sizes between true/false conditions |
| **Time-based blind** | Measures delay induced by `SLEEP()` / `WAITFOR DELAY` payloads |

**v4.8 improvements:** verbose terminal output shows the exact method and evidence under each vulnerable URL; parameters are prioritized by attack surface (numeric IDs first, then known param names, then others).

---

## 📊 Output Formats

DorkEye saves all results to the `Dump/` folder.

| Extension | Format | Content |
|-----------|--------|---------|
| `.html` | Interactive HTML report | Matrix rain UI, filter bar, real-time search, export panel, per-row ⓘ detail popup, files panel |
| `.json` | Structured JSON | Full metadata + SQLi tests + agent findings (secrets, PII, emails, subdomains) + statistics |
| `.csv` | Spreadsheet CSV | URL, title, category, extension, file size, SQLi status, WAF, confidence |
| `.txt` | Plain text | Numbered list with per-result details |

The HTML report features:
- **Filter bar** — ALL / DOC / SQLi / SCRIPTS / PAGES with sub-filters per category
- **Real-time search** — across URL, title, category, dork simultaneously
- **⬇ Export Links** panel — export filtered URLs as TXT / JSON / CSV
- **📁 Export Files** panel — select and download file-type results individually
- **ⓘ Detail popup** — per-row popup with dork, snippet, SQLi method, evidence, WAF, timestamp (new in v4.8)

---

## 🗂️ File Categories

| Category | Extensions | Use case |
|----------|-----------|----------|
| 📄 Documents | `.pdf .doc .docx .xls .xlsx .ppt .pptx .odt .ods` | Office documents, reports |
| 📦 Archives | `.zip .rar .tar .gz .7z .bz2` | Compressed files, backups |
| 🗄️ Databases | `.sql .db .sqlite .mdb` | Database dumps, exports |
| 💾 Backups | `.bak .backup .old .tmp` | Backup files, temp data |
| ⚙️ Configs | `.conf .config .ini .yaml .yml .json .xml` | Configuration files |
| 📜 Scripts | `.php .asp .aspx .jsp .sh .bat .ps1` | Server-side scripts |
| 🔑 Credentials | `.env .git .svn .htpasswd` | Sensitive auth files |

---

## ⚙️ Configuration File

```bash
# Generate sample config
python dorkeye.py --create-config
```

Example `dorkeye_config.yaml`:

```yaml
extensions:
  documents: [".pdf", ".doc", ".docx", ".xls", ".xlsx"]
  archives:  [".zip", ".rar", ".tar", ".gz"]
  databases: [".sql", ".db", ".sqlite"]
  backups:   [".bak", ".backup", ".old"]
  configs:   [".conf", ".config", ".ini", ".yaml", ".json"]
  scripts:   [".php", ".asp", ".jsp", ".sh"]
  credentials: [".env", ".git", ".htpasswd"]

blacklist: []
whitelist: []

analyze_files:        true
max_file_size_check:  52428800  # 50 MB
sqli_detection:       false
stealth_mode:         false
http_fingerprinting:  true
user_agent_rotation:  true
request_timeout:      10
max_retries:          3
extended_delay_every_n_results: 100
```

---

## 📊 Example Dork File

Create a `dorks.txt` file with one dork per line (lines starting with `#` are ignored):

```
# Admin panels
inurl:admin intitle:login
inurl:administrator
site:.com inurl:wp-admin

# Sensitive files
filetype:sql "MySQL dump"
filetype:env DB_PASSWORD
filetype:log inurl:access.log

# Documents
site:.edu filetype:pdf "confidential"
site:.gov filetype:xls

# Configuration files
filetype:conf intext:password
ext:xml inurl:config
```

---

## 🎯 Use Cases

### Security Research

```bash
# Find exposed admin panels
python dorkeye.py -d "inurl:admin OR inurl:login" -c 100 -o admin_panels.json

# Search for database dumps
python dorkeye.py -d "filetype:sql" --whitelist .sql -o db_dumps.json

# Full SQLi scan with analysis
python dorkeye.py --dg=sqli --mode=medium --sqli --stealth \
  --analyze --analyze-fetch -o sqli_scan.json
```

### OSINT Investigations

```bash
# Gather leaked documents
python dorkeye.py -d "site:target.com filetype:pdf confidential" -o docs.json

# Find exposed credentials
python dorkeye.py -d "filetype:env OR filetype:git" --analyze -o credentials.json

# Subdomain + tech fingerprint intel
python dorkeye.py -d "site:target.com" --analyze --analyze-fetch -o recon.json
```

### Compliance Auditing

```bash
# Check for exposed backups
python dorkeye.py -d "site:company.com filetype:bak OR filetype:backup" -o backups.json

# Find configuration files
python dorkeye.py -d "site:company.com ext:conf OR ext:ini" -o configs.json
```

### Bug Bounty Hunting

```bash
# Multiple target dorks, all modes
python dorkeye.py -d bug_bounty_dorks.txt -c 200 --sqli --stealth -o bounty.json

# Use dork generator with adaptive crawl
python dorkeye.py --dg=all --mode=aggressive \
  --crawl --crawl-rounds 6 --crawl-stealth \
  -o bounty_crawl.json
```

### Re-Testing Saved Sessions

```bash
# Re-run SQLi on a file from a previous session
python dorkeye.py -f Dump/bounty.json --sqli -o retest.json

# Full re-analysis with agents
python dorkeye.py -f Dump/bounty.json \
  --analyze --analyze-fetch --analyze-fetch-max 5000 \
  -o full_analysis.json
```

---

## 📁 Project Structure

```
DorkEye/
├── dorkeye.py                     # Main script
├── dorkeye_agents.py              # Agents v3.0 — 10-step analysis pipeline
├── dorkeye_patterns.py            # Shared pattern library (secrets, PII, triage rules)
├── dorkeye_analyze.py             # Standalone analysis CLI
├── dork_generator.py              # Dynamic dork generator engine
├── http_fingerprints.json         # 22 HTTP fingerprint profiles (v2.0)
├── requirements.txt               # Python dependencies (pinned)
├── setup.sh                       # Linux/macOS automatic setup
├── setup.bat                      # Windows automatic setup
├── INSTALL.md                     # Detailed installation guide
├── README.md                      # This file
├── dorkeye_config.yaml            # Sample configuration file
│
├── Templates/
│   ├── dorks_templates.yaml       # Default dork template
│   └── dorks_templates_research.yaml
│
├── .github/
│   ├── CODE_OF_CONDUCT.md
│   ├── CONTRIBUTING.md
│   ├── SECURITY.md
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
└── Dump/                          # Auto-created output directory
    ├── *.html
    ├── *.json
    ├── *.csv
    └── *.txt
```

---

## 🔒 Best Practices

### Ethical Guidelines

- ✅ Always obtain written permission before testing
- ✅ Use only on authorized targets or public data
- ✅ Respect robots.txt and site policies
- ✅ Follow responsible disclosure for any findings
- ❌ Never access or download unauthorized data
- ❌ Never use for malicious purposes

### Operational Tips

- 🕒 Use `--stealth` for sensitive targets — longer delays reduce detection risk
- 🔄 Use `--crawl` to automatically refine and follow up on initial findings
- 📊 Open HTML reports for a visual overview before diving into JSON
- 🎯 Combine dork generator categories for layered recon
- 🔐 Use `-f` to re-test saved results without running new dork searches
- 💾 Keep dork template files organized in `Templates/`

---

## 🛠️ Troubleshooting

### `ModuleNotFoundError: No module named 'ddgs'`

```bash
pip install ddgs
```

### No results returned (0 results)

```bash
# Test with a simple dork to check connectivity
python dorkeye.py -d "python" -c 5 -o test.html

# If rate-limited, increase delay with stealth mode
python dorkeye.py -d dorks.txt --stealth -o results.html
```

### Virtual environment not activating

```bash
rm -rf dorkeye_env
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate   # Windows: dorkeye_env\Scripts\activate
pip install -r requirements.txt
```

For more troubleshooting, see [INSTALL.md](INSTALL.md).

---

## 🔄 Changelog

### v4.8 (Current)
- `-u URL` — direct SQLi test on a single URL
- `-f FILE` — re-process saved `.json` / `.txt` result files
- `--dg-max` — configurable dork generator combination limit
- HTML report: ⓘ per-row detail popup (dork, snippet, SQLi method/payload, WAF)
- Terminal: verbose SQLi output with method + evidence under each vulnerable URL
- Dork retry limit raised from 2 to 3 impulses
- Agents v3.0 pipeline: 5 → 10 steps
- 5 new agents: HeaderIntelAgent, TechFingerprintAgent, EmailHarvesterAgent, PiiDetectorAgent, SubdomainHarvesterAgent
- TriageAgent: runtime bonuses for SQLi confirmed, accessible:200, GET param count
- PageFetchAgent: retry (3 attempts), UA rotation, response headers saved
- SecretsAgent: hash detection, severity field, normalized dedup
- `dorkeye_patterns.py`: FETCH_UA_POOL, SECRET_SEVERITY map, PII_RULES, luhn_check()
- 13 new SECRET_RULES: 6 hash types + 7 cloud/SaaS (Twilio, SendGrid, GitLab PAT, etc.)
- 8 new TRIAGE_RULES: devops panels, monitoring, containers, log files, JWT, cloud keys, RCE candidates

### v4.7
- Security fix CWE-20/116/185/186: HTMLParser replaces regex `<script>` stripper
- HTML report: Search panel, Export Links panel, Export Files panel, per-panel ✕ close buttons
- HTTP fingerprints v2.0: 2 → 22 profiles (7 browser families, desktop + mobile)
- 14 bug fixes: Rich MarkupError, UNION precedence, closure capture, analyze_files default, HTML injection, and more
- Full escaping audit for all HTML and terminal output

### v4.6
- DorkCrawlerAgent — adaptive recursive crawl (`--crawl`)
- `dorkeye_agents.py` — TriageAgent, PageFetchAgent, SecretsAgent, ReportAgent
- `dorkeye_patterns.py` — centralized pattern library
- `--analyze` pipeline with HTML/MD/JSON/TXT report formats

### v4.4
- Complete wizard rewrite — all CLI options accessible interactively
- Deep SQLi engine rewrite — drastically reduced false positives
- `requirements.txt` pinned for reproducible installs

### v4.3
- Dynamic Dork Generator category system (`--dg`, `--mode`, `--templates`)
- Rich HTML report interface

### v4.2.6
- Dork Generator template engine — YAML-based, with variable interpolation
- Modular extensible architecture

### v3.1 (Legacy)
- HTTP fingerprinting with UA rotation
- SQLi detection engine (first version)
- Blacklist / whitelist extension system
- Enhanced file metadata extraction

### v3.0
- Complete rewrite with Rich UI
- File analysis and auto-categorization
- Multiple export formats (CSV, JSON, HTML)
- Configuration file support

---

## 🧩 Roadmap (v4.9+)

- `--templates=list` — print all available templates and categories
- Template YAML validation schema (pre-run integrity check)
- HTML report: sortable columns
- Profile presets (`--profile=recon`, `--profile=hardening`)
- `--no-output` flag for explicit opt-out of auto-save
- `sqli_agents.py` — dedicated SQLi module with YAML-driven payload files

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Contribution ideas: new dork templates, additional secret patterns, PII patterns for other regions, UI improvements, documentation improvements, bug fixes.

---

## ⚠️ Legal Disclaimer

> **READ CAREFULLY BEFORE USE**

This tool is provided for **educational, research, and authorized security testing purposes only**.

- ⚖️ Unauthorized access to computer systems is illegal in most jurisdictions
- 🔒 Always obtain written permission before testing any target
- 📜 Users are solely responsible for compliance with all applicable local, state, and federal laws
- 🚫 The author disclaims all liability for misuse or damages
- ✅ Use responsibly and ethically at all times

By using DorkEye, you agree to use it only on authorized targets or public information, comply with all applicable laws, and take full responsibility for your actions.

---

## 📞 Contact & Support

- **Author:** xPloits3c
- **Email:** whitehat.report@onionmail.org
- **GitHub:** [@xPloits3c](https://github.com/xPloits3c)
- **Telegram:** [t.me/DorkEye](https://t.me/DorkEye)

Support the project: ⭐ star the repository · 🐛 report bugs via Issues · 💡 suggest features via Discussions

---

## 🔗 Related Projects

[![MetaByte](https://img.shields.io/badge/MetaByte-Metadata_Extractor-blue?style=for-the-badge)](https://github.com/xPloits3c/MetaByte)

Check out **MetaByte** — Advanced metadata extraction tool.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> 🌟 If you found DorkEye useful, please star the repository! 🌟
>
> Made with ❤️ for you. Happy Dorking! Stay Legal, Stay Ethical! 🔍🔐
