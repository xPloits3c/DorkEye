# 🔍 DorkEye — Dork Generator

> **Automated OSINT query generation for ethical security research**

---

```
 ___
__H__       xploits3c.github.io/DorkEye
 [,]
 [)]
 [;]    DorkEye | Security Dorking Framework
 |_|                         v4.2.6
  V
```

---

## 📌 Table of Contents

- [What is the Dork Generator?](#what-is-the-dork-generator)
- [How It Works](#how-it-works)
- [Why It's Better Than Manual Google Dorks](#why-its-better-than-manual-google-dorks)
- [Template System](#template-system)
- [Categories](#categories)
- [Generation Modes](#generation-modes)
- [CLI Usage](#cli-usage)
- [YAML Template Structure](#yaml-template-structure)
- [Writing Custom Templates](#writing-custom-templates)
- [Combining with Other Features](#combining-with-other-features)
- [Real-World Use Cases](#real-world-use-cases)
- [Comparison Table](#comparison-table)
- [Tips & Best Practices](#tips--best-practices)
- [Roadmap](#roadmap)
- [Legal Disclaimer](#legal-disclaimer)

---

## What is the Dork Generator?

The **Dork Generator** (`--dg`) is the query automation engine at the core of DorkEye v4.2.6. Instead of manually writing individual [Google Dorks](https://www.exploit-db.com/google-hacking-database) or [DuckDuckGo](https://duckduckgo.com) search queries, it reads structured YAML templates and generates optimized, category-specific dork strings at scale — ready to be fired directly through DorkEye's search engine.

Think of it as a **dork compiler**: you describe *what you want to find*, it produces the precise queries needed to find it.

```bash
# Without Dork Generator — manual, slow, error-prone
python3 dorkeye.py -d "site:example.com filetype:sql"
python3 dorkeye.py -d "site:example.com inurl:phpmyadmin"
python3 dorkeye.py -d "site:example.com ext:bak"

# With Dork Generator — automated, scalable, reproducible
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.html
```

---

## How It Works

The Dork Generator operates in three phases:

### Phase 1 — Template Loading

DorkEye reads one or more YAML template files from the `/Templates` directory. Each file contains categories (e.g., `sqli`, `backups`, `admin`) with lists of parameterized dork patterns.

```
Templates/
├── dorks_templates.yaml          ← default
├── dorks_templates_research.yaml ← research-focused
└── dorks_templates_custom.yaml   ← your custom templates
```

### Phase 2 — Query Generation

The `DorkGenerator` class processes the templates and expands every pattern according to the selected **mode** (soft / medium / aggressive). More aggressive modes produce more queries with deeper operator combinations.

```
Template pattern → [ site:{target} inurl:{path} ext:{ext} ]
                 ↓
Generated dorks → site:example.com inurl:backup ext:sql
                  site:example.com inurl:db ext:bak
                  site:example.com inurl:dump ext:gz
                  ... (N queries based on mode)
```

### Phase 3 — Execution

Each generated dork is passed to DorkEye's search engine (DuckDuckGo via `DDGS()`), which returns URLs. These are deduplicated, filtered, optionally analyzed for SQLi, and saved to the output report.

```
Generated Dorks → DuckDuckGo Search → URL Results → Analysis → Report
```

---

## Why It's Better Than Manual Google Dorks

| Feature | Manual Dorks | DorkEye Dork Generator |
|---|---|---|
| Query writing | Manual, one by one | Automated from templates |
| Scale | Limited by patience | Hundreds of queries in one run |
| Deduplication | Manual | Automatic (MD5 hash-based) |
| Operator coverage | Depends on user knowledge | Comprehensive per category |
| Reproducibility | None | Full (same template = same dorks) |
| SQLi correlation | None | Auto-tested per result |
| CAPTCHA avoidance | High risk on Google | DuckDuckGo, no CAPTCHA |
| Stealth | None | Rate limiting, UA rotation, fingerprinting |
| Output | Copy/paste | CSV, JSON, HTML report |
| Category targeting | Manual | `--dg=sqli`, `--dg=backups`, etc. |
| Mode tuning | N/A | soft / medium / aggressive |

### The CAPTCHA Problem

Tools that use **Google Search** directly hit CAPTCHA blocks after a few requests, making automation nearly impossible without paid API keys or proxy farms.

DorkEye routes all queries through **[DuckDuckGo](https://duckduckgo.com)** using the `DDGS()` library, which is far more resistant to automated query blocks. The result: you get clean, uninterrupted bulk searches without spending anything on APIs or proxies.

### Operator Intelligence

A manual analyst typically uses 2–3 operators per query (`site:`, `filetype:`, `inurl:`). The Dork Generator systematically combines all relevant operators for each category:

```
site:       ─→ target domain scoping
inurl:      ─→ path pattern matching
intitle:    ─→ page title targeting
filetype:   ─→ extension-based discovery
ext:        ─→ alternative extension operator
intext:     ─→ page content matching
```

This guarantees operator coverage that would take hours to replicate manually.

---

## Template System

Templates are YAML files stored in `Templates/`. DorkEye ships with a default template (`dorks_templates.yaml`) covering the most important OSINT and security research categories. You can extend, fork, or completely replace them.

### Selecting Templates

```bash
# Default template (auto-selected)
python3 dorkeye.py --dg=all

# Specific template file
python3 dorkeye.py --dg=all --templates=dorks_templates_research.yaml

# Load ALL templates in the Templates/ folder
python3 dorkeye.py --dg=all --templates=all
```

> ⚠️ The `--templates=` syntax requires `=` (no space). Using `--templates filename.yaml` will raise an error.

---

## Categories

Each template file defines a set of **categories**. You can target a single category or run all of them at once.

### Built-in Categories (default template)

| Category | What It Targets | Example Dorks Generated |
|---|---|---|
| `sqli` | SQL-injectable URLs with parameters | `site:example.com inurl:".php?id="` |
| `admin` | Admin panels and login interfaces | `site:example.com intitle:"admin panel"` |
| `backups` | Exposed backup files | `site:example.com ext:bak OR ext:old` |
| `databases` | Database files indexed publicly | `site:example.com filetype:sql` |
| `configs` | Configuration files | `site:example.com ext:env OR ext:conf` |
| `credentials` | Credential files (.env, .htpasswd, etc.) | `site:example.com inurl:.env` |
| `documents` | Sensitive documents | `site:example.com filetype:pdf intitle:confidential` |
| `logs` | Server log files | `site:example.com ext:log` |
| `cameras` | Exposed webcam/IP camera interfaces | `inurl:"/view/index.shtml"` |
| `open_dirs` | Open directory listings | `intitle:"index of /" site:example.com` |
| `errors` | Verbose error pages with stack traces | `site:example.com intext:"SQL syntax"` |

### Listing Available Categories

```bash
# Let DorkEye read the template and tell you what's available
python3 dorkeye.py --dg=INVALID_CATEGORY
# → Error: Invalid category 'INVALID_CATEGORY'. Available: admin, backups, configs, ...
```

---

## Generation Modes

The `--mode` flag controls how many dorks are generated per category and how deeply operator combinations are expanded.

| Mode | Volume | Use Case |
|---|---|---|
| `soft` | Low | Quick scan, minimal noise, safe for rate-limited environments |
| `medium` | Moderate | Balanced — good for most assessments |
| `aggressive` | High | Deep coverage, maximum operator combinations, pair with `--stealth` |

```bash
# Soft — quick recon
python3 dorkeye.py --dg=admin --mode=soft -o quick_scan.html

# Medium — standard pentest
python3 dorkeye.py --dg=all --mode=medium -o full_scan.html

# Aggressive — thorough, use stealth
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o deep_sqli.html
```

> 💡 Always pair `--mode=aggressive` with `--stealth` to avoid triggering rate limits. Aggressive mode generates enough queries to be detected by anti-bot systems without proper pacing.

---

## CLI Usage

### Full Syntax

```bash
python3 dorkeye.py --dg[=CATEGORY] [--mode=MODE] [--templates=FILE] [OPTIONS] -o OUTPUT
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `--dg` | (none) | Enable Dork Generator. Optionally specify a category: `--dg=sqli` |
| `--dg=all` | — | Run all categories found in the template |
| `--mode` | `soft` | Generation intensity: `soft`, `medium`, `aggressive` |
| `--templates` | `dorks_templates.yaml` | Template file to use, or `all` to load every `.yaml` in `Templates/` |
| `--sqli` | off | Enable real SQL injection testing on results |
| `--stealth` | off | Enable rate-limit protection, extended delays, fingerprint rotation |
| `--no-fingerprint` | off | Disable HTTP fingerprinting (faster, less stealthy) |
| `-o` / `--output` | (none) | Output file name (`.html`, `.json`, `.csv`, `.txt`) |
| `-c` / `--count` | `50` | Max results per dork query |
| `--blacklist` | (none) | Skip URLs with these extensions: `--blacklist .pdf .doc` |
| `--whitelist` | (none) | Only keep URLs with these extensions: `--whitelist .php .asp` |

### Common Recipes

```bash
# === DISCOVERY ===

# Full OSINT sweep — all categories, default mode
python3 dorkeye.py --dg=all -o recon_report.html

# Admin panel hunting
python3 dorkeye.py --dg=admin --mode=medium -o admin_panels.html

# Exposed backup files
python3 dorkeye.py --dg=backups --mode=aggressive -o backups.html

# Credential file discovery
python3 dorkeye.py --dg=credentials --mode=aggressive -o creds.html

# === SQL INJECTION ===

# SQLi discovery + live testing + stealth
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o sqli_report.html

# SQLi with JSON output for pipeline integration
python3 dorkeye.py --dg=sqli --mode=medium --sqli -o sqli_results.json

# === MULTI-TEMPLATE ===

# Load all templates, run all categories
python3 dorkeye.py --dg=all --templates=all --mode=medium -o complete.html

# Custom research template
python3 dorkeye.py --dg=all --templates=dorks_templates_research.yaml -o research.html

# === FILTERED OUTPUT ===

# Only PHP files
python3 dorkeye.py --dg=sqli --whitelist .php -o php_only.html

# Exclude documents
python3 dorkeye.py --dg=all --blacklist .pdf .doc .docx -o no_docs.html
```

---

## YAML Template Structure

```yaml
# Templates/dorks_templates.yaml

_meta:
  version: "1.0"
  author: "xPloits3c"
  description: "DorkEye default template"

templates:

  # ── Category name ──────────────────────────────
  sqli:
    description: "SQL injection point discovery"
    dorks:
      soft:
        - 'inurl:".php?id="'
        - 'inurl:".asp?id="'
      medium:
        - 'inurl:".php?id=" intext:"error"'
        - 'inurl:"index.php?cat="'
        - 'inurl:"item.php?id="'
        - 'inurl:"news.php?id="'
      aggressive:
        - 'inurl:".php?id=" intext:"mysql_fetch"'
        - 'inurl:".asp?id=" intext:"ODBC"'
        - 'inurl:"view.php?pid="'
        - 'inurl:"article.php?id="'
        - 'inurl:"product.php?id="'
        - 'inurl:"cat.php?id="'
        - 'inurl:"detail.php?id="'
        - 'inurl:"read.php?id="'

  # ── Another category ───────────────────────────
  backups:
    description: "Exposed backup files"
    dorks:
      soft:
        - 'ext:bak'
        - 'ext:old'
      medium:
        - 'ext:bak inurl:backup'
        - 'ext:sql inurl:dump'
        - 'filetype:tar.gz inurl:backup'
      aggressive:
        - 'ext:bak OR ext:old OR ext:backup'
        - 'inurl:"backup" filetype:zip'
        - 'intitle:"index of" "backup"'
        - 'ext:sql intext:"CREATE TABLE"'
```

### Key Rules

- **Mode inheritance**: A `medium` run includes `soft` dorks plus `medium` dorks. `aggressive` includes all three levels.
- **No `_meta` required**: The `_meta` block is optional metadata, not used by the engine.
- **Multiple templates**: When `--templates=all` is used, categories from all YAML files are merged. Duplicate category names are combined.

---

## Writing Custom Templates

Creating a custom template lets you target specific industries, technologies, or attack surfaces.

### Step 1 — Create the file

```bash
touch Templates/my_custom_template.yaml
```

### Step 2 — Define your categories

```yaml
templates:

  iot_devices:
    description: "Exposed IoT management interfaces"
    dorks:
      soft:
        - 'intitle:"RouterOS" inurl:winbox'
        - 'intitle:"Hikvision" inurl:doc/page/login.asp'
      medium:
        - 'intitle:"Netgear" inurl:/setup.cgi'
        - 'inurl:"/cgi-bin/luci" intitle:"OpenWrt"'
      aggressive:
        - 'intitle:"TP-Link" inurl:userRpm'
        - 'inurl:"/dana-na/auth/url_default/welcome.cgi"'
        - 'intitle:"Ubiquiti" inurl:/login.cgi'

  cloud_misconfig:
    description: "Cloud misconfiguration discovery"
    dorks:
      soft:
        - 'site:s3.amazonaws.com "index of"'
        - 'site:blob.core.windows.net'
      medium:
        - 'site:s3.amazonaws.com filetype:pdf confidential'
        - 'site:storage.googleapis.com ext:sql'
      aggressive:
        - 'site:s3.amazonaws.com ext:env OR ext:config'
        - 'site:blob.core.windows.net inurl:backup'
        - 'site:storage.googleapis.com intitle:"index of"'
```

### Step 3 — Use it

```bash
python3 dorkeye.py --dg=iot_devices --templates=my_custom_template.yaml --mode=aggressive -o iot_report.html
```

### Step 4 — Validate

```bash
# Python quick-check (no installation needed)
python3 -c "import yaml; yaml.safe_load(open('Templates/my_custom_template.yaml')); print('Template OK')"
```

---

## Combining with Other Features

The Dork Generator becomes much more powerful when combined with DorkEye's other subsystems.

### + SQLi Detector

```bash
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o sqli_full.html
```

The `--sqli` flag activates `SQLiDetector`, which tests every result URL for:
- **GET parameter injection** — probes each `?param=value` with payloads
- **Error-based detection** — matches MySQL, PostgreSQL, MSSQL, SQLite, Oracle error signatures
- **Differential analysis** — compares baseline response vs. injected response similarity
- **Time-based hints** — detects abnormal response time increases
- **POST / JSON support** — tests forms and API endpoints too

Results are then split in the HTML report into **SQLi VULN**, **SQLi SAFE**, and **SQLi ALL** sub-filters.

### + HTTP Fingerprinting

```bash
python3 dorkeye.py --dg=all --mode=medium -o scan.html
# Fingerprinting is ON by default

python3 dorkeye.py --dg=all --no-fingerprint -o fast_scan.html
# Disable for speed
```

HTTP fingerprinting rotates realistic browser profiles (Chrome, Firefox, Safari, Edge) with accurate `User-Agent`, `Accept`, `Accept-Language`, `Sec-Fetch-*`, and `Cache-Control` headers. This makes requests indistinguishable from real browser traffic.

### + Stealth Mode

```bash
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o paranoid.html
```

Stealth mode activates:
- Extended random delays between requests (`5–8s` base, `120–150s` extended)
- Full HTTP fingerprint rotation per request
- Rate-limit pattern avoidance
- Backoff on 429/503 responses

### + Output Formats

```bash
# Interactive HTML report (recommended)
python3 dorkeye.py --dg=all -o report.html

# Machine-readable JSON for pipeline integration
python3 dorkeye.py --dg=sqli --sqli -o results.json

# Spreadsheet-ready CSV
python3 dorkeye.py --dg=all -o results.csv

# Plain text URL list
python3 dorkeye.py --dg=all -o urls.txt
```

---

## Real-World Use Cases

### 🔐 Bug Bounty — SQLi Scope Recon

```bash
# 1. Generate and run aggressive SQLi dorks with live testing
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o bb_sqli.html

# 2. Open report → filter SQLi › VULN to see confirmed endpoints
# 3. Pass confirmed URLs to sqlmap for further exploitation
sqlmap -u "https://target.com/page.php?id=1" --dbs
```

### 🏢 Internal Red Team — Pre-engagement Recon

```bash
# Full surface mapping before engagement
python3 dorkeye.py --dg=all --templates=all --mode=medium --stealth -o recon_full.html

# Focus on admin panels
python3 dorkeye.py --dg=admin --mode=aggressive -o admin.html

# Credential file exposure
python3 dorkeye.py --dg=credentials --mode=aggressive -o creds.html
```

### 📊 Security Audit — Client Exposure Report

```bash
# Generate professional HTML report with all findings
python3 dorkeye.py --dg=all --mode=medium --sqli -o client_report.html

# The HTML report includes:
# → Executive summary stats
# → Filterable results table (DOC › PDF, SQLi › VULN, SCRIPTS › PHP...)
# → Direct download links for exposed files
# → SQLi status per URL
```

### 🔬 Research — Mapping Attack Surface Trends

```bash
# JSON output for data analysis
python3 dorkeye.py --dg=all --templates=all --mode=aggressive -o data.json

# Load into pandas, plot category distribution, track over time
python3 -c "
import json, collections
data = json.load(open('Dump/data.json'))
cats = collections.Counter(r['category'] for r in data['results'])
print(cats.most_common())
"
```

---

## Comparison Table

How does DorkEye's Dork Generator compare to other tools in the space?

| | DorkEye `--dg` | Manual Google Dorks | GHDB Tools | Commercial Scanners |
|---|---|---|---|---|
| **No CAPTCHA** | ✅ DuckDuckGo | ❌ Google blocks fast | Varies | Varies |
| **Template-based** | ✅ YAML | ❌ | Some | Some |
| **Custom categories** | ✅ Full control | ✅ (manually) | Limited | Rarely |
| **SQLi detection** | ✅ Built-in | ❌ | ❌ | ✅ |
| **Stealth mode** | ✅ Full | ❌ | Rarely | Varies |
| **HTTP fingerprinting** | ✅ | ❌ | ❌ | Some |
| **Deduplication** | ✅ MD5-based | Manual | Basic | ✅ |
| **Output formats** | HTML, JSON, CSV, TXT | Manual | Basic | ✅ |
| **Interactive report** | ✅ Matrix UI + filters | ❌ | ❌ | ✅ |
| **Open source** | ✅ MIT | N/A | Varies | ❌ |
| **Cost** | Free | Free | Free | $$$  |

---

## Tips & Best Practices

### ✅ Do

- Always use `--stealth` with `--mode=aggressive`
- Pair `--dg=sqli` with `--sqli` for correlated injection results
- Use `--whitelist .php .asp .aspx` to focus on dynamic pages for SQLi scanning
- Start with `--mode=soft` on new targets, escalate to `aggressive` after baseline
- Combine multiple runs: first `--dg=admin`, then `--dg=sqli` on confirmed dynamic pages
- Use `--templates=all` for maximum coverage when time allows
- Save to `.html` for human analysis, `.json` for tool integration

### ❌ Don't

- Don't use `--mode=aggressive` without `--stealth` — you will be rate-limited
- Don't use `--templates=` with a space: always `--templates=filename.yaml`
- Don't run `--dg` and `-d` together — pick one input source
- Don't test on targets without written authorization

### ⚙️ Performance Tuning

```bash
# Increase result count per dork (default: 50)
python3 dorkeye.py --dg=all -c 100 -o results.html

# Disable file analysis for faster runs (no HEAD requests)
python3 dorkeye.py --dg=all --no-analyze -c 200 -o fast.html

# Disable fingerprinting for maximum speed (less stealthy)
python3 dorkeye.py --dg=all --no-fingerprint --no-analyze -o turbo.html
```

---

## Roadmap

Future improvements planned for the Dork Generator:

- [ ] **Target-aware generation** — inject domain/IP directly into template patterns via `--target example.com`
- [ ] **Dork scoring** — rank generated dorks by historical hit rate
- [ ] **Community template registry** — pull templates directly from a curated online repository
- [ ] **Operator auto-expansion** — AI-assisted operator combination for niche targets
- [ ] **Export to sqlmap** — one-click export of SQLi VULN results to sqlmap command list
- [ ] **Shodan / Censys bridge** — route generated patterns to specialized engines
- [ ] **Category tagging on results** — link each found URL back to the specific dork that found it

---

## Legal Disclaimer

> ⚠️ **This tool is intended for educational, research, and authorized security testing only.**
>
> Attacking targets without prior mutual consent is illegal. It is the end user's responsibility to comply with all applicable local, state, and federal laws. The author disclaims all liability for improper or unauthorized use.
>
> - Never test on systems you do not own or do not have explicit written permission to test.
> - Always operate within the scope defined in your engagement rules of engagement.
> - Use isolated environments and VPNs for additional operational security.

---

## See Also

- [README.md](../README.md) — Main project documentation
- [INSTALL.md](../INSTALL.md) — Installation guide
- [http_fingerprints.json](../http_fingerprints.json) — Browser fingerprint profiles
- [dorkeye_config.yaml](../dorkeye_config.yaml) — Configuration reference
- [Exploit-DB GHDB](https://www.exploit-db.com/google-hacking-database) — Google Hacking Database

---

<div align="center">

**DorkEye v4.2.6** · [xPloits3c](https://github.com/xPloits3c) · MIT License

*For authorized security research only*

</div>

---

<!-- GitHub topic hashtags for discoverability -->
#google-dorks #dorking #osint #dork-generator #google-hacking #ethical-hacking #cybersecurity #sqli #sql-injection #duckduckgo #security-research #reconnaissance #recon #pentest #penetration-testing #bug-bounty #vulnerability-detection #information-gathering #hacking-tools #python #open-source #dorking-tool #google-hacking-database #ghdb #osint-tool #dorkeyeframework
