# DorkEye Project — Complete Usage Reference

Every flag, every mode, every combination — explained.

```
 ___
__H__       xploits3c.github.io/DorkEye
 [d]
 [e]
 [;]    DorkEye | USAGE
 |_|
  V
```

-----

## 📌 Basic Syntax

```bash
python3 dorkeye.py [OPTIONS]
```

DorkEye operates in **five distinct modes**, each triggered by different flags:

|Mode                  |Trigger   |Description                                      |
|----------------------|----------|-------------------------------------------------|
|**Interactive Wizard**|`--wizard`|Guided menu-driven session                       |
|**Dork Search**       |`-d`      |Search with manual or file-based dorks           |
|**Dork Generator**    |`--dg`    |Auto-generate dorks from YAML templates          |
|**Direct URL Test**   |`-u`      |Test a single URL for SQLi                       |
|**File Reload**       |`-f`      |Re-process saved results (SQLi / analyze / crawl)|

Minimal required: at least one of `-d`, `--dg`, `-u`, or `-f`. Output `-o` is auto-generated if omitted.

-----

## ══════════════════════════════════════════

## CORE FLAGS

## ══════════════════════════════════════════

### 🔹 `--wizard` — Interactive Mode

Launches a fully guided session with numbered menus. Covers dork search, dork generation, analysis, and crawl — no flags needed.

```bash
python3 dorkeye.py --wizard
```

The wizard will prompt for:

- Dork input (single string or file)
- Results per dork
- SQLi / stealth / fingerprinting toggles
- Output filename and format
- Post-search analysis (if output is `.json`)
- Recursive crawl options

-----

### 🔹 `-d` / `--dork` — Dork Input

Defines the search query. Accepts a single dork string or a `.txt` file (one dork per line, `#` lines ignored).

```bash
# Single dork
python3 dorkeye.py -d "inurl:admin filetype:php" -o output.html

# File with multiple dorks
python3 dorkeye.py -d dorks.txt -c 100 -o output.json
```

💡 For automation and large-scale scans, always use files.

-----

### 🔹 `-u` / `--url` — Direct URL SQLi Test

Tests a single URL directly for SQL injection. No search is performed.
Automatically enables `--sqli` if not specified.

```bash
# Basic direct test
python3 dorkeye.py -u "https://example.com/page.php?id=1" --sqli

# With stealth and output
python3 dorkeye.py -u "https://example.com/page.php?id=1" --sqli --stealth -o sqli_result.json
```

**Output includes:**

- Vulnerability status (SAFE / VULNERABLE)
- Confidence level (NONE → LOW → MEDIUM → HIGH → CRITICAL)
- Detection method and evidence
- WAF detection

-----

### 🔹 `-f` / `--file` — Load Saved Results

Loads results from a previously saved `.json` or `.txt` file and re-processes them.
Combine with `--sqli`, `--analyze`, or `--crawl` to run additional analysis on existing data.

```bash
# Re-run SQLi on saved results
python3 dorkeye.py -f Dump/results.json --sqli -o retest.json

# Run analysis pipeline on saved results
python3 dorkeye.py -f Dump/results.json --analyze -o reanalyzed.json

# Full re-processing: SQLi + analysis + crawl
python3 dorkeye.py -f Dump/results.json --sqli --analyze --crawl -o full_retest.json
```

**Supported formats:**

- `.json` — DorkEye JSON output (supports both `{"results": [...]}` and raw `[...]`)
- `.txt` — One URL per line (lines starting with `http`)

The file is searched in the current directory first, then in `Dump/`.

-----

### 🔹 `-o` / `--output` — Output Filename

Specifies the output filename. The file is saved inside the `Dump/` folder.
Format is inferred from the extension.

```bash
python3 dorkeye.py -d dorks.txt -o results.json
python3 dorkeye.py -d dorks.txt -o report.html
python3 dorkeye.py -d dorks.txt -o export.csv
python3 dorkeye.py -d dorks.txt -o links.txt
```

