# CLI Reference — DorkEye Project

> All flags, all accepted values, all combinations.
> Single-page cheat sheet — keep it open while you hunt.

-----

## Input Sources — one required

|Flag               |Type|Description                                                                       |
|-------------------|----|----------------------------------------------------------------------------------|
|`--wizard`         |bool|Launch the interactive guided session (menus for everything)                      |
|`-d DORK`, `--dork`|str |Single dork string **or** path to a `.txt` file (one dork per line, `#` = comment)|
|`-u URL`, `--url`  |str |Single URL — direct vulnerability test (SQLi + XSS), no search performed          |
|`-f FILE`, `--file`|str |Load saved DorkEye results (`.json` or `.txt`) for re-processing                  |
|`--dg[=CATEGORY]`  |str |Activate Dork Generator; value = category name or `all` (default if omitted)      |
|`--create-config`  |bool|Write sample `dorkeye_config.yaml` to disk and exit                               |
|`--ui`             |bool|Launch the Web Console (Flask dashboard) — see **Web Console** section            |

-----

## Output

|Flag                 |Default                      |Description                                                |
|---------------------|-----------------------------|-----------------------------------------------------------|
|`-o FILE`, `--output`|`report_YYYYMMDD_HHMMSS.html`|Output file — extension determines format (see table below)|
|`-c N`, `--count`    |`50`                         |Max results per dork from DuckDuckGo                       |

All output files are saved inside the `Dump/` folder (auto-created).

-----

## Configuration

|Flag             |Description                                                    |
|-----------------|---------------------------------------------------------------|
|`--config FILE`  |Load a custom YAML or JSON configuration (merged with defaults)|
|`--create-config`|Generate sample `dorkeye_config.yaml` and exit                 |

-----

## Scan Behaviour

|Flag              |Default|Description                                                        |
|------------------|-------|-------------------------------------------------------------------|
|`--sqli`          |off    |Enable multi-method SQL injection detection on every result        |
|`--xss`           |off    |Enable multi-method XSS detection on every result                  |
|`--stealth`       |off    |Stealth mode — 1.4×–1.8× longer delays, extended rate-limit pauses |
|`--no-analyze`    |off    |Skip HEAD-request file analysis (no size / content-type / status)  |
|`--no-fingerprint`|off    |Disable HTTP fingerprint rotation (falls back to basic UA rotation)|
|`--blacklist EXT…`|none   |Space-separated extensions to exclude (e.g. `.jpg .png .gif`)      |
|`--whitelist EXT…`|none   |Space-separated extensions — only these are kept                   |

-----

## XSS Detection

Requires `Tools/xss.py`. Activated via `--xss`. All methods run by default (`--xss-type all`).

|Flag             |Default|Description                                                      |
|-----------------|-------|-----------------------------------------------------------------|
|`--xss`          |off    |Enable XSS detection pipeline (reflected + stored + dom + header)|
|`--xss-type TYPE`|`all`  |Detection method(s) to run — see **XSS Types** table below       |

### XSS Types (`--xss-type`)

|Value      |Method                                                                                             |
|-----------|---------------------------------------------------------------------------------------------------|
|`reflected`|Inject payloads into GET params; check for unescaped reflection in response                        |
|`stored`   |POST payload per individual param, refetch via GET, check if marker persists                       |
|`dom`      |Static analysis of JS source-to-sink patterns (inline scripts + up to 5 external scripts)          |
|`header`   |Inject marker into `X-Forwarded-For`, `Referer`, `User-Agent`, `X-Forwarded-Host`, `X-Original-URL`|
|`all`      |Run all four methods in sequence (default)                                                         |

### XSS Confidence Levels

|Level     |Meaning                                                            |
|----------|-------------------------------------------------------------------|
|`NONE`    |No XSS detected                                                    |
|`LOW`     |DOM static analysis: 3–5 co-occurring source/sink pairs            |
|`MEDIUM`  |DOM analysis: 6+ pairs; or reflected/stored with CSP header present|
|`HIGH`    |Unescaped reflection confirmed (reflected/stored/header), no CSP   |
|`CRITICAL`|Multiple methods confirmed — combined confidence score ≥ 5         |


