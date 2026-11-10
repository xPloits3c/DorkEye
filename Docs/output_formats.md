<img width="1264" height="843" alt="image" src="https://github.com/user-attachments/assets/3f4cdecf-78ac-4fe6-aefe-2d6d85118378" />

# Output Formats — DorkEye Project

All result files are saved to the `Dump/` folder, created automatically in the same directory as `dorkeye.py`.

---

## Specify Output

```bash
python dorkeye.py -d "site:example.com" -o results.html   # HTML report
python dorkeye.py -d "site:example.com" -o results.json   # JSON + analysis prompt
python dorkeye.py -d "site:example.com" -o results.csv    # CSV spreadsheet
python dorkeye.py -d "site:example.com" -o results.txt    # Plain text
```

If `-o` is omitted, DorkEye generates: `report_YYYYMMDD_HHMMSS.html`

---

## Tabbed Report

When other phases run with a search (`--analyze`, `--dbscan`, `--crawl`, `--osint`), DorkEye
writes **one** HTML file with a tab per phase instead of separate reports:

| Tab | Shown when |
|-----|------------|
| Dorks | always — the HTML report described below |
| Analyze | `--analyze` (or analysis accepted at the prompt) |
| DBScan | `--dbscan` found hosts to scan |
| Crawl | `--crawl` |
| OSINT | `--osint` / `--osint-seed` — see [osint.md](osint.md) |

Each tab is the complete, self-contained report of that phase, isolated in its own frame, so
filters, exports and the OSINT graph keep working exactly as on their own.

| `-o` | Files in `Dump/` |
|------|------------------|
| `scan.html` | `scan.html` — the tabbed report |
| `scan.json` / `.csv` / `.txt` | `scan.json` (results, unchanged) **+** `scan.html` (tabbed report) |

With no extra phase, `-o` is written as usual in the format of its extension.

---

## HTML Report

The default and most feature-rich format. Opens in any browser — no server required.

### Interface elements

**Filter bar** (left side):
- `ALL` — show all results
- `DOC` — documents, archives, backups — with sub-filters: PDF / DOCX / XLSX / PPT / Archives
- `SQLi` — results with SQLi tests — sub-filters: ALL / CRITICAL / VULN / SAFE
- `SCRIPTS` — scripts, configs, credentials — sub-filters: PHP / ASP / SH-BAT / CONFIGS / CREDS
- `PAGES` — webpages

**Right-side panels:**
- `🔍 SEARCH` — real-time keyword filter across URL, title, category, and dork simultaneously; match counter updates live
- `⬇ LINKS` — export filtered URL list as TXT, JSON, or CSV; scope respects active filter + search
- `📁 FILES` — file-type results with checkboxes, status indicator (✓ / ✗), size, individual download icon; bulk select/export

**Results table columns:**
- `#` — row index
- `URL` — truncated link + `↓` download + `ⓘ` detail popup
- `Title` — page title
- `Category` — color-coded badge
- `SQLi Status` — CRITICAL / VULN / SAFE / N/A with confidence
- `WAF` — WAF name if detected
- `Size` — formatted file size

**ⓘ Detail popup:** clicking the `ⓘ` button on any row opens a floating panel with:

| Field | Content |
|-------|---------|
| URL | Full URL (truncated at 80 chars) |
| Title | Page title |
| Category | File category |
| Extension | File extension |
| Size | Formatted file size |
| Timestamp | Discovery time |
| Dork | Dork that produced this result |
| Snippet | DDG body snippet (120 chars) |
| SQLi Status | Confidence level |
| Method / Payload | Test method(s) and evidence |
| WAF | WAF name if detected |

The popup closes on ✕ click or click-outside. Positioning is viewport-aware.

**Matrix rain background** — animated green character rain (toggle: reduce motion for accessibility).

---

## JSON

```bash
python dorkeye.py -d "site:example.com" -o results.json
```

When the output is `.json`, DorkEye prompts after the search:
> *"Vuoi analizzare i risultati? [y/N]"*

Use `--analyze` to skip the prompt and force yes.

### Structure