|Extension|Format            |Features                                                                                |
|---------|------------------|----------------------------------------------------------------------------------------|
|`.json`  |Structured JSON   |Full metadata, statistics, SQLi details. Enables `--analyze` prompt.                    |
|`.html`  |Interactive report|Dark matrix theme, filters, search, export panels, SQLi badges, WAF labels, file browser|
|`.csv`   |Spreadsheet-ready |All columns including SQLi status, WAF, confidence                                      |
|`.txt`   |Plain text        |Numbered list with per-result details                                                   |

If `-o` is omitted, DorkEye auto-generates `report_YYYYMMDD_HHMMSS.html`.

💡 Using `.json` output automatically prompts for post-search analysis.

-----

### 🔹 `-c` / `--count` — Results per Dork

Limits the maximum number of results fetched per dork query. Default: **50**.

```bash
python3 dorkeye.py -d dorks.txt -c 200 -o output.html
```

**Notes:**

- Higher values = slower scans and higher risk of rate-limiting
- Use `--stealth` when `-c > 100`
- DorkEye automatically applies extended delays every 100 results (configurable)

-----

### 🔹 `--config` — Custom Configuration File

Loads a YAML or JSON configuration file that overrides the defaults.

```bash
python3 dorkeye.py -d dorks.txt --config custom_config.yaml -o scan.json
```

Configurable settings include: extensions map, blacklist/whitelist, timeouts, retry count, stealth mode, fingerprinting, SQLi detection, and the extended delay threshold.

See `--create-config` to generate a starter template.

-----

### 🔹 `--create-config` — Generate Default Config

Writes a sample `dorkeye_config.yaml` to disk.

```bash
python3 dorkeye.py --create-config
```

-----

## ══════════════════════════════════════════

## DETECTION & STEALTH

## ══════════════════════════════════════════

### 🔹 `--sqli` — SQL Injection Detection

Enables the multi-method SQLi detection engine on all discovered URLs.

```bash
python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o sqli_scan.html
```

**Detection pipeline (per parameter, in order):**

|Method              |Description                                                                                          |
|--------------------|-----------------------------------------------------------------------------------------------------|
|**Error-based**     |Injects payloads that trigger DB-specific error signatures (MySQL, PostgreSQL, MSSQL, SQLite, Oracle)|
|**UNION-based**     |Probes column count with `UNION SELECT NULL,...` and detects mismatch errors or response anomalies   |
|**Boolean blind**   |Compares response sizes for true/false condition pairs with statistical noise filtering              |
|**Time-based blind**|Measures `SLEEP()`-induced response delays above baseline + margin                                   |

**Additional features:**

- Parameter priority sorting (high / medium / low risk)
- Adaptive noise probing before each parameter test
- WAF detection (Cloudflare, ModSecurity, Wordfence, Sucuri, Imperva, Akamai, F5 BigIP, Barracuda, FortiWeb, AWS WAF, DenyAll, Reblaze)
- Circuit breaker: auto-skips unreachable hosts
- Confidence scoring: NONE → LOW → MEDIUM → HIGH → CRITICAL

**POST and JSON injection** are available programmatically via `SQLiDetector.test_post_sqli()` and `SQLiDetector.test_json_sqli()`.

-----

### 🔹 `--stealth` — Stealth Mode

Reduces detection and rate-limiting risks by increasing delays and randomization.

```bash
python3 dorkeye.py -d dorks.txt --stealth -o stealth_scan.html
```

**What it activates:**

- Extended randomized delays between requests (1.4×–1.8× multiplier)
- Longer inter-dork waits
- Extended rate-limit pauses (120–150s vs. 85–110s)
- Additional delays during SQLi testing

✅ Strongly recommended for: sensitive targets, long scans, SQLi testing, high `-c` values.

-----

### 🔹 `--no-fingerprint` — Disable HTTP Fingerprinting

Disables the browser fingerprint rotation system. Falls back to basic User-Agent rotation.

```bash
python3 dorkeye.py -d dorks.txt --no-fingerprint -o output.html
```