> **Note** — DOM analysis never reaches HIGH/CRITICAL on its own; modern SPAs (React/Vue/Angular)
> produce source/sink pairs from framework internals. Results below the 3-pair threshold are
> recorded as informational only.

-----

## SQL Injection Detection

|Flag    |Default|Description                                                |
|--------|-------|-----------------------------------------------------------|
|`--sqli`|off    |Enable multi-method SQL injection detection on every result|

### SQLi Confidence Levels

|Level     |Meaning                                                 |
|----------|--------------------------------------------------------|
|`NONE`    |No injection detected                                   |
|`LOW`     |Weak signal (e.g. UNION col-mismatch only)              |
|`MEDIUM`  |Boolean blind differential or time-based confirmed      |
|`HIGH`    |DB error signature matched or strong UNION evidence     |
|`CRITICAL`|Multiple methods confirmed across parameters (score ≥ 5)|

### WAF Detection

Detected automatically during SQLi and XSS testing. Supported signatures:

Cloudflare · ModSecurity · Wordfence · Sucuri · Imperva · Akamai · F5 BigIP · Barracuda ·
FortiWeb · AWS WAF · DenyAll · Reblaze · generic (403/406/419/429 with short body)

-----

## Dork Generator

|Flag              |Default               |Description                                                           |
|------------------|----------------------|----------------------------------------------------------------------|
|`--dg[=CATEGORY]` |`all`                 |Category to generate (`all` = every category in template)             |
|`--dg-max N`      |`800`                 |Max dork combinations per template file                               |
|`--mode MODE`     |`soft`                |Generation intensity: `soft` / `medium` / `aggressive`                |
|`--templates=FILE`|`dorks_templates.yaml`|Template file inside `Templates/`; `all` = every `.yaml` in the folder|

⚠ `--templates` requires `=` syntax: `--templates=file.yaml` ✓ — `--templates file.yaml` ✗

-----

## Agents — Integrated Post-Search Analysis

|Flag                   |Default|Description                                               |
|-----------------------|-------|----------------------------------------------------------|
|`--analyze`            |off    |Run the full analysis pipeline (triage → secrets → report)|
|`--analyze-fetch`      |off    |Download page content for HIGH / CRITICAL results         |
|`--analyze-fetch-max N`|`20`   |Max pages to download during analysis                     |
|`--analyze-fmt FORMAT` |`html` |Analysis report format: `html` / `md` / `json` / `txt`    |
|`--analyze-out FILE`   |auto   |Custom path for the analysis report                       |

Requires `dorkeye_agents.py` in `Tools/`. If missing, `--analyze` and `--crawl` are silently disabled.

-----

## Adaptive Recursive Crawl

|Flag                |Default|Description                                               |
|--------------------|-------|----------------------------------------------------------|
|`--crawl`           |off    |Enable multi-round adaptive crawl after the initial search|
|`--crawl-rounds N`  |`4`    |Maximum refinement rounds                                 |
|`--crawl-max N`     |`300`  |Total result cap across all rounds                        |
|`--crawl-per-dork N`|`20`   |DuckDuckGo results per generated dork per round           |
|`--crawl-stealth`   |off    |Longer delays between crawl searches                      |
|`--crawl-report`    |off    |Generate a dedicated crawl HTML report                    |
|`--crawl-out FILE`  |auto   |Custom path for the crawl report                          |

The crawler analyzes initial results (domains, paths, technologies, extensions), generates
refined dorks, searches again, and repeats until diminishing returns.

-----

## DB Port Scanner

Requires `Tools/db_portscan.py`. Activated via `--dbscan` in the main pipeline,
or run standalone as `python Tools/db_portscan.py`.

### Integrated flags (via `dorkeye.py`)

|Flag                  |Default|Description                                                        |
|----------------------|-------|-------------------------------------------------------------------|
|`--dbscan`            |off    |Run DB port scan on all unique hosts extracted from results        |
|`--dbscan-timeout N`  |`2.5`  |TCP connect timeout per port in seconds                            |
|`--dbscan-threads N`  |`60`   |Worker threads per host (max 200)                                  |
|`--dbscan-max-hosts N`|`200`  |Maximum hosts to scan (private/loopback IPs automatically excluded)|

