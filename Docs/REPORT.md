# DorkEye — HTML Report Interface



> **File:** `report_YYYYMMDD_HHMMSS.html` (generated automatically, or via `-o filename.html`)
> **Engine:** self-contained single-file HTML — no external dependencies, no server required.
> Open in any modern browser. All logic runs client-side.

---

## Table of Contents

1. [Overview](#overview)
2. [Visual Design](#visual-design)
3. [Page Structure](#page-structure)
4. [Header](#header)
5. [Alert Banners](#alert-banners)
6. [Statistics Cards](#statistics-cards)
7. [Toolbar](#toolbar)
   - [Left — Category Filters](#left--category-filters)
   - [Right — Action Panels](#right--action-panels)
8. [🔍 Search Panel](#-search-panel)
9. [⬇ Export Links Panel](#-export-links-panel)
10. [📁 Export Files Panel](#-export-files-panel)
11. [Results Table](#results-table)
12. [Embedded Data](#embedded-data)
13. [Responsive Breakpoints](#responsive-breakpoints)
14. [Category Color Reference](#category-color-reference)
15. [SQLi Status Reference](#sqli-status-reference)
16. [Data Structures](#data-structures)

---

## Overview

The HTML report is a **fully interactive, self-contained single-file** dashboard generated at the end of every DorkEye scan. It embeds all result data as inline JavaScript constants (`EXPORT_DATA`, `FILE_DATA`) so it remains fully functional offline and without any backend.

```
report_20260314_090118.html   ← auto-named when -o is not specified
```

---

## Visual Design

| Property        | Value                                                  |
|-----------------|--------------------------------------------------------|
| Theme           | Matrix / terminal — black background, green phosphor   |
| Background      | Animated Matrix rain canvas (opacity 0.32)             |
| Font            | `'Courier New', monospace` throughout                  |
| Primary color   | `#00ff41` (bright green)                               |
| Accent green    | `#00aa2a`, `#009922`                                   |
| Alert red       | `#ff3333`, `#ff2222`                                   |
| Alert yellow    | `#ffaa00`, `#ffcc44`                                   |
| Blue (panels)   | `#00aaff`, `#007acc`, `#0077bb`                        |
| SQLi critical   | `#ff00ff` (magenta, with glow)                         |

The Matrix rain animation is rendered on a `<canvas id="matrix-canvas">` fixed behind all content. It uses katakana characters + hex digits and runs at ~22 fps via `setInterval(draw, 45)`. It is purely decorative and has `pointer-events: none`.

---

## Page Structure

```
<body>
├── <canvas id="matrix-canvas">        ← animated background
└── <div id="content">
    ├── .header                        ← title + generation time
    ├── .sqli-alert          (optional, only if vulns found)
    ├── .waf-alert           (optional, only if WAF detected)
    ├── .stats               ← 5 stat cards
    ├── .toolbar
    │   ├── .filter-bar      ← LEFT: green category filters
    │   └── .right-btns      ← RIGHT: SEARCH | LINKS | FILES
    ├── .active-sub-info     ← live filter status line
    ├── .table-wrap
    │   └── <table>          ← results table
    └── .footer
```

---

## Header

```html
<div class="header">
  <h1>■ DorkEye | Report _</h1>
  <div class="subtitle">→ Generated: YYYY-MM-DD HH:MM:SS | xploits3c.github.io/DorkEye</div>
</div>
```

- The `_` after "Report" has class `.blink` — CSS animation `blink 1.1s step-end infinite`
- Timestamp is injected at generation time via Python `datetime.now()`

---

## Alert Banners

### SQLi Alert (conditional)

Rendered only when `sqli_vulnerable > 0`.

```html
<div class="sqli-alert">
  <h2>⚠ SECURITY ALERT ⚠</h2>
  <p><strong>N</strong> potential SQL injection vulnerabilities detected!</p>
</div>
```

Style: dark red background, left border `#ff2222`, text `#ff6666`.

### WAF Alert (conditional)

Rendered only when `waf_detected > 0`.

```html
<div class="waf-alert">
  ⚠ <strong>N</strong> WAF-protected target(s) detected — SQLi results may have false negatives.
</div>
```

Style: dark amber background, left border `#ffaa00`, text `#ffcc44`.

---

## Statistics Cards

Five cards rendered in a responsive CSS grid (`repeat(auto-fit, minmax(190px, 1fr))`):

| Card | Source | Color |
|------|--------|-------|
| TOTAL RESULTS | `len(self.results)` | green |
| DUPLICATES FILTERED | `self.stats["duplicates"]` | green |
| SQLI VULNERABILITIES | `self.stats["sqli_vulnerable"]` | `#ff3333` red |
| WAF DETECTED | `self.stats["waf_detected"]` | `#ffaa00` amber |
| EXECUTION TIME | `time.time() - self.start_time` in seconds | green |

---

## Toolbar

The toolbar is a flex row with two zones:

```
[ FILTER ]  ALL  DOC ▼  SQLi ▼  SCRIPTS ▼  PAGE        🔍 SEARCH  ⬇ LINKS  📁 FILES
└──────────────── .filter-bar (flex:1) ─────────────┘  └─── .right-btns ────────────┘
```

---

## Left — Category Filters

All filter buttons are styled in **green** (`#00aa2a` border, `#00ff41` active background).

### Top-level buttons

| Button | `data-group` | Covers categories |
|--------|-------------|-------------------|
| ALL | `all` | All rows |
| DOC ▼ | `doc` | `documents`, `archives`, `backups` |
| SQLi ▼ | `sqli` | All rows with SQLi test result |
| SCRIPTS ▼ | `scripts` | `scripts`, `configs`, `credentials` |
| PAGE | `page` | `webpage` |

Active button: `background: #00ff41; color: #000`.
Each button shows a live count badge (`.badge`) updated by `buildSubBadges()` on init.

### DOC submenu

| Sub-filter | `data-sub` | Extension match |
|-----------|------------|-----------------|
| ALL | `doc-all` | all doc categories |
| PDF | `doc-pdf` | `.pdf` |
| DOCX | `doc-docx` | `.doc` `.docx` `.odt` |
| XLSX | `doc-xlsx` | `.xls` `.xlsx` `.ods` |
| PPT | `doc-ppt` | `.ppt` `.pptx` |
| ARCHIVES | `doc-arc` | `.zip` `.rar` `.tar` `.gz` `.7z` `.bz2` |

### SQLi submenu

| Sub-filter | `data-sub` | Logic |
|-----------|------------|-------|
| SQLi ALL | `sqli-all` | `data-sqli` ∈ {`vuln`, `safe`, `critical`} |
| SQLi CRITICAL | `sqli-critical` | `data-sqli === "critical"` |
| SQLi VULN | `sqli-vuln` | `data-sqli` ∈ {`vuln`, `critical`} |
| SQLi SAFE | `sqli-safe` | `data-sqli === "safe"` |

### SCRIPTS submenu

| Sub-filter | `data-sub` | Extension match |
|-----------|------------|-----------------|
| ALL | `scripts-all` | all script categories |
| PHP | `scripts-php` | `.php` |
| ASP | `scripts-asp` | `.asp` `.aspx` |
| SH/BAT | `scripts-sh` | `.sh` `.bat` `.ps1` |
| CONFIGS | `scripts-config` | `.conf` `.config` `.ini` `.yaml` `.yml` `.json` `.xml` |
| CREDS | `scripts-creds` | `.env` `.git` `.svn` `.htpasswd` |

### Filter logic

```
applyFilter(btn)       → sets activeGroup, opens submenu
applySubFilter(btn)    → sets activeSub, calls renderRows()
renderRows()           → toggles .hidden on each <tr> based on category + SUB_PRED
buildSubBadges()       → counts rows per sub-filter and writes to badge spans
updateInfoBar()        → updates .active-sub-info text with visible count
```

Filters compose with Search: a row must pass **both** the category filter and the search query to be visible. Hidden state uses two separate classes: `.hidden` (filter) and `.srch-hidden` (search). Both must be absent for a row to be visible.

---

## Right — Action Panels

Three blue buttons (`#0077bb` border, `#00aaff` text) on the right side of the toolbar. Each opens a floating panel (`.rpanel`) positioned `absolute` below the button. Only one panel can be open at a time — opening one closes the others via `closeAllPanels()`. Clicking outside any panel also closes all. Each panel has an `×` close button (`.panel-close`) in the top-right corner.

```javascript
closeAllPanels()  // closes srchPanel, exportPanel, filesPanel
                  // removes .open from all three toggle buttons
```

---

## 🔍 Search Panel

**Button:** `🔍 SEARCH`
**Panel id:** `srchPanel`
**Min width:** 320px

### Features

| Element | Description |
|---------|-------------|
| Text input `#srchInput` | Real-time filter; fires `doSearch()` on every `oninput` event |
| CLEAR button | Calls `clearSearch()` — removes query and `srch-hidden` from all rows |
| Match counter | "Matching: X of N results" — updated live |
| Scope toggles | Four buttons to control which row fields are searched |

### Search Scopes

| Scope button | `data-scope` | Row field searched |
|-------------|-------------|-------------------|
| URL | `url` | `data-url` attribute |
| TITLE | `title` | `data-title` attribute |
| CATEGORY | `category` | `data-category` attribute |
| DORK | `dork` | `data-dork` attribute |

Each scope button is independently toggle-able via `toggleScope(btn)`. All four are active by default. At least one scope should remain active. Search is case-insensitive (`toLowerCase()`).

### Behaviour

```javascript
doSearch()          // runs on every keystroke; iterates all non-.hidden rows
applySearchToRow()  // called per row: checks haystack.includes(query)
                    // adds/removes .srch-hidden class
```

Search respects active category filters — it only searches visible (non-`.hidden`) rows.

---

## ⬇ Export Links Panel

**Button:** `⬇ LINKS`
**Panel id:** `exportPanel`
**Min width:** 370px

Exports URL metadata (not file content) as text lists, JSON, or CSV.

### Export scopes

| Label | Scope key | Rows included |
|-------|-----------|---------------|
| All (N) | `all` | Every row in `EXPORT_DATA` |
| ⚠ All tested | `sqli-all` | Rows where `sqli` ∈ {`vuln`, `safe`, `critical`} |
| ⚠ VULN only | `sqli-vuln` | Rows where `sqli` ∈ {`vuln`, `critical`} |
| ✓ SAFE only | `sqli-safe` | Rows where `sqli === "safe"` |
| Visible | `view` | Rows currently visible (respects filter + search) |

### Export formats

| Format | Output | MIME type |
|--------|--------|-----------|
| TXT | Numbered list with url, title, category, dork, sqli, waf, timestamp | `text/plain` |
| JSON | `{ meta: {...}, results: [...] }` | `application/json` |
| CSV | Headers: url, title, dork, category, ext, sqli, conf, waf, timestamp | `text/csv` |

**Filename pattern:** `{report_base}_links_{scope}_{ISO-timestamp}.{ext}`

Example: `report_20260314_links_sqli_vuln_2026-03-14T09-01-18.csv`

### Count badges

The `(N)` counts next to each label are updated live by `updateExportCounts()`, which is called when the panel opens and after every filter/search change.

---

## 📁 Export Files Panel

**Button:** `📁 FILES`
**Panel id:** `filesPanel`
**Min width:** 420px — `display: flex; flex-direction: column` (only when `.open`)
**Max height:** 520px with internal scroll on `.files-list`

Dedicated to non-webpage results that have a file extension and were analyzed (`--analyze`).

### File row structure

Each row in the scrollable list (`.file-row`) contains:

| Element | Description |
|---------|-------------|
| Checkbox `.file-chk` | `data-fidx` = index into `FILE_DATA` array |
| Status icon `✓` / `✗` | Color `#00aa44` (accessible) or `#663333` (not accessible); `title` = HTTP status code |
| File URL link | Truncated to 62 chars; opens in new tab |
| Category + extension | Shown below URL in dim text |
| Size | From `file_size` field; formatted by `_format_size()` |
| `⬇` icon `.file-dl` | Direct `download` link to the file URL |

Rows where `accessible=False` are rendered at `opacity: 0.45`.

### Bulk actions

| Button | Action |
|--------|--------|
| ALL | `selectAllFiles(true)` — checks all checkboxes |
| NONE | `selectAllFiles(false)` — unchecks all |
| LIST (TXT) | `exportSelectedFiles('list')` — exports selected as numbered text list |
| LIST (JSON) | `exportSelectedFiles('json')` — exports selected as JSON array |

**"Selected: N"** counter updates live via `updateSelCount()` on every checkbox `onchange`.

**Filename pattern:** `{report_base}_files_selected_{ISO-timestamp}.{txt|json}`

### Data source

The FILES panel reads from the embedded `FILE_DATA` JavaScript array. This is populated only for results where `category != "webpage"`. It requires `--analyze` to have been used during the scan to populate `file_size`, `accessible`, and `status_code` fields.

If no file results exist, the panel displays:
> *No file results in this report. Run with --analyze to detect accessible files.*

---

## Results Table

### Columns

| Column | CSS class | Width | Description |
|--------|-----------|-------|-------------|
| `#` | `c-num` | 36px fixed | Row number (1-indexed) |
| URL | `c-url` | `min-width: 180px`, fills remaining space | Truncated link (70 chars max) + `⬇` icon |
| Title | `c-title` | 14% / min 120px | Page title, truncated to 40 chars |
| Category | `c-cat` | 9% / min 90px | Color-coded category badge |
| SQLi Status | `c-sqli` | 10% / min 110px | Status with color coding |
| WAF | `c-waf` | 7% / min 70px | WAF name badge if detected |
| Size | `c-size` | 6% / min 54px | File size (from HEAD request) |

Table uses `table-layout: auto` — the browser distributes space based on actual content widths. This prevents excessive empty space between URL and Title columns.

### Row data attributes

Each `<tr>` carries these `data-*` attributes used by filter and search logic:

| Attribute | Content |
|-----------|---------|
| `data-category` | e.g. `webpage`, `documents`, `scripts` |
| `data-ext` | file extension, e.g. `.php`, `.pdf` |
| `data-sqli` | `critical`, `vuln`, `safe`, `untested` |
| `data-conf` | SQLi confidence: `critical`, `high`, `medium`, `low`, `none` |
| `data-idx` | 0-based index into `EXPORT_DATA` array |
| `data-url` | full URL (for search) |
| `data-title` | page title (for search) |
| `data-dork` | source dork (for search) |

### URL cell

```html
<div class="url-cell">
  <a href="{url}" target="_blank" title="{full_url}">{url_truncated}</a>
  <a class="dl-btn" href="{url}" download>⬇</a>
</div>
```

The `dl-btn` is a plain icon (no border, no background) — just a colored `⬇` character that triggers a browser download when clicked.

---

## Embedded Data

Two JavaScript constants are injected inline at the bottom of the `<body>`:

### `EXPORT_DATA`

Array of objects, one per result. Used by the Links panel.

```javascript
{
  url:       "https://example.com/page?id=1",
  title:     "Page Title",
  dork:      "site:example.com inurl:page",
  category:  "webpage",
  ext:       "",
  timestamp: "2026-03-14 09:01:18",
  sqli:      "vuln",          // "critical" | "vuln" | "safe" | "untested"
  conf:      "high",          // "critical" | "high" | "medium" | "low" | "none"
  waf:       "cloudflare"     // WAF name or ""
}
```

### `FILE_DATA`

Array of objects, one per non-webpage result. Used by the Files panel.

```javascript
{
  url:         "https://example.com/backup.sql",
  title:       "Database Backup",
  category:    "databases",
  ext:         ".sql",
  size:        2516582,          // bytes (null if unknown)
  size_str:    "2.4 MB",
  accessible:  true,
  status_code: 200,
  timestamp:   "2026-03-14 09:01:18"
}
```

### `REPORT_BASE`

Base filename string (no extension) used to prefix all export filenames:

```javascript
const REPORT_BASE = "report_20260314_090118";
```

---

## Responsive Breakpoints

| Breakpoint | Behaviour |
|-----------|-----------|
| `> 1100px` | Full layout, all columns visible with percentage widths |
| `≤ 1100px` | Column widths tighten slightly (fixed px values) |
| `≤ 860px` | Title (`c-title`) and WAF (`c-waf`) columns hidden via `display: none`; URL and SQLi Status always remain visible |

The table wraps in `.table-wrap { overflow-x: auto }` so on very narrow screens horizontal scrolling is always available as a last resort.

---

## Category Color Reference

| Category | Color | Extensions covered |
|----------|-------|--------------------|
| `documents` | `#ff6b6b` red | `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.odt`, `.ods` |
| `archives` | `#ffa500` orange | `.zip`, `.rar`, `.tar`, `.gz`, `.7z`, `.bz2` |
| `databases` | `#b47fff` purple | `.sql`, `.db`, `.sqlite`, `.mdb` |
| `backups` | `#e67e22` dark orange | `.bak`, `.backup`, `.old`, `.tmp` |
| `configs` | `#1abc9c` teal | `.conf`, `.config`, `.ini`, `.yaml`, `.yml`, `.json`, `.xml` |
| `scripts` | `#f1c40f` yellow | `.php`, `.asp`, `.aspx`, `.jsp`, `.sh`, `.bat`, `.ps1` |
| `credentials` | `#e74c3c` bright red | `.env`, `.git`, `.svn`, `.htpasswd` |
| `webpage` | `#7f8c8d` grey | (no file extension) |
| `other` | inherits | any extension not in the above lists |

---

## SQLi Status Reference

| `data-sqli` | Display text | CSS class | Color |
|-------------|-------------|-----------|-------|
| `critical` | `⚠ CRITICAL` | `.sqli-critical` | `#ff00ff` magenta + glow |
| `vuln` | `VULN (high/medium/low)` | `.sqli-vuln` | `#ff3333` red bold |
| `safe` | `SAFE` | `.sqli-safe` | `#00ff41` green |
| `untested` | `N/A` | `.sqli-untested` | `#444` dark grey |

---

## Data Structures

### Python → HTML data flow

```
DorkEyeEnhanced.results[]
        │
        ├─ export_rows[]  ──→  EXPORT_DATA  (Links panel)
        └─ file_rows[]    ──→  FILE_DATA    (Files panel)
                │
                └─ <tr data-*> attributes  (table rows + filter/search)
```

### Stats counter sources

```
self.stats["total_found"]       → TOTAL RESULTS card
self.stats["duplicates"]        → DUPLICATES FILTERED card
self.stats["sqli_vulnerable"]   → SQLI VULNERABILITIES card
self.stats["waf_detected"]      → WAF DETECTED card
time.time() - self.start_time   → EXECUTION TIME card
```

### Key JavaScript functions

| Function | Purpose |
|----------|---------|
| `applyFilter(btn)` | Applies top-level category filter |
| `applySubFilter(btn, groupId)` | Applies sub-category filter |
| `renderRows()` | Re-evaluates `.hidden` on all `<tr>` elements |
| `buildSubBadges()` | Counts rows per sub-filter, writes to badge spans |
| `updateInfoBar()` | Updates the "Showing N result(s)" status line |
| `toggleSearch()` | Opens/closes Search panel |
| `doSearch()` | Applies keyword filter to all visible rows |
| `applySearchToRow(row, q)` | Applies search to a single row, returns bool |
| `clearSearch()` | Clears search input, removes all `.srch-hidden` |
| `toggleScope(btn)` | Toggles a search scope button on/off |
| `toggleExportPanel()` | Opens/closes Links export panel |
| `doExport(fmt, scope)` | Triggers file download (txt/json/csv × scope) |
| `updateExportCounts()` | Updates (N) counts in Links panel |
| `toggleFilesPanel()` | Opens/closes Files panel |
| `updateSelCount()` | Updates "Selected: N" counter |
| `selectAllFiles(val)` | Checks/unchecks all file checkboxes |
| `exportSelectedFiles(fmt)` | Exports selected files as list (txt/json) |
| `closeAllPanels()` | Closes all three right-side panels |

---

*DorkEye v4.6 — For authorized security research only.*