By default, DorkEye loads `http_fingerprints.json` and rotates full browser profiles (User-Agent, Accept, Accept-Language, Accept-Encoding, Sec-Fetch-*, Cache-Control) to mimic real browser traffic.

-----

### 🔹 `--no-analyze` — Disable File Analysis

Skips HEAD-request file analysis for faster scans. No size, content-type, or accessibility checks.

```bash
python3 dorkeye.py -d dorks.txt --no-analyze -o fast_scan.txt
```

|Mode          |Speed |Metadata                            |
|--------------|------|------------------------------------|
|Default       |Medium|File size, content-type, HTTP status|
|`--no-analyze`|Fast  |None                                |

-----

### 🔹 `--blacklist` — Extension Blacklist

Excludes specific file types from results.

```bash
python3 dorkeye.py -d "site:target.com" --blacklist .jpg .png .gif -o no_images.html
```

-----

### 🔹 `--whitelist` — Extension Whitelist

Only includes specific file types. All other extensions are ignored.

```bash
python3 dorkeye.py -d "site:target.com" --whitelist .pdf .xls .docx -o documents.html
```

-----

## ══════════════════════════════════════════

## DORK GENERATOR

## ══════════════════════════════════════════

### 🔹 `--dg` — Activate Dork Generator

Generates structured Google dorks from YAML template files. Replaces manual dork writing with a scalable, category-based engine.

```bash
# All categories, soft mode (default)
python3 dorkeye.py --dg

# Specific category
python3 dorkeye.py --dg=sqli
python3 dorkeye.py --dg=backups
python3 dorkeye.py --dg=sensitive
python3 dorkeye.py --dg=admin

# All categories, explicit
python3 dorkeye.py --dg=all
```

**Architecture note:** `--dg` controls *dork generation*. `--sqli` controls *SQLi detection*. They are independent.

```bash
# Generate SQLi dorks AND test them
python3 dorkeye.py --dg=sqli --sqli --mode=aggressive -o report.html
```

-----

### 🔹 `--mode` — Generation Mode

Controls dork generation intensity. Default: `soft`.

|Mode        |Behavior                                    |
|------------|--------------------------------------------|
|`soft`      |Safe, minimal footprint. Fewer combinations.|
|`medium`    |Balanced coverage.                          |
|`aggressive`|Maximum coverage. All variable expansions.  |

```bash
python3 dorkeye.py --dg=all --mode=aggressive -o results.json
```

-----

### 🔹 `--templates` — Template File Selection

Specifies which template YAML file to use from the `Templates/` directory. Use `=` syntax (no space).

```bash
# Default template
python3 dorkeye.py --dg=sqli --templates=dorks_templates.yaml

# All YAML files in Templates/
python3 dorkeye.py --dg=all --templates=all

# Specific research template
python3 dorkeye.py --dg=backups --templates=dorks_templates_research.yaml
```

-----

### 🔹 `--dg-max` — Max Dork Combinations

Limits the maximum number of dork combinations generated per template. Default: **800**.

```bash
python3 dorkeye.py --dg=all --dg-max=10000 -o big_scan.json
```

-----

## ══════════════════════════════════════════

## POST-SEARCH ANALYSIS PIPELINE

## ══════════════════════════════════════════

The analysis pipeline is powered by `dorkeye_agents.py` and runs autonomous post-search analysis: triage, page fetching, secrets detection, and report generation — no external AI needed.

### 🔹 `--analyze` — Enable Analysis Pipeline

Runs the full analysis pipeline after the search completes. Automatically prompted when output is `.json`.

```bash
# Explicit activation
python3 dorkeye.py -d dorks.txt -o results.json --analyze

# Also works with file mode
python3 dorkeye.py -f Dump/results.json --analyze -o reanalyzed.json
```

**Pipeline stages:**

1. **TriageAgent** — Prioritizes results by risk level
1. **PageFetchAgent** — Downloads page content (if `--analyze-fetch`)
1. **SecretsAgent** — Detects credentials, API keys, tokens, sensitive data
1. **ReportAgent** — Generates the analysis report