### Standalone flags (`python Tools/db_portscan.py`)

|Flag          |Default     |Description                                           |
|--------------|------------|------------------------------------------------------|
|`results_file`|*(required)*|DorkEye `.json` results file                          |
|`--timeout`   |`2.5`       |TCP connect timeout in seconds                        |
|`--threads`   |`60`        |Worker threads per host                               |
|`--ports N…`  |all DB ports|Space-separated port list to scan                     |
|`--max-hosts` |`200`       |Max hosts to scan                                     |
|`--stealth`   |off         |Add inter-host delay (1.5–3.5 s)                      |
|`--out FILE`  |auto        |Output base path (writes `_dbscan_<ts>.json` + `.txt`)|

### Detected services and ports

|Service      |Port(s)     |Probe method                                       |
|-------------|------------|---------------------------------------------------|
|MySQL        |3306        |TCP banner                                         |
|PostgreSQL   |5432        |TCP banner                                         |
|MongoDB      |27017/18/19 |OP_MSG isMaster handshake                          |
|Redis        |6379        |`PING` → `+PONG` = no-auth                         |
|Elasticsearch|9200 / 9300 |HTTP GET `/` — checks `cluster_name` in response   |
|CouchDB      |5984        |HTTP GET `/` — checks `couchdb` in response        |
|InfluxDB     |8086        |HTTP GET `/ping` — 204 = alive                     |
|Neo4j        |7474        |HTTP GET `/` — checks `neo4j`/`bolt` in response   |
|MSSQL        |1433        |TCP banner                                         |
|Oracle       |1521        |TCP banner                                         |
|Cassandra    |9042        |TCP banner                                         |
|Memcached    |11211       |`stats\r\n` → `STAT` = no-auth                     |
|RethinkDB    |28015 / 5000|TCP banner                                         |
|DB2          |50000       |TCP banner *(non-default, not in default scan set)*|
|Riak HTTP    |8098        |HTTP GET `/`                                       |

### DBScan Severity Levels

|Level     |Meaning                                                  |
|----------|---------------------------------------------------------|
|`CRITICAL`|Port open **and** unauthenticated access confirmed       |
|`HIGH`    |Port open and service confirmed via banner/protocol probe|
|`MEDIUM`  |Port open, service identity unclear                      |
|`INFO`    |Port closed / filtered / timeout                         |

Port hints are automatically extracted from dork strings, URL paths, and page titles to
prioritise relevant ports (e.g. a result containing “phpmyadmin” will scan port 3306 first).

-----

## Web Console

Requires Flask (`pip install flask`). Launches a local Matrix-themed dashboard
that wraps the full `dorkeye.py` pipeline in a browser UI.

### Flags (via `dorkeye.py`)

|Flag      |Default|Description                                                     |
|----------|-------|----------------------------------------------------------------|
|`--ui`    |off    |Start the Web Console and open the browser                      |
|`--port N`|`8080` |Preferred port; auto-increments up to +100 if the port is in use|

### Standalone (`python Tools/dorkeye_web.py`)

|Flag          |Default|Description                             |
|--------------|-------|----------------------------------------|
|`--port N`    |`8080` |Starting port                           |
|`--no-browser`|off    |Start server without opening the browser|

The console auto-detects a free port, binds to `127.0.0.1` only, streams
subprocess output via SSE, and exposes all pipeline options through a
form-based interface (Scan, URL Tester, Dork Gen, Jobs, Results).
The `Dump/` folder is browsable and files can be opened or downloaded directly.

-----

## Accepted Values

### `--mode`

|Value       |Behaviour                                         |Footprint|
|------------|--------------------------------------------------|---------|
|`soft`      |Low-risk dorks only — minimal variable expansion  |Minimal  |
|`medium`    |Soft + medium coverage patterns                   |Moderate |
|`aggressive`|All dork combinations — maximum variable expansion|Maximum  |

### `-o` / `--output` — format by extension