```json
{
  "metadata": {
    "total_results": 42,
    "generated_at": "2026-03-21 14:30:00",
    "sqli_detection_enabled": true,
    "sqli_vulnerabilities_found": 3,
    "waf_blocked_count": 1,
    "http_fingerprinting_enabled": true,
    "stealth_mode": false,
    "statistics": { "total_found": 48, "duplicates": 6, "..." }
  },
  "results": [
    {
      "url":          "https://target.com/page.php?id=1",
      "title":        "Page title",
      "snippet":      "DDG body snippet...",
      "dork":         "inurl:.php?id=",
      "timestamp":    "2026-03-21 14:25:11",
      "extension":    ".php",
      "category":     "scripts",
      "file_size":    null,
      "content_type": null,
      "accessible":   null,
      "status_code":  null,
      "sqli_test": {
        "tested":             true,
        "vulnerable":         true,
        "overall_confidence": "high",
        "waf_detected":       null,
        "message":            "Tested 2 parameter(s)",
        "tests": [
          {
            "method":     "error_based",
            "vulnerable": true,
            "confidence": "high",
            "evidence":   ["MYSQL error signature matched: extractvalue(0,...)"]
          }
        ]
      }
    }
  ]
}
```

### Analysis report JSON (from `--analyze --analyze-fmt json`)

```json
{
  "meta":       { "generated_at": "...", "target": "...", "engine": "DorkEye v5.2 + Agents v3.1" },
  "metrics":    { "total": 42, "by_label": { "CRITICAL": 3, "HIGH": 8, "..." }, "secrets": 5, "pii": 2, "emails": 7, "subdomains": 4 },
  "secrets":    [{ "type": "AWS_KEY", "severity": "CRITICAL", "value": "AKIA…", "..." }],
  "pii":        [{ "type": "CF_IT", "value": "RSM***", "..." }],
  "emails":     [{ "email": "admin@target.com", "category": "admin", "source": "..." }],
  "subdomains": { "target.com": ["api.target.com", "staging.target.com"] },
  "cve_dorks":  ["site:target.com inurl:wp-login.php", "..."],
  "results":    [...]
}
```

---

## CSV

```bash
python dorkeye.py -d "site:example.com" -o results.csv
```

Columns:

| Column | Content |
|--------|---------|
| `url` | Full URL |
| `title` | Page title |
| `snippet` | DDG snippet |
| `dork` | Search dork |
| `timestamp` | Discovery timestamp |
| `extension` | File extension |
| `category` | File category |
| `file_size` | Size in bytes (if analyzed) |
| `content_type` | Content-Type header (if analyzed) |
| `accessible` | `True` / `False` (if analyzed) |
| `status_code` | HTTP status code (if analyzed) |
| `sqli_vulnerable` | `True` / `False` |
| `sqli_confidence` | `critical` / `high` / `medium` / `low` / `none` |
| `waf_detected` | WAF name or empty |

---

## TXT

```bash
python dorkeye.py -d "site:example.com" -o results.txt
```

Plain numbered list with per-result details:

```
1. https://target.com/admin/login.php
   Title: Admin Login
   Category: scripts
   SQLi: VULNERABLE (high)
   WAF: cloudflare

2. https://target.com/backup.sql
   Title: (no title)
   Category: databases
```

---

## OSINT Files

`--osint` adds these files to `Dump/` (names follow the OSINT database name, see
[osint.md](osint.md#database)):

| File | Content |
|------|---------|
| `<name>.sqlite` | The graph database (always) |
| `<name>.html` | Standalone OSINT report (OSINT-only runs; otherwise it is the OSINT tab) |
| `<name>.csv`, `<name>_graph.json`, `<name>.graphml`, `<name>_summary.txt` | With `--osint-export csv,json,graphml,txt` |

---

## Analysis Report Formats (`--analyze-fmt`)

The Agents v3.1 pipeline produces its own report separately from the main result file.

```bash
--analyze-fmt html   # full dark-theme HTML with all agent sections (default)
--analyze-fmt md     # markdown with tables
--analyze-fmt json   # structured JSON with pii, emails, subdomains, cve_dorks
--analyze-fmt txt    # plain text summary
```

Default output path: `{basename}_analysis_{TIMESTAMP}.{fmt}` next to the main output file.
Override with `--analyze-out custom_report.html`.
