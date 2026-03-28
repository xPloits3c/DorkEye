# DorkEye — Complete Usage Reference

Every flag, every mode, every combination — explained.

```
 ___
__H__       xploits3c.github.io/DorkEye
 [d]
 [e]
 [;]    DorkEye v4.9 | Project
 |_|
  V
```

---

## 🗂️ Navigation

[![Core Flags](https://img.shields.io/badge/Core_Flags-0077BB?style=flat-square)](#-core-flags)
[![Detection & Stealth](https://img.shields.io/badge/Detection_%26_Stealth-0077BB?style=flat-square)](#-detection--stealth)
[![XSS Detection](https://img.shields.io/badge/XSS_Detection-0077BB?style=flat-square)](#-xss-detection)
[![SQLi Detection](https://img.shields.io/badge/SQLi_Detection-0077BB?style=flat-square)](#-sqli---sql-injection-detection)
[![Dork Generator](https://img.shields.io/badge/Dork_Generator-0077BB?style=flat-square)](#-dork-generator)
[![Analysis Pipeline](https://img.shields.io/badge/Analysis_Pipeline-0077BB?style=flat-square)](#-post-search-analysis-pipeline)
[![Recursive Crawl](https://img.shields.io/badge/Recursive_Crawl-0077BB?style=flat-square)](#-adaptive-recursive-crawl)
[![Interrupt Control](https://img.shields.io/badge/Interrupt_Control-0077BB?style=flat-square)](#-interrupt-control)
[![Termux](https://img.shields.io/badge/Termux_%2F_Android-0077BB?style=flat-square)](#-termux--android)
[![Combinations](https://img.shields.io/badge/Recommended_Combos-0077BB?style=flat-square)](#-recommended-combinations)
[![Flag Reference](https://img.shields.io/badge/Complete_Flag_Reference-0077BB?style=flat-square)](#-complete-flag-reference)

---

## 📌 Basic Syntax

```bash
python3 dorkeye.py [OPTIONS]
```

DorkEye operates in **five distinct modes**, each triggered by different flags:

| Mode | Trigger | Description |
|---|---|---|
| **Interactive Wizard** | `--wizard` | Guided menu-driven session |
| **Dork Search** | `-d` | Search with manual or file-based dorks |
| **Dork Generator** | `--dg` | Auto-generate dorks from YAML templates |
| **Direct URL Test** | `-u` | Test a single URL for SQLi / XSS |
| **File Reload** | `-f` | Re-process saved results (SQLi / XSS / analyze / crawl) |

Minimal required: at least one of `-d`, `--dg`, `-u`, or `-f`. Output `-o` is auto-generated if omitted.

---

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
- SQLi / XSS / stealth / fingerprinting toggles
- XSS type (`all` / `reflected` / `stored` / `dom`)
- Output filename and format
- Post-search analysis (if output is `.json`)
- Recursive crawl options

---

### 🔹 `-d` / `--dork` — Dork Input

Defines the search query. Accepts a single dork string or a `.txt` file (one dork per line, `#` lines ignored).

```bash
# Single dork
python3 dorkeye.py -d "inurl:admin filetype:php" -o output.html

# File with multiple dorks
python3 dorkeye.py -d dorks.txt -c 100 -o output.json
```

💡 For automation and large-scale scans, always use files.

---

### 🔹 `-u` / `--url` — Direct URL Test

Tests a single URL directly for SQL injection and/or XSS. No search is performed.
Automatically enables `--sqli` if neither `--sqli` nor `--xss` is specified.

```bash
# SQLi test only
python3 dorkeye.py -u "https://example.com/page.php?id=1" --sqli

# XSS test only
python3 dorkeye.py -u "https://target.com/search?q=test" --xss

# Both SQLi and XSS, with stealth and output
python3 dorkeye.py -u "https://example.com/page.php?id=1" --sqli --xss --stealth -o result.json
```

**Output includes:**

- Vulnerability status (SAFE / VULNERABLE)
- Confidence level (NONE → LOW → MEDIUM → HIGH → CRITICAL)
- Detection method, parameter, and evidence
- XSS type(s) found (reflected / stored / dom / header)
- WAF detection

---

### 🔹 `-f` / `--file` — Load Saved Results

Loads results from a previously saved `.json` or `.txt` file and re-processes them.
Combine with `--sqli`, `--xss`, `--analyze`, or `--crawl` to run additional analysis on existing data.

```bash
# Re-run SQLi on saved results
python3 dorkeye.py -f Dump/results.json --sqli -o retest.json

# Re-run XSS on saved results
python3 dorkeye.py -f Dump/results.json --xss --xss-type=reflected -o xss_retest.json

# Run analysis pipeline on saved results
python3 dorkeye.py -f Dump/results.json --analyze -o reanalyzed.json

# Full re-processing: SQLi + XSS + analysis + crawl
python3 dorkeye.py -f Dump/results.json --sqli --xss --analyze --crawl -o full_retest.json
```

**Supported formats:**

- `.json` — DorkEye JSON output (supports both `{"results": [...]}` and raw `[...]`)
- `.txt` — One URL per line (lines starting with `http`)

The file is searched in the current directory first, then in `Dump/`.

---

### 🔹 `-o` / `--output` — Output Filename

Specifies the output filename. The file is saved inside the `Dump/` folder.
Format is inferred from the extension.

```bash
python3 dorkeye.py -d dorks.txt -o results.json
python3 dorkeye.py -d dorks.txt -o report.html
python3 dorkeye.py -d dorks.txt -o export.csv
python3 dorkeye.py -d dorks.txt -o links.txt
```

| Extension | Format | Features |
|---|---|---|
| `.json` | Structured JSON | Full metadata, statistics, SQLi + XSS details. Enables `--analyze` prompt. |
| `.html` | Interactive report | Dark matrix theme, filters, search, export panels, SQLi + XSS badges, WAF labels, file browser, XSS export section |
| `.csv` | Spreadsheet-ready | All columns including SQLi status, XSS status, types, WAF, confidence |
| `.txt` | Plain text | Numbered list with per-result details including SQLi and XSS status |

If `-o` is omitted, DorkEye auto-generates `report_YYYYMMDD_HHMMSS.html`.

💡 Using `.json` output automatically prompts for post-search analysis.

---

### 🔹 `-c` / `--count` — Results per Dork

Limits the maximum number of results fetched per dork query. Default: **50**.

```bash
python3 dorkeye.py -d dorks.txt -c 200 -o output.html
```

**Notes:**

- Higher values = slower scans and higher risk of rate-limiting
- Use `--stealth` when `-c > 100`
- DorkEye automatically applies extended delays every 100 results (configurable)

---

### 🔹 `--config` — Custom Configuration File

Loads a YAML or JSON configuration file that overrides the defaults.

```bash
python3 dorkeye.py -d dorks.txt --config custom_config.yaml -o scan.json
```

Configurable settings include: extensions map, blacklist/whitelist, timeouts, retry count, stealth mode, fingerprinting, SQLi detection, XSS detection, XSS type, and the extended delay threshold.

See `--create-config` to generate a starter template.

---

### 🔹 `--create-config` — Generate Default Config

Writes a sample `dorkeye_config.yaml` to disk.

```bash
python3 dorkeye.py --create-config
```

---

## ══════════════════════════════════════════
## DETECTION & STEALTH
## ══════════════════════════════════════════

### 🔹 `--stealth` — Stealth Mode

Reduces detection and rate-limiting risks by increasing delays and randomization.

```bash
python3 dorkeye.py -d dorks.txt --stealth -o stealth_scan.html
```

**What it activates:**

- Extended randomized delays between requests (1.4×–1.8× multiplier)
- Longer inter-dork waits
- Extended rate-limit pauses (120–150s vs. 85–110s)
- Additional delays during SQLi and XSS testing

✅ Strongly recommended for: sensitive targets, long scans, SQLi/XSS testing, high `-c` values.

---

### 🔹 `--no-fingerprint` — Disable HTTP Fingerprinting

Disables the browser fingerprint rotation system. Falls back to basic User-Agent rotation.

```bash
python3 dorkeye.py -d dorks.txt --no-fingerprint -o output.html
```

By default, DorkEye loads `http_fingerprints.json` and rotates full browser profiles (User-Agent, Accept, Accept-Language, Accept-Encoding, Sec-Fetch-*, Cache-Control) to mimic real browser traffic.

---

### 🔹 `--no-analyze` — Disable File Analysis

Skips HEAD-request file analysis for faster scans. No size, content-type, or accessibility checks.

```bash
python3 dorkeye.py -d dorks.txt --no-analyze -o fast_scan.txt
```

| Mode | Speed | Metadata |
|---|---|---|
| Default | Medium | File size, content-type, HTTP status |
| `--no-analyze` | Fast | None |

---

### 🔹 `--blacklist` — Extension Blacklist

Excludes specific file types from results.

```bash
python3 dorkeye.py -d "site:target.com" --blacklist .jpg .png .gif -o no_images.html
```

---

### 🔹 `--whitelist` — Extension Whitelist

Only includes specific file types. All other extensions are ignored.

```bash
python3 dorkeye.py -d "site:target.com" --whitelist .pdf .xls .docx -o documents.html
```

---

## ══════════════════════════════════════════
## XSS DETECTION
## ══════════════════════════════════════════

### 🔹 `--xss` — XSS Detection

Enables the multi-method XSS detection engine on all discovered URLs. Works alongside `--sqli` or standalone.

```bash
# XSS on a dork search
python3 dorkeye.py -d "inurl:search?q=" --xss -o xss_scan.html

# XSS + SQLi combined
python3 dorkeye.py -d dorks.txt --sqli --xss -o full_scan.json

# XSS on a direct URL
python3 dorkeye.py -u "https://target.com/search?q=test" --xss

# XSS on saved results
python3 dorkeye.py -f Dump/results.json --xss -o xss_retest.json
```

---

### 🔹 `--xss-type` — XSS Detection Scope

Limits XSS testing to a specific method. Default: `all`.

```bash
python3 dorkeye.py -d dorks.txt --xss --xss-type=reflected -o reflected.json
python3 dorkeye.py -d dorks.txt --xss --xss-type=stored    -o stored.json
python3 dorkeye.py -d dorks.txt --xss --xss-type=dom       -o dom.json
python3 dorkeye.py -d dorks.txt --xss --xss-type=all       -o full_xss.json
```

---

### 🔹 XSS Detection Pipeline (4 methods)

All four methods run in sequence when `--xss-type=all`. Each is fully independent and can be selected individually.

#### Method 1 — Reflected

Injects payloads into GET parameters and checks the response for unescaped reflection.

**51 total payloads** across two tiers:

| Tier | Count | Examples |
|---|---|---|
| Standard | 29 | `<script>`, `<svg/onload>`, `<img onerror>`, autofocus events, MathML, `formaction`, attribute break-out |
| WAF bypass | 16 | Case mixing, URL double-encoding, comment insertion (`<scr<!---->ipt>`), tab/newline in tags, data URI iframe, backtick attributes |
| OOB | 6 | Blind callback via `--oob-url` (interactsh endpoint) |

**False-positive reduction:**

- Skips responses with non-HTML `Content-Type` (JSON, XML, plain text)
- Verifies the full tag structure survives, not just the marker word
- Rejects reflection inside `<!-- HTML comments -->`
- Rejects reflection where `\u003C` escaping is detected in a `<script>` block
- Uses 60-char context window (vs 20 in previous versions)

**Confidence:**
- `HIGH` when unescaped and no CSP
- `MEDIUM` when unescaped but `Content-Security-Policy` (without `unsafe-inline`) is present

#### Method 2 — Stored

POSTs payloads into each parameter individually (not all at once), then refetches the page via GET and checks for persistence.

Two-stage detection:

| Stage | Trigger | Confidence |
|---|---|---|
| Stage 1 | Payload echoed in immediate POST response | MEDIUM |
| Stage 2 | Payload persists in subsequent GET request | HIGH |

Content-type gate applied on both POST response and GET refetch.

#### Method 3 — DOM

Fetches the page, extracts inline `<script>` blocks and up to 5 external `.js` files, then performs static source-to-sink analysis.

**Sources detected:** `location.hash`, `location.search`, `location.href`, `document.URL`, `document.documentURI`, `document.referrer`, `window.name`, `history.state`

**Sinks detected:** `document.write`, `innerHTML =`, `outerHTML =`, `eval()`, `setTimeout("…")`, `location.href =`, `insertAdjacentHTML`, `.setAttribute("src"/"href"/"on*")`, `document.createElement("script")`

**False-positive reduction:**
- Source and sink must co-occur in the **same 40-line sliding block** — global page-level matching is not used
- Lines matching analytics, static string writes, and code comments are excluded before analysis
- Confidence is `LOW` for a single source/sink pair, `MEDIUM` for 2+ distinct pairs in the same block

#### Method 4 — Header

Injects the XSS marker into HTTP request headers that some servers reflect back in error pages, debug output, or log-replay interfaces.

**Tested headers:** `X-Forwarded-For` · `Referer` · `User-Agent` · `X-Forwarded-Host` · `X-Original-URL`

Confidence: `HIGH` on unescaped reflection. Content-type gate applied per response.

---

### 🔹 XSS Confidence Scoring

Individual method confidence is aggregated into an overall score:

| Score | Overall Confidence |
|---|---|
| ≥ 5 | CRITICAL |
| ≥ 3 | HIGH |
| ≥ 2 | MEDIUM |
| < 2 | LOW |

---

### 🔹 XSS Terminal Output

```
[!] Potential XSS found (high) [reflected]: https://target.com/search?q=test
    ↳ type: reflected [payload: "><script>alert("DEXSS7x")</script>]
      evidence: Unescaped reflection in param [q]: ...
```

---

### 🔹 XSS Output Formats

XSS results are persisted across all output formats:

| Format | XSS data included |
|---|---|
| `.json` | `xss_test` dict per result; metadata: `xss_detection_enabled`, `xss_type`, `xss_vulnerabilities_found` |
| `.html` | XSS column in results table; XSS alert banner; XSS stats counter; XSS filter sub-menu (VULN / SAFE); XSS export section in Links panel (all tested / vuln / safe) |
| `.csv` | `xss_vulnerable`, `xss_types`, `xss_confidence` columns |
| `.txt` | `XSS: VULNERABLE (high) [reflected, stored]` line per result |

---

## ══════════════════════════════════════════
## SQLi — SQL INJECTION DETECTION
## ══════════════════════════════════════════

### 🔹 `--sqli` — SQL Injection Detection

Enables the multi-method SQLi detection engine on all discovered URLs.

```bash
python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o sqli_scan.html
```

---

### 🔹 SQLi Detection Pipeline (7 methods)

| Method | Description | Confidence |
|---|---|---|
| **Error-based** | Injects payloads that trigger DB-specific error signatures (MySQL, PostgreSQL, MSSQL, SQLite, Oracle) | HIGH |
| **UNION-based** | Probes column count with `UNION SELECT NULL,…` and detects mismatch errors or response anomalies | MEDIUM–HIGH |
| **Boolean blind** | Compares response sizes for true/false condition pairs with statistical noise filtering | MEDIUM |
| **Time-based blind** | Measures `SLEEP()`-induced delays above baseline + margin | MEDIUM |
| **Stacked queries** | Injects after `;` — targets PDO multi-statement, stored procedures, APIs executing multiple queries | HIGH |
| **Heavy query time** | CPU-intensive delays without `SLEEP`/`WAITFOR` — bypasses WAFs that block those keywords | MEDIUM |
| **Header injection** | Injects into `X-Forwarded-For`, `X-Real-IP`, `User-Agent`, `Referer`, `CF-Connecting-IP` | MEDIUM–HIGH |

**Payload counts:**

| Method | Payloads |
|---|---|
| Error-based | 8 (+ updatexml, BENCHMARK error, CONVERT MSSQL, cast PG, XMLType Oracle) |
| UNION-based | 4 × 5 column depths |
| Boolean blind | 4 true/false pairs |
| Time-based | 6 (+ WAITFOR MSSQL, pg_sleep PG, dbms_pipe Oracle, OR SLEEP bypass) |
| Stacked queries | 11 |
| Heavy query | 12 |
| Header injection | 5 headers × error + boolean |

---

### 🔹 SQLi Additional Features

- Parameter priority sorting: high-risk (`id`, `page`, `cat`) → medium (`search`, `q`) → low
- Adaptive noise probing before each parameter test
- WAF detection (12 providers: Cloudflare, ModSecurity, Wordfence, Sucuri, Imperva, Akamai, F5 BigIP, Barracuda, FortiWeb, AWS WAF, DenyAll, Reblaze)
- Circuit breaker: auto-skips unreachable hosts
- Confidence scoring: NONE → LOW → MEDIUM → HIGH → CRITICAL (threshold `best >= 6`)
- POST and JSON injection available via `SQLiDetector.test_post_sqli()` and `test_json_sqli()`

---

### 🔹 SQLi Terminal Output

```
[!] Potential SQLi found (critical): https://target.com/product.php?id=7
    ↳ method: error_based [param: id]  evidence: MYSQL error signature: extractvalue(0,...
    ↳ method: time_based_blind         evidence: SLEEP(3) elapsed=3.4s > threshold=3.2s
```

---

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

**Architecture note:** `--dg` controls *dork generation*. `--sqli` and `--xss` control *vulnerability detection*. They are fully independent.

```bash
# Generate SQLi dorks AND test them for SQLi AND XSS
python3 dorkeye.py --dg=sqli --sqli --xss --mode=aggressive -o report.html
```

---

### 🔹 `--mode` — Generation Mode

Controls dork generation intensity. Default: `soft`.

| Mode | Behavior |
|---|---|
| `soft` | Safe, minimal footprint. Fewer combinations. |
| `medium` | Balanced coverage. |
| `aggressive` | Maximum coverage. All variable expansions. |

```bash
python3 dorkeye.py --dg=all --mode=aggressive -o results.json
```

---

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

---

### 🔹 `--dg-max` — Max Dork Combinations

Limits the maximum number of dork combinations generated per template. Default: **800**.

```bash
python3 dorkeye.py --dg=all --dg-max=10000 -o big_scan.json
```

---

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

1. **TriageAgent** — Prioritizes results by risk level (SQLi/XSS confirmed scores bonus points)
2. **PageFetchAgent** — Downloads page content (if `--analyze-fetch`)
3. **SecretsAgent** — Detects credentials, API keys, tokens, sensitive data
4. **ReportAgent** — Generates the analysis report

---

### 🔹 `--analyze-fetch` — Enable Page Downloading

Downloads actual page content for HIGH/CRITICAL priority results, enabling deeper secrets detection.

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-fetch
```

---

### 🔹 `--analyze-fetch-max` — Max Pages to Download

Limits the number of pages downloaded during analysis. Default: **20**.

```bash
python3 dorkeye.py --dg=sqli -o results.json --analyze --analyze-fetch --analyze-fetch-max=5000
```

---

### 🔹 `--analyze-fmt` — Analysis Report Format

Sets the output format for the analysis report. Default: `html`.

| Format | Extension |
|---|---|
| `html` | Interactive HTML report |
| `md` | Markdown |
| `json` | Structured JSON |
| `txt` | Plain text |

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-fmt=md
```

---

### 🔹 `--analyze-out` — Analysis Report Path

Custom path for the analysis report. Default: auto-generated next to the `-o` file.

```bash
python3 dorkeye.py -d dorks.txt -o results.json --analyze --analyze-out=custom_report.html
```

---

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

---

### 🔹 `--crawl-rounds` — Maximum Crawl Rounds

```bash
python3 dorkeye.py --dg=sqli --crawl --crawl-rounds=5 -o crawl.json
```

---

### 🔹 `--crawl-max` — Maximum Total Crawl Results

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-max=200 -o crawl.json
```

---

### 🔹 `--crawl-per-dork` — Results per Crawl Dork

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-per-dork=30 -o crawl.json
```

---

### 🔹 `--crawl-stealth` — Stealth Crawl

Applies longer delays during crawl rounds.

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-stealth -o crawl.json
```

---

### 🔹 `--crawl-report` — Generate Crawl Report

```bash
python3 dorkeye.py --dg=sqli --crawl --crawl-rounds=5 --crawl-report -o crawl.json
```

---

### 🔹 `--crawl-out` — Crawl Report Path

```bash
python3 dorkeye.py -d dorks.txt --crawl --crawl-stealth --crawl-out=crawl_report.html -o crawl.json
```

---

## ══════════════════════════════════════════
## INTERRUPT CONTROL
## ══════════════════════════════════════════

DorkEye supports graceful interrupt handling throughout all operations:

| Action | Effect |
|---|---|
| **Single Ctrl+C** | Skips the current dork / task and moves to the next |
| **Double Ctrl+C** (within 1.5s) | Exits immediately, saves partial results |

This works during: searches, file analysis, SQLi testing, XSS testing, delays, analysis, and crawl. The interrupt signal propagates automatically to `sqli.py` and `xss.py` sub-modules.

---

## ══════════════════════════════════════════
## TERMUX / ANDROID
## ══════════════════════════════════════════

DorkEye auto-detects Termux on Android and activates battery-saver mode:

- Reduced baseline samples for SQLi latency
- Lower probe and boolean sample counts
- Shorter connect timeouts
- Fewer time-based confirmation rounds

No flags needed — detection is automatic.

---

## ══════════════════════════════════════════
## RECOMMENDED COMBINATIONS
## ══════════════════════════════════════════

### Professional Stealth — SQLi + XSS + Analysis

```bash
python3 dorkeye.py -d dorks.txt --stealth --sqli --xss -c 150 -o pro_scan.json --analyze --analyze-fetch
```

### XSS Only — Reflected Type, Stealth

```bash
python3 dorkeye.py -d "inurl:search?q=" --xss --xss-type=reflected --stealth -o xss_reflected.html
```

### Full Vulnerability Scan — Generator + SQLi + XSS

```bash
python3 dorkeye.py --dg=all --mode=aggressive --sqli --xss -c 80 -o full_scan.json
```

### Fast Recon (No Analysis)

```bash
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o recon.txt
```

### Document Harvesting

```bash
python3 dorkeye.py -d "site:.gov" --whitelist .pdf .docx .xlsx -o docs.html
```

### Full Pipeline — Generate + Search + SQLi + XSS + Analyze + Crawl

```bash
python3 dorkeye.py \
  --dg=sqli \
  --mode=aggressive \
  --sqli \
  --xss \
  --stealth \
  -c 80 \
  -o full_report.json \
  --analyze \
  --analyze-fetch \
  --crawl \
  --crawl-rounds=4 \
  --crawl-report
```

### Re-test Saved Results — SQLi + XSS

```bash
python3 dorkeye.py -f Dump/old_results.json --sqli --xss --analyze --crawl -o retested.json
```

### Direct URL — SQLi + XSS Test

```bash
python3 dorkeye.py -u "https://target.com/item.php?id=42" --sqli --xss --stealth -o direct_test.json
```

### Standalone Analysis on Saved File

```bash
python3 dorkeye_analyze.py Dump/results.json --fetch --fmt=html
```

---

## ══════════════════════════════════════════
## COMPLETE FLAG REFERENCE
## ══════════════════════════════════════════

| Flag | Type | Default | Description |
|---|---|---|---|
| `--wizard` | flag | — | Launch interactive wizard |
| `-d` / `--dork` | string | — | Single dork string or `.txt` file |
| `-u` / `--url` | string | — | Direct URL for SQLi / XSS test |
| `-f` / `--file` | string | — | Load results from saved `.json` / `.txt` |
| `-o` / `--output` | string | auto | Output filename (saved in `Dump/`) |
| `-c` / `--count` | int | 50 | Results per dork |
| `--config` | string | — | Custom YAML/JSON config file |
| `--create-config` | flag | — | Generate sample `dorkeye_config.yaml` |
| `--sqli` | flag | off | Enable SQL injection detection |
| `--xss` | flag | off | Enable XSS detection (reflected, stored, DOM, header) |
| `--xss-type` | string | `all` | XSS scope: `reflected` / `stored` / `dom` / `header` / `all` |
| `--stealth` | flag | off | Enable stealth mode |
| `--no-fingerprint` | flag | off | Disable HTTP fingerprinting |
| `--no-analyze` | flag | off | Disable file analysis (HEAD requests) |
| `--blacklist` | list | — | Extensions to exclude (e.g., `.jpg .png`) |
| `--whitelist` | list | — | Extensions to include exclusively |
| `--dg` | string | — | Activate dork generator (`all` or category) |
| `--dg-max` | int | 800 | Max dork combinations per template |
| `--mode` | string | soft | Generation mode: `soft` / `medium` / `aggressive` |
| `--templates` | string | default | Template file in `Templates/` (use `=` syntax) |
| `--analyze` | flag | off | Run post-search analysis pipeline |
| `--analyze-fetch` | flag | off | Download pages during analysis |
| `--analyze-fetch-max` | int | 20 | Max pages to download |
| `--analyze-fmt` | string | html | Report format: `html` / `md` / `json` / `txt` |
| `--analyze-out` | string | auto | Custom analysis report path |
| `--crawl` | flag | off | Enable adaptive recursive crawl |
| `--crawl-rounds` | int | — | Max crawl refinement rounds |
| `--crawl-max` | int | — | Max total crawl results |
| `--crawl-per-dork` | int | — | Results per generated crawl dork |
| `--crawl-stealth` | flag | off | Stealth delays during crawl |
| `--crawl-report` | flag | off | Generate crawl HTML report |
| `--crawl-out` | string | auto | Custom crawl report path |

---

## ⚠️ Legal Reminder

Use **only** on:

- Authorized targets
- Public data
- Educational / research environments

Attacking targets without prior mutual consent is illegal.
It is the end user's responsibility to obey all applicable local, state and federal laws.

Power without control is noise. Stay precise. Stay ethical.