-----

### 🔹 `--analyze-fetch` — Enable Page Downloading

Downloads actual page content for HIGH/CRITICAL priority results, enabling deeper secrets detection.

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-fetch
```

-----

### 🔹 `--analyze-fetch-max` — Max Pages to Download

Limits the number of pages downloaded during analysis. Default: **20**.

```bash
python3 dorkeye.py --dg=sqli -o results.json --analyze --analyze-fetch --analyze-fetch-max=5000
```

-----

### 🔹 `--analyze-fmt` — Analysis Report Format

Sets the output format for the analysis report. Default: `html`.

|Format|Extension              |
|------|-----------------------|
|`html`|Interactive HTML report|
|`md`  |Markdown               |
|`json`|Structured JSON        |
|`txt` |Plain text             |

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-fmt=md
```

-----

### 🔹 `--analyze-out` — Analysis Report Path

Custom path for the analysis report. Default: auto-generated next to the `-o` file.

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-out=custom_report.html
```

-----

## ══════════════════════════════════════════

## ADAPTIVE RECURSIVE CRAWL

## ══════════════════════════════════════════

The crawler (`DorkCrawlerAgent`) performs automatic multi-round refinement: it analyzes initial results, extracts patterns (domains, paths, technologies, extensions), generates new refined dorks, and searches again — iterating until diminishing returns.

### 🔹 `--crawl` — Enable Recursive Crawl

Activates the adaptive crawl after the initial search.

```bash
python3 dorkeye.py -d "site:example.com inurl:admin" --crawl -o crawl.json
```

New results from the crawl are merged with the initial results and saved together.

-----

### 🔹 `--crawl-rounds` — Maximum Crawl Rounds

Number of refinement rounds. Default depends on the agents module.

```bash
python3 dorkeye.py --dg=sqli --crawl --crawl-rounds=5 -o crawl.json
```

-----

### 🔹 `--crawl-max` — Maximum Total Crawl Results

Cap on total results collected across all crawl rounds.

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-max=200 -o crawl.json
```

-----

### 🔹 `--crawl-per-dork` — Results per Crawl Dork

Maximum results fetched per individual generated dork during crawl rounds.

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-per-dork=30 -o crawl.json
```

-----

### 🔹 `--crawl-stealth` — Stealth Crawl

Applies longer delays during crawl rounds.

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-stealth -o crawl.json
```

-----

### 🔹 `--crawl-report` — Generate Crawl Report

Generates an HTML report at the end of the crawl.

```bash
python3 dorkeye.py --dg=sqli --crawl --crawl-rounds=5 --crawl-report -o crawl.json
```

-----

### 🔹 `--crawl-out` — Crawl Report Path

Custom path for the crawl report.

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-stealth --crawl-out=crawl_report.html -o crawl.json
```

-----

## ══════════════════════════════════════════

## INTERRUPT CONTROL

## ══════════════════════════════════════════

DorkEye supports graceful interrupt handling throughout all operations:

|Action                         |Effect                                             |
|-------------------------------|---------------------------------------------------|
|**Single Ctrl+C**              |Skips the current dork / task and moves to the next|
|**Double Ctrl+C** (within 1.5s)|Exits immediately, saves partial results           |

This works during: searches, file analysis, SQLi testing, delays, analysis, and crawl.

-----

## ══════════════════════════════════════════

## TERMUX / ANDROID

## ══════════════════════════════════════════

DorkEye auto-detects Termux on Android and activates battery-saver mode:

- Reduced baseline samples for SQLi latency
- Lower probe and boolean sample counts
- Shorter connect timeouts
- Fewer time-based confirmation rounds

No flags needed — detection is automatic.

-----

## ══════════════════════════════════════════

## RECOMMENDED COMBINATIONS

## ══════════════════════════════════════════

### Professional Stealth + SQLi + Analysis

```bash
python3 dorkeye.py -d dorks.txt --stealth --sqli -c 150 -o pro_scan.json --analyze --analyze-fetch
```

### Fast Recon (No Analysis)

```bash
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o recon.txt
```

### Document Harvesting

```bash
python3 dorkeye.py -d "site:.gov" --whitelist .pdf .docx .xlsx -o docs.html
```

### Full Pipeline: Generate + Search + SQLi + Analyze + Crawl

```bash
python3 dorkeye.py \
  --dg=sqli \
  --mode=aggressive \
  --sqli \
  --stealth \
  -c 80 \
  -o full_report.json \
  --analyze \
  --analyze-fetch \
  --crawl \
  --crawl-rounds=4 \
  --crawl-report
