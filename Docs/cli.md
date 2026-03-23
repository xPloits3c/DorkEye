# CLI Reference — DorkEye v4.8

> All 31 flags, all accepted values, all combinations.
> Single-page cheat sheet — keep it open while you hunt.

-----

## Input Sources — one required

|Flag               |Type|Description                                                                       |
|-------------------|----|----------------------------------------------------------------------------------|
|`--wizard`         |bool|Launch the interactive guided session (menus for everything)                      |
|`-d DORK`, `--dork`|str |Single dork string **or** path to a `.txt` file (one dork per line, `#` = comment)|
|`-u URL`, `--url`  |str |Single URL — direct SQL injection test, no search performed                       |
|`-f FILE`, `--file`|str |Load saved DorkEye results (`.json` or `.txt`) for re-processing                  |
|`--dg[=CATEGORY]`  |str |Activate Dork Generator; value = category name or `all` (default if omitted)      |
|`--create-config`  |bool|Write sample `dorkeye_config.yaml` to disk and exit                               |

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
|`--stealth`       |off    |Stealth mode — 1.4×–1.8× longer delays, extended rate-limit pauses |
|`--no-analyze`    |off    |Skip HEAD-request file analysis (no size / content-type / status)  |
|`--no-fingerprint`|off    |Disable HTTP fingerprint rotation (falls back to basic UA rotation)|
|`--blacklist EXT…`|none   |Space-separated extensions to exclude (e.g. `.jpg .png .gif`)      |
|`--whitelist EXT…`|none   |Space-separated extensions — only these are kept                   |

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

The crawler analyzes initial results (domains, paths, technologies, extensions), generates refined dorks, searches again, and repeats until diminishing returns.

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
|`.txt`   |Numbered plain text          |Per-result details (title, category, SQLi status, WAF)                                                                                                                  |

If no extension is provided, `.json` is appended automatically.

### `--analyze-fmt`

|Value |Output                                                         |
|------|---------------------------------------------------------------|
|`html`|Full dark-theme HTML with triage, secrets, credentials sections|
|`md`  |Markdown with tables                                           |
|`json`|Structured JSON (pii, emails, subdomains, cve_dorks keys)      |
|`txt` |Plain text summary                                             |

### SQLi Confidence Levels

Reported in results and HTML reports:

|Level     |Meaning                                                 |
|----------|--------------------------------------------------------|
|`NONE`    |No injection detected                                   |
|`LOW`     |Weak signal (e.g. UNION col-mismatch only)              |
|`MEDIUM`  |Boolean blind differential or time-based confirmed      |
|`HIGH`    |DB error signature matched or strong UNION evidence     |
|`CRITICAL`|Multiple methods confirmed across parameters (score ≥ 5)|

### WAF Detection

Detected automatically during SQLi testing. Supported signatures:

Cloudflare · ModSecurity · Wordfence · Sucuri · Imperva · Akamai · F5 BigIP · Barracuda · FortiWeb · AWS WAF · DenyAll · Reblaze · generic (403/406/419/429 with short body)

-----

## Compatibility Rules

### Mutually exclusive inputs

```
--wizard  ←→  -d  ←→  -u  ←→  -f  ←→  --dg  ←→  --create-config
```

Only one input source per invocation.

### `-u` constraints

- `--sqli` is auto-enabled even if not specified
- Not compatible with `--analyze`, `--crawl`, `-d`, `-f`, `--dg`
- Execution stops immediately after the SQLi test
- Result is saved to `-o` if provided

### `--dg` constraints

- One `--dg` value only — `--dg=sqli` ✓, two `--dg` flags ✗
- Must use `--templates=FILE` syntax (with `=`, no space)
- `-c` / `--count` is **ignored** — the generator uses a fixed 50 results per dork

### `--analyze` constraints

- `--analyze-fetch-max` only takes effect when `--analyze-fetch` is also set
- `--analyze-out` requires `--analyze` to be active (or `.json` output)
- Requires `dorkeye_agents.py` in `Tools/` — otherwise silently skipped

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
- Combine freely with `--sqli`, `--analyze`, `--crawl`
- Existing URL hashes are reconstructed to avoid false duplicates

-----

## Interrupt Control

|Action                         |Effect                                     |
|-------------------------------|-------------------------------------------|
|**Single Ctrl+C**              |Skip current dork / task → continue to next|
|**Double Ctrl+C** (within 1.5s)|Exit immediately → save partial results    |

Works during: searches, file analysis, SQLi testing, inter-dork delays, analysis, crawl.

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

# ── DORK SEARCH ──────────────────────────────────────────────────────────
python dorkeye.py -d "site:example.com filetype:pdf" -o results.html
python dorkeye.py -d dorks.txt -c 100 -o results.json
python dorkeye.py -d "inurl:.php?id=" --sqli --stealth -o results.json
python dorkeye.py -d dorks.txt --analyze --analyze-fetch -o results.json
python dorkeye.py -d dorks.txt --sqli --analyze --crawl -o results.json   # full pipeline

# ── DORK GENERATOR ───────────────────────────────────────────────────────
python dorkeye.py --dg=all
python dorkeye.py --dg=sqli --mode=medium --sqli -o results.json
python dorkeye.py --dg=all --mode=aggressive --dg-max=10000 -o results.json
python dorkeye.py --dg=sqli --sqli --analyze --analyze-fetch -o results.json

# ── DIRECT URL TEST ──────────────────────────────────────────────────────
python dorkeye.py -u "https://target.com/page.php?id=1"
python dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o out.json

# ── FILE RE-PROCESSING ──────────────────────────────────────────────────
python dorkeye.py -f Dump/results.json --sqli -o retest.json
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch -o reanalysis.json
python dorkeye.py -f Dump/results.json --sqli --analyze --crawl -o full.json

# ── FULL PIPELINE (generate + search + detect + analyze + crawl) ─────────
python dorkeye.py \
  --dg=sqli \
  --mode=aggressive \
  --sqli \
  --stealth \
  -o full.json \
  --analyze \
  --analyze-fetch \
  --analyze-fetch-max=100 \
  --crawl \
  --crawl-rounds=6 \
  --crawl-stealth \
  --crawl-report

# ── STANDALONE AGENTS (separate script) ──────────────────────────────────
python dorkeye_analyze.py Dump/results.json --fetch --fmt=html
```
