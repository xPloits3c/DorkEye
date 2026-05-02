# Web Console — DorkEye

> Matrix-themed local web dashboard for all DorkEye operations.
> Run scans, preview dorks, stream live output, and browse results — all from the browser.

-----

## Overview

`dorkeye_web.py` is a Flask-based web interface that wraps the entire `dorkeye.py` pipeline
in a browser UI. It launches a local server (bound to `127.0.0.1` only), spawns scans as
background jobs, and streams their output in real time via **Server-Sent Events (SSE)**.

No data leaves the machine. The dashboard is a local tool — it is not designed to be
exposed on a network interface.

**Lives in:** `DorkEye/Tools/dorkeye_web.py`

-----

## Requirements

```bash
pip install flask
```

`requests` and `rich` are used by the underlying modules but not required by the web layer itself.

-----

## Usage

### Via `dorkeye.py` (recommended)

```bash
# Start on default port 8080
python dorkeye.py --ui

# Start on a custom port
python dorkeye.py --ui --port 9090
```

### Standalone

```bash
python Tools/dorkeye_web.py
python Tools/dorkeye_web.py --port 9090
python Tools/dorkeye_web.py --port 9090 --no-browser
```

-----

## Flags

### Via `dorkeye.py`

|Flag      |Default|Description                                                      |
|----------|-------|-----------------------------------------------------------------|
|`--ui`    |off    |Launch the Web Console and open the browser automatically        |
|`--port N`|`8080` |Preferred port — auto-increments up to +100 if the port is in use|

### Standalone (`python Tools/dorkeye_web.py`)

|Flag          |Default|Description                             |
|--------------|-------|----------------------------------------|
|`--port N`    |`8080` |Starting port                           |
|`--no-browser`|off    |Start server without opening the browser|

-----

## Auto Port Selection

If the preferred port is in use, the server scans ports `start` through `start + 100`
and binds to the first free one. The actual URL is printed on startup:

```
  ▸ URL     →  http://127.0.0.1:8082
  ▸ Port    →  8082  (auto-selected)
```

The socket is created with `SO_REUSEADDR` so the port is released immediately on shutdown,
even after a force kill (`TIME_WAIT` is not an issue).

-----

## Dashboard Sections

### ◈ Dashboard

Home screen with at-a-glance stats and quick-action buttons:

|Card        |Shows                                |
|------------|-------------------------------------|
|Active Jobs |Number of currently running scan jobs|
|Total Jobs  |All jobs launched this session       |
|Result Files|Number of files in `Dump/`           |
|Dump Size   |Total disk usage of `Dump/`          |

Quick-action buttons jump directly to: **New Scan**, **URL Tester**, **Dork Gen**, **DB Scan**, **Results**.

The **Recent Jobs** table shows the last 6 jobs with status badges and a TERM button
to attach the terminal to any of them.

-----

### ◉ New Scan

Full-featured scan form covering every `dorkeye.py` pipeline option.

**Target**

- Dork string — single or multiline (one per line). Multiline input is automatically
  written to a temporary `.txt` file in `Dump/` and passed via `-d`.
- Max results per dork (`-c`)
- Output file name (`-o`) — extension determines format; defaults to `.html`

**Mode & Options**

|Toggle        |Flag mapped       |
|--------------|------------------|
|Stealth       |`--stealth`       |
|SQLi Detection|`--sqli`          |
|XSS Detection |`--xss`           |
|Skip Analysis |`--no-analyze`    |
|No Fingerprint|`--no-fingerprint`|

XSS type selector (`--xss-type`): `all` / `reflected` / `stored` / `dom`.

**Mode selector** (`--mode`): `soft` / `medium` / `aggressive` (default: aggressive in the UI).

**Collapsible sections** (expand as needed):