|Extension|Format                       |Notes                                                                                                                                                                   |
|---------|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`.html`  |Interactive dark-theme report|Matrix rain, filter bar, search panel, export panels (TXT/JSON/CSV), file browser, ⓘ detail popup, WAF badges                                                           |
|`.json`  |Structured JSON              |Full metadata + statistics block. **Triggers interactive analysis prompt**                                                                                              |
|`.csv`   |Spreadsheet CSV              |All columns: url, title, snippet, dork, timestamp, extension, category, file_size, content_type, accessible, status_code, sqli_vulnerable, sqli_confidence, waf_detected|
|`.txt`   |Numbered plain text          |Per-result details (title, category, SQLi status, XSS status, WAF)                                                                                                      |

If no extension is provided, `.json` is appended automatically.

### `--analyze-fmt`

|Value |Output                                                         |
|------|---------------------------------------------------------------|
|`html`|Full dark-theme HTML with triage, secrets, credentials sections|
|`md`  |Markdown with tables                                           |
|`json`|Structured JSON (pii, emails, subdomains, cve_dorks keys)      |
|`txt` |Plain text summary                                             |

-----

## Compatibility Rules

### Mutually exclusive inputs

```
--wizard  ←→  -d  ←→  -u  ←→  -f  ←→  --dg  ←→  --create-config  ←→  --ui
```

Only one input source per invocation.

### `-u` constraints

- `--sqli` and `--xss` are auto-enabled even if not specified
- Not compatible with `--analyze`, `--crawl`, `-d`, `-f`, `--dg`
- Execution stops immediately after the vulnerability tests
- Result is saved to `-o` if provided

### `--xss` constraints

- `--xss-type` only takes effect when `--xss` is active
- Compatible with `-d`, `-u`, `-f`, `--dg`
- Requires `Tools/xss.py` — otherwise silently skipped
- WAF pre-detected by the SQLi probe is shared with the XSS engine automatically

### `--dbscan` constraints

- `--dbscan-timeout`, `--dbscan-threads`, `--dbscan-max-hosts` only take effect when `--dbscan` is active
- Works with `-d`, `-f`, `--dg` — not with `-u` (no URL pool to extract hosts from)
- Skips private/loopback IPs automatically (192.168.x, 10.x, 127.x, etc.)
- Saves a separate `_dbscan_<ts>.json` + `_dbscan_<ts>.txt` file alongside the main output

### `--dg` constraints

- One `--dg` value only — `--dg=sqli` ✓, two `--dg` flags ✗
- Must use `--templates=FILE` syntax (with `=`, no space)
- `-c` / `--count` is **ignored** — the generator uses a fixed 50 results per dork

### `--analyze` constraints

- `--analyze-fetch-max` only takes effect when `--analyze-fetch` is also set
- `--analyze-out` requires `--analyze` to be active (or `.json` output)
- Requires `dorkeye_agents.py` in `Tools/` — otherwise silently skipped

### `--ui` constraints

- Cannot be combined with any other input flag in the same invocation
- Flask must be installed (`pip install flask`)
- Binds to `127.0.0.1` only — not exposed on LAN
- All scans launched from the UI are queued as background jobs with live SSE streaming

### `.json` output special behaviour

When `-o` ends in `.json` and `--analyze` is **not** explicitly set, DorkEye displays an interactive prompt:

```
Run analysis on results? [y/N]:
```

Use `--analyze` to force yes and skip the prompt (useful for scripting).

### `-f` / `--file` behaviour

- Searches current directory first, then `Dump/`
- `.json` supports both `{"results": [...]}` and raw `[...]` formats
- `.txt` reads one URL per line (lines starting with `http`)
- Combine freely with `--sqli`, `--xss`, `--analyze`, `--crawl`, `--dbscan`
- Existing URL hashes are reconstructed to avoid false duplicates

-----

## Interrupt Control

|Action                         |Effect                                     |
|-------------------------------|-------------------------------------------|
|**Single Ctrl+C**              |Skip current dork / task → continue to next|
|**Double Ctrl+C** (within 1.5s)|Exit immediately → save partial results    |

Works during: searches, file analysis, SQLi/XSS testing, inter-dork delays,
analysis, crawl, DB port scan.

