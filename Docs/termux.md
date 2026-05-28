# DorkEye on Termux

> Run the full DorkEye pipeline directly from your Android device.
> Termux is auto-detected — no extra flags needed. Battery-saver tuning activates automatically.

-----

## Requirements

- Android 7.0 or higher
- [Termux](https://f-droid.org/packages/com.termux/) installed from **F-Droid** (the Play Store version is deprecated and unsupported)
- Internet connection

> **Do not use the Play Store version of Termux.** It is outdated and will cause dependency errors.

-----

## Installation

### Step 1 — Update Termux packages

```bash
pkg update && pkg upgrade -y
```

Run this first, every time, on a fresh Termux install.

-----

### Step 2 — Install system dependencies

```bash
pkg install -y python git libxml2 libxslt
```

|Package  |Why it’s needed                               |
|---------|----------------------------------------------|
|`python` |Runtime for DorkEye                           |
|`git`    |Clone the repository                          |
|`libxml2`|Required by `lxml` (HTML parser) — C extension|
|`libxslt`|Required by `lxml` — C extension              |


> **Important:** `libxml2` and `libxslt` must be installed via `pkg` **before** running `pip install`.
> Skipping this step will cause the `lxml` build to fail with a `fatal error` during requirements installation.

-----

### Step 3 — Clone DorkEye

```bash
git clone https://github.com/xPloits3c/DorkEye
cd DorkEye
```

-----

### Step 4 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs all required libraries:

|Library                  |Purpose                        |
|-------------------------|-------------------------------|
|`requests` / `urllib3`   |HTTP engine                    |
|`PyYAML`                 |Config and template parsing    |
|`beautifulsoup4` / `lxml`|HTML parsing                   |
|`rich`                   |Terminal UI and formatting     |
|`colorama`               |Color support                  |
|`ddgs`                   |DuckDuckGo search integration  |
|`flask`                  |Web Console (`--ui`) — optional|

-----

### Step 5 — Verify the installation

```bash
python dorkeye.py -h
```

Expected output: the full help banner with all available flags.
If you see it, DorkEye is ready.

-----

## Termux Auto-Detection

When DorkEye detects it is running inside Termux, the banner displays:

```
Platform: Android / Termux ⚡ battery-saver active
```

The following parameters are automatically reduced to preserve battery and avoid timeouts on mobile connections:

|Parameter               |Desktop|Termux|
|------------------------|-------|------|
|Connect timeout         |4 s    |3 s   |
|SQLi baseline samples   |2      |1     |
|Probe samples           |3      |2     |
|Boolean blind samples   |3      |2     |
|Time-based confirmations|2      |1     |

No flags required — this tuning is applied automatically.

-----

## Basic Usage

### Interactive wizard (recommended for beginners)

```bash
python dorkeye.py --wizard
```

Guided menus for every option. The easiest way to start.

-----

### Single dork search

```bash
python dorkeye.py -d "inurl:login.php" -o results.html
```

Searches DuckDuckGo for the dork and saves an interactive HTML report in `Dump/`.

-----

### Load dorks from a file

```bash
python dorkeye.py -d dorks.txt -c 100 -o results.json
```

`dorks.txt` — one dork per line, lines starting with `#` are ignored.
`-c 100` — fetch up to 100 results per dork (default: 50).

-----

### Direct URL test (SQLi + XSS, no search)

```bash
python dorkeye.py -u "https://target.com/page.php?id=1"
```

Runs the full vulnerability pipeline directly against a single URL.
`--sqli` and `--xss` are auto-enabled in this mode.

-----

## Vulnerability Scanning

### SQL Injection

```bash
python dorkeye.py -d "inurl:.php?id=" --sqli -o results.json
```

### XSS

```bash
python dorkeye.py -d "inurl:search.php?q=" --xss -o results.json
```

### SQLi + XSS combined

```bash
python dorkeye.py -d "inurl:.php?id=" --sqli --xss -o results.json
```

### With stealth mode

```bash
python dorkeye.py -d "inurl:.php?id=" --sqli --xss --stealth -o results.json
```

`--stealth` adds longer delays between requests (1.4×–1.8×) to reduce detection and rate-limiting.
Recommended on mobile connections where reconnections are costly.

-----

## Output Formats

All output files are saved inside the `Dump/` folder (auto-created).

|Extension|Format                                                            |
|---------|------------------------------------------------------------------|
|`.html`  |Interactive dark-theme report — filterable, searchable, exportable|
|`.json`  |Full structured data + statistics — triggers analysis prompt      |
|`.csv`   |Spreadsheet-compatible, all columns included                      |
|`.txt`   |Plain text, one result per block                                  |

```bash
# HTML report (default, recommended for reading)
python dorkeye.py -d "inurl:config.php" -o report.html

# JSON (required for --analyze, --crawl, --dbscan re-processing)
python dorkeye.py -d "inurl:config.php" -o results.json
```

If no extension is provided, `.json` is appended automatically.

-----

## Re-processing Saved Results

```bash
# Add SQLi scan to existing results
python dorkeye.py -f Dump/results.json --sqli -o retest.json

# Add XSS scan
python dorkeye.py -f Dump/results.json --xss -o retest.json

# Run full analysis on saved results
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch -o analysis.json
```

Useful to avoid repeating the search — reuse results and add new scan layers.

-----

## Dork Generator

Generate dorks from built-in templates and search immediately.

```bash
# Generate all categories, search, detect SQLi
python dorkeye.py --dg=all --sqli -o results.json

# Generate SQLi-focused dorks, medium intensity
python dorkeye.py --dg=sqli --mode=medium --sqli -o results.json
```

|`--mode` value|Behaviour                                  |
|--------------|-------------------------------------------|
|`soft`        |Low-risk dorks, minimal expansion (default)|
|`medium`      |Broader coverage patterns                  |
|`aggressive`  |Maximum combinations — high result volume  |


> On mobile, `soft` or `medium` is recommended. `aggressive` can generate thousands of requests.

-----

## Analysis Pipeline

Requires `Tools/dorkeye_agents.py`. Automatically skipped if the file is missing.

```bash
python dorkeye.py -d dorks.txt --analyze -o results.json
python dorkeye.py -d dorks.txt --analyze --analyze-fetch -o results.json
```

`--analyze` — runs triage, secrets detection, and generates a report after the search.
`--analyze-fetch` — also downloads page content for HIGH / CRITICAL results.

Output format options: `html` (default), `md`, `json`, `txt`.

```bash
python dorkeye.py -d dorks.txt --analyze --analyze-fmt md -o results.json
```

-----

## DB Port Scanner

Requires `Tools/db_portscan.py`. Scans hosts extracted from results for exposed database ports.

```bash
# Integrated — runs after the search
python dorkeye.py -d dorks.txt --dbscan -o results.json

# Standalone — on saved results
python Tools/db_portscan.py Dump/results.json
python Tools/db_portscan.py Dump/results.json --timeout 3 --threads 40
```

> **Termux note:** The default `--dbscan-threads 60` may be high for some Android devices.
> If you experience instability, reduce it: `--dbscan-threads 30` or `--dbscan-threads 40`.
> Private and loopback IPs are automatically excluded from the scan.

-----

## Web Console (`--ui`)

Launches a local Flask-based dashboard in your browser.

```bash
python dorkeye.py --ui
```

> **Termux note:** The browser will not open automatically on Android.
> After launching, open your browser manually and navigate to:
> 
> ```
> http://127.0.0.1:8080
> ```
> 
> If port 8080 is busy, DorkEye auto-increments. Check the terminal output for the actual port.

`--ui` cannot be combined with any other input flag (`-d`, `-u`, `-f`, `--dg`) in the same command.

-----

## Interrupt Control

|Action                                           |Effect                                 |
|-------------------------------------------------|---------------------------------------|
|Single **Ctrl+C** (or **Vol Down + C** in Termux)|Skip current task → continue to next   |
|Double **Ctrl+C** within 1.5 s                   |Exit immediately → save partial results|

-----

## Common Combinations for Termux

```bash
# Quickest start — guided wizard
python dorkeye.py --wizard

# Search + SQLi + HTML report
python dorkeye.py -d "inurl:.php?id=" --sqli -o results.html

# Search + SQLi + XSS + stealth
python dorkeye.py -d dorks.txt --sqli --xss --stealth -o results.json

# Direct URL vulnerability test
python dorkeye.py -u "https://target.com/page.php?id=1"

# Generate dorks + scan + analyze
python dorkeye.py --dg=sqli --mode=medium --sqli --analyze -o results.json

# Re-process saved results — add analysis
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch -o analysis.json

# DB port scan on saved results (reduced threads for mobile)
python Tools/db_portscan.py Dump/results.json --threads 40 --timeout 3
```

-----

## Troubleshooting

**`lxml` build fails during `pip install`**

```bash
pkg install libxml2 libxslt
pip install -r requirements.txt
```

**`ModuleNotFoundError` for any package**

```bash
pip install -r requirements.txt --force-reinstall
```

**`git clone` is slow or fails**

Check your connection or try:

```bash
pkg install wget
```

and download the ZIP from GitHub manually.

**`--ui` — browser does not open**

Expected on Android. Open `http://127.0.0.1:8080` manually in any browser.

**Double Ctrl+C not working**

In Termux, use the keyboard shortcut **Vol Down + C** as the Ctrl key equivalent.

-----

## Next Steps

For the full list of 38 flags, advanced combinations, and detailed module documentation:

- [`Docs/cli.md`](cli.md) — complete CLI reference
- [`Docs/xss.md`](xss.md) — XSS detection engine
- [`Docs/sqli.md`](sqli.md) — SQL injection engine
- [`Docs/dbscan.md`](dbscan.md) — DB port scanner
- [`Docs/agents.md`](agents.md) — analysis pipeline
- [`Docs/webconsole.md`](webconsole.md) — Web Console (`--ui`)

-----

## Community & Support

- **GitHub:** [github.com/xPloits3c/DorkEye](https://github.com/xPloits3c/DorkEye)
- **Telegram:** [t.me/DorkEye](https://t.me/DorkEye)