```

### Re-test Saved Results

```bash
python3 dorkeye.py -f Dump/old_results.json --sqli --analyze --crawl -o retested.json
```

### Direct URL SQLi Test

```bash
python3 dorkeye.py -u "https://target.com/item.php?id=42" --sqli --stealth -o direct_test.json
```

### Standalone Analysis on Saved File

```bash
python3 dorkeye_analyze.py Dump/results.json --fetch --fmt=html
```

-----

## ══════════════════════════════════════════

## COMPLETE FLAG REFERENCE

## ══════════════════════════════════════════

|Flag                 |Type  |Default|Description                                      |
|---------------------|------|-------|-------------------------------------------------|
|`--wizard`           |flag  |—      |Launch interactive wizard                        |
|`-d` / `--dork`      |string|—      |Single dork string or `.txt` file                |
|`-u` / `--url`       |string|—      |Direct URL for SQLi test                         |
|`-f` / `--file`      |string|—      |Load results from saved `.json` / `.txt`         |
|`-o` / `--output`    |string|auto   |Output filename (saved in `Dump/`)               |
|`-c` / `--count`     |int   |50     |Results per dork                                 |
|`--config`           |string|—      |Custom YAML/JSON config file                     |
|`--create-config`    |flag  |—      |Generate sample `dorkeye_config.yaml`            |
|`--sqli`             |flag  |off    |Enable SQL injection detection                   |
|`--stealth`          |flag  |off    |Enable stealth mode                              |
|`--no-fingerprint`   |flag  |off    |Disable HTTP fingerprinting                      |
|`--no-analyze`       |flag  |off    |Disable file analysis (HEAD requests)            |
|`--blacklist`        |list  |—      |Extensions to exclude (e.g., `.jpg .png`)        |
|`--whitelist`        |list  |—      |Extensions to include exclusively                |
|`--dg`               |string|—      |Activate dork generator (`all` or category)      |
|`--dg-max`           |int   |800    |Max dork combinations per template               |
|`--mode`             |string|soft   |Generation mode: `soft` / `medium` / `aggressive`|
|`--templates`        |string|default|Template file in `Templates/` (use `=` syntax)   |
|`--analyze`          |flag  |off    |Run post-search analysis pipeline                |
|`--analyze-fetch`    |flag  |off    |Download pages during analysis                   |
|`--analyze-fetch-max`|int   |20     |Max pages to download                            |
|`--analyze-fmt`      |string|html   |Report format: `html` / `md` / `json` / `txt`    |
|`--analyze-out`      |string|auto   |Custom analysis report path                      |
|`--crawl`            |flag  |off    |Enable adaptive recursive crawl                  |
|`--crawl-rounds`     |int   |—      |Max crawl refinement rounds                      |
|`--crawl-max`        |int   |—      |Max total crawl results                          |
|`--crawl-per-dork`   |int   |—      |Results per generated crawl dork                 |
|`--crawl-stealth`    |flag  |off    |Stealth delays during crawl                      |
|`--crawl-report`     |flag  |off    |Generate crawl HTML report                       |
|`--crawl-out`        |string|auto   |Custom crawl report path                         |

-----

## ⚠️ Legal Reminder

Use **only** on:

- Authorized targets
- Public data
- Educational / research environments

Attacking targets without prior mutual consent is illegal.
It is the end user’s responsibility to obey all applicable local, state and federal laws.

🐲 Power without control is noise. Stay precise. Stay ethical.