|Section            |Flags exposed                                                                                                     |
|-------------------|------------------------------------------------------------------------------------------------------------------|
|⊞ Dork Generator   |`--dg=CAT`, `--templates`, `--dg-max`                                                                             |
|◧ Filters          |`--blacklist`, `--whitelist`, `--config`                                                                          |
|🔬 Analysis Pipeline|`--analyze`, `--analyze-fetch`, `--analyze-fetch-max`, `--analyze-fmt`, `--analyze-out`                           |
|🕸 Adaptive Crawl   |`--crawl`, `--crawl-rounds`, `--crawl-max`, `--crawl-per-dork`, `--crawl-stealth`, `--crawl-report`, `--crawl-out`|
|🗄 DB Port Scan     |`--dbscan`, `--dbscan-timeout`, `--dbscan-threads`, `--dbscan-max-hosts`                                          |

-----

### ◎ URL Tester

Direct vulnerability test on a single target URL — maps to `dorkeye.py -u`.

|Field     |Flag mapped |
|----------|------------|
|Target URL|`-u`        |
|SQLi Test |`--sqli`    |
|XSS Test  |`--xss`     |
|XSS type  |`--xss-type`|
|Stealth   |`--stealth` |
|Output    |`-o`        |

-----

### ⊞ Dork Generator

Preview and export dork combinations without launching a scan.

|Control       |Description                                                                     |
|--------------|--------------------------------------------------------------------------------|
|Templates     |Dropdown populated from all `.yaml` files in `Templates/`                       |
|Category      |Populated dynamically from the selected template via `/api/templates/categories`|
|Mode          |`soft` / `medium` / `aggressive`                                                |
|Max combos    |Cap on generated combinations (10–10,000)                                       |
|PREVIEW button|Fetches up to 200 dorks inline for review                                       |
|EXPORT TXT    |Downloads the full set as `dorkeye_dorks_<ts>.txt`                              |

Template resolution order:

1. `default` / empty → `Templates/dorks_templates.yaml` if present, else first `.yaml` found
1. `all` → every `.yaml` in `Templates/`
1. Specific filename → that file; falls back to default if not found

-----

### ▣ Jobs

Table of all jobs launched this session:

|Column |Description                                       |
|-------|--------------------------------------------------|
|ID     |8-character hex job ID                            |
|Label  |Human-readable description of the job             |
|Status |`running` (animated) / `done` / `error` / `killed`|
|Started|Timestamp                                         |
|Ended  |Timestamp (or `—` if still running)               |
|Output |Output filename                                   |
|Actions|TERM / VIEW / KILL buttons                        |

- **TERM** — attaches the terminal bar to that job’s live output stream
- **VIEW** — opens the `.html` report in a new browser tab (only for `.html` outputs)
- **KILL** — sends `SIGTERM` to the subprocess

-----

### ◧ Results

File browser for the `Dump/` directory. Shows all `.html`, `.json`, `.txt`, `.csv`, `.md` files
(temp files starting with `_` are hidden).

|Column   |Description                                 |
|---------|--------------------------------------------|
|Name     |File name — click to open `.html` in browser|
|Size     |Human-readable file size                    |
|Modified |Last modified timestamp                     |
|FILE MODE|Re-process with `dorkeye.py -f`             |
|↓ DL     |Download the file                           |
|OPEN     |Open `.html` reports in a new tab           |

-----

## Terminal Bar

Persistent terminal strip at the bottom of the page. Streams output from the
active job via SSE.

|Control     |Action                                                   |
|------------|---------------------------------------------------------|
|Click header|Toggle between normal (200px) and expanded (400px) height|
|COPY        |Copy all terminal text to clipboard                      |
|CLEAR       |Clear terminal contents                                  |
|KILL        |Kill the active job (visible only while running)         |

**Line colouring:**