-----

## Termux / Android

Auto-detected — no flags needed. When running inside Termux:

- Connect timeout: 3s (vs 4s)
- SQLi baseline samples: 1 (vs 2)
- Probe samples: 2 (vs 3), Boolean samples: 2 (vs 3)
- Time-based confirmations: 1 (vs 2)
- Banner shows: `Platform: Android / Termux ⚡ battery-saver active`

-----

## Common Combinations

```bash
# ── WIZARD ───────────────────────────────────────────────────────────────
python dorkeye.py --wizard

# ── WEB CONSOLE ──────────────────────────────────────────────────────────
python dorkeye.py --ui
python dorkeye.py --ui --port 9090
python Tools/dorkeye_web.py --port 9090 --no-browser

# ── DORK SEARCH ──────────────────────────────────────────────────────────
python dorkeye.py -d "site:example.com filetype:pdf" -o results.html
python dorkeye.py -d dorks.txt -c 100 -o results.json
python dorkeye.py -d "inurl:.php?id=" --sqli --stealth -o results.json
python dorkeye.py -d "inurl:.php?id=" --sqli --xss --stealth -o results.json
python dorkeye.py -d dorks.txt --analyze --analyze-fetch -o results.json
python dorkeye.py -d dorks.txt --sqli --xss --analyze --crawl -o results.json  # full pipeline

# ── DORK GENERATOR ───────────────────────────────────────────────────────
python dorkeye.py --dg=all
python dorkeye.py --dg=sqli --mode=medium --sqli -o results.json
python dorkeye.py --dg=all --mode=aggressive --dg-max=10000 -o results.json
python dorkeye.py --dg=sqli --sqli --xss --analyze --analyze-fetch -o results.json

# ── DIRECT URL TEST ──────────────────────────────────────────────────────
python dorkeye.py -u "https://target.com/page.php?id=1"
python dorkeye.py -u "https://target.com/page.php?id=1" --sqli --xss --stealth -o out.json
python dorkeye.py -u "https://target.com/page.php?id=1" --xss --xss-type reflected -o out.json

# ── FILE RE-PROCESSING ────────────────────────────────────────────────────
python dorkeye.py -f Dump/results.json --sqli -o retest.json
python dorkeye.py -f Dump/results.json --sqli --xss -o retest.json
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch -o reanalysis.json
python dorkeye.py -f Dump/results.json --sqli --xss --analyze --crawl -o full.json
python dorkeye.py -f Dump/results.json --dbscan --dbscan-timeout 3 -o dbscan.json

# ── DB PORT SCAN ─────────────────────────────────────────────────────────
python dorkeye.py -d dorks.txt --dbscan -o results.json
python dorkeye.py -d dorks.txt --dbscan --dbscan-timeout 3 --dbscan-threads 80 -o results.json
python Tools/db_portscan.py Dump/results.json
python Tools/db_portscan.py Dump/results.json --timeout 3 --threads 80
python Tools/db_portscan.py Dump/results.json --ports 3306 5432 27017 6379
python Tools/db_portscan.py Dump/results.json --stealth --max-hosts 50

# ── XSS-ONLY SCAN ────────────────────────────────────────────────────────
python dorkeye.py -d dorks.txt --xss --xss-type reflected -o results.json
python dorkeye.py -d dorks.txt --xss --xss-type dom -o results.json

# ── STANDALONE AGENTS ────────────────────────────────────────────────────
python dorkeye_analyze.py Dump/results.json --fetch --fmt=html

# ── FULL PIPELINE (generate + search + sqli + xss + analyze + crawl + dbscan) ──
python dorkeye.py \
  --dg=sqli \
  --mode=aggressive \
  --sqli \
  --xss \
  --stealth \
  -o full.json \
  --analyze \
  --analyze-fetch \
  --analyze-fetch-max=100 \
  --crawl \
  --crawl-rounds=6 \
  --crawl-stealth \
  --crawl-report \
  --dbscan \
  --dbscan-timeout=2.5 \
  --dbscan-threads=80 \
  --dbscan-max-hosts=200
```