|Colour|Pattern matched                                        |
|------|-------------------------------------------------------|
|Green |`[✓]`, `SAFE`, `saved`, `done`, `completed`, `[ Open ]`|
|Yellow|`[~]`, `WARNING`, `WAF`, `skipping`                    |
|Red   |`[!]`, `VULNERABLE`, `CRITICAL`, `error`, `[ Closed ]` |
|Blue  |`[*]`, `Searching`, `Analyzing`, `Loading`, `DBScan`   |
|Dim   |Empty lines, separators                                |

ANSI escape codes and Rich markup are stripped from subprocess output before display.

-----

## Job System

Each scan is launched as a background subprocess via `subprocess.Popen`. The web layer
does not block — multiple jobs can run concurrently.

**Job lifecycle:**

```
api/run POST  →  JobManager.spawn()  →  Popen(dorkeye.py ...)
                                        ↓
                                  stdout/stderr merged
                                        ↓
                              Job.lines (deque, max 20,000)
                                        ↓
                              /api/stream/<jid>  (SSE)
                                        ↓
                              Terminal bar in browser
```

- `stdin` is pre-seeded with `n\n` to auto-answer the `Run analysis? [y/N]` prompt
  (prevents the job from hanging on an interactive checkpoint)
- `PYTHONUNBUFFERED=1`, `NO_COLOR=1`, `FORCE_COLOR=0` are set in the subprocess environment
- Subprocess `cwd` is set to the project root so relative paths resolve correctly

-----

## API Endpoints

|Method|Endpoint                   |Description                                    |
|------|---------------------------|-----------------------------------------------|
|GET   |`/`                        |Main dashboard HTML                            |
|GET   |`/api/status`              |Server status: version, port, running job count|
|GET   |`/api/jobs`                |List all jobs (summary)                        |
|GET   |`/api/jobs/<jid>`          |Job detail + full output lines                 |
|DELETE|`/api/jobs/<jid>`          |Kill a running job                             |
|GET   |`/api/stream/<jid>`        |SSE stream of job output                       |
|POST  |`/api/run`                 |Launch a new job (scan / urltest / file)       |
|GET   |`/api/dump`                |List files in `Dump/`                          |
|GET   |`/api/templates/list`      |List `.yaml` files in `Templates/`             |
|GET   |`/api/templates/categories`|List categories from a template file           |
|POST  |`/api/dorkgen/preview`     |Generate and return up to 200 dorks            |
|POST  |`/api/dorkgen/export`      |Generate and return full dork list as `.txt`   |
|GET   |`/dump/<filename>`         |Serve a file from `Dump/`                      |

-----

## Path Resolution

The web module resolves the project root at startup by walking up the directory tree
from `dorkeye_web.py` looking for `dorkeye.py`:

```
DorkEye/
    dorkeye.py          ← root anchor
    Dump/               ← output directory
    Templates/          ← dork templates
    Tools/
        dorkeye_web.py  ← starts here
```

This works whether `dorkeye_web.py` is run directly from `Tools/` or from the project root.

-----

## Security Notes

- The server binds exclusively to `127.0.0.1` — it is **not reachable from other machines**
  on the network.
- Template path resolution includes a **directory traversal guard**: any path that resolves
  outside `Templates/` is rejected and falls back to the default template.
- SIGINT is restored to the default handler before starting Flask so that Ctrl+C correctly
  shuts down the Werkzeug server (DorkEye installs a custom SIGINT handler that would
  otherwise intercept the signal and prevent clean shutdown).

-----

## Shutdown

```
Ctrl+C
```

The server closes cleanly, releases the port immediately (SO_REUSEADDR), and prints:

```
  [!] Server stopped. Port released.
```

-----

## Dependencies

|Package   |Required                |Used for                          |
|----------|------------------------|----------------------------------|
|`flask`   |**yes**                 |HTTP server, routing, SSE         |
|`werkzeug`|yes (bundled with Flask)|`make_server`, SO_REUSEADDR socket|
|`requests`|optional                |Used by underlying scan modules   |
|`rich`    |optional                |Used by underlying scan modules   |

```bash
pip install flask requests rich
```
