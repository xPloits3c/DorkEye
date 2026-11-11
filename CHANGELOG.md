# Changelog

All notable changes to DorkEye are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [5.2] - 2026-11-11

### Added
- **OSINT graph (`--osint`).** Passive, keyless recon on the hosts found by the
  dorks: Certificate Transparency (crt.sh), RDAP, DNS-over-HTTPS, Shodan
  InternetDB, reverse DNS, ASN / geo and the Wayback Machine. Three levels:
  `1` registry + subdomains + DNS, `2` (default) adds ports / CVEs / reverse DNS /
  ASN for every IP, `3` adds archived URLs and one HTTP request per host.
  Correlates shared-IP pivots, ASN clusters, IPs with known CVEs and telling
  hostnames, and extracts emails and phone numbers. Custom JSON chains and a
  standalone mode (`python Tools/osint.py --seed ...`).
- **New flags:** `--osint`, `--osint-seed`, `--osint-db`, `--osint-threads`,
  `--osint-max-nodes`, `--osint-export` (`csv`, `json`, `graphml`, `txt`).
  OSINT is also available from the wizard and the Web Console.
- **Unified tabbed report.** Dorks, Analyze, DBScan, Crawl and OSINT are collected
  into one HTML file, one tab per phase. With `-o` set to `.json` / `.csv` /
  `.txt`, that file keeps the results and the tabbed report is saved next to it
  as `.html`.
- **SQLite export** button in the HTML report (all results, every field).
- **Python 3.7 → 3.13 support.** `requirements.txt` uses per-version markers;
  on Python 3.7 / 3.8, where `ddgs` is not available, the dork search and the
  crawler automatically use the built-in lite DuckDuckGo client
  (`Devices/iOS/ddg_lite.py`).
- **README in 7 languages:** English, 简体中文, Español, Português (BR), Русский,
  日本語, Italiano (`Docs/languages/`).
- `Docs/osint.md` and an OSINT section in the README; OSINT, `--dbscan*`, `--ui`
  and `--port` added to the USAGE flag reference.

### Changed
- The HTML report engine moved from `dorkeye.py` to `Tools/report.py`
  (`dorkeye.py` is ~560 lines lighter).
- **Search Statistics** and **Results by Category** are printed as a single block
  with square tables.
- Removed the `Scanning results (files/SQLi/XSS)` line and the `SEARCH COMPLETE`
  banner; one save line per output file.
- MetaByte email / phone / IP / URL extractors are built into `dorkeye.py`.
- Claude workflow prompts aligned with `requirements.txt` and Python 3.7; the
  weekly audit also covers `report.py` and `osint.py`.
- `.gitignore` excludes `Dump/` and OSINT outputs (`*.sqlite`, `*.graphml`,
  `*_summary.txt`).

### Fixed
- `pip install -r requirements.txt` failed on Python 3.7 / 3.8.
- Every secret finding (analyzer and `SecretsAgent`) was reported as `HIGH`
  confidence. Each rule now has its own level: vendor-prefixed keys `HIGH`,
  `key=value` patterns `MEDIUM`, generic hashes / IPs `LOW`.
- The agents report header, footer and JSON `engine` field showed v4.8 / v5.0.
- Broken links in the device guides, INSTALL and the USAGE navigation bar.

### Security
- **XSS in the dork HTML report:** the Details popup rendered titles, snippets and
  dorks as HTML, a crafted URL could break out of the `data-ext` attribute, and
  `javascript:` links were clickable. Values are now escaped and links are
  limited to `http` / `https` / `ftp`.
- **XSS in the analysis and agents reports** (`--analyze`): every value is escaped
  in HTML and Markdown, links are limited to `http` / `https` with
  `rel="noopener noreferrer"`, and the HTML reports carry a strict
  Content-Security-Policy. Shared escaping helpers live in
  `Tools/dorkeye_patterns.py`.

## [5.1] - 2026-10-27

### Fixed
- **XSS detection runs independently.** A scan with `--xss` is no longer skipped
  when file analysis and SQLi are disabled — the XSS tests always run when
  requested.
- **Result count no longer capped at 50.** Dork searches now return the full
  requested set; `-c` values above 50 are honoured instead of stopping at the
  first page.
- **SQLi targets only parametric URLs.** URLs without GET parameters are skipped
  (nothing to inject into) and reported in the phase header, so the target count
  and the on-screen list are meaningful.
- **Checkpoints stored as JSON.** Session checkpoints use JSON instead of
  `pickle`, removing the code-execution risk of loading an untrusted checkpoint
  file. Checkpoints are now written to `Dump/.checkpoints/<id>.json`.
- **Thread-safe User-Agent rotation.** `UserAgentRotator` guards its index with
  a lock, so the producer thread can no longer skip or repeat a User-Agent.

### Changed — output & colours
- Clear separation between the two analysis stages: the inline per-result stage
  is now labelled **"Scanning results (files/SQLi/XSS)"** / **"Checking files"**,
  distinct from the post-search **agents analysis** pipeline.
- Every inline scan line is prefixed with a **timestamp**.
- The **SQLi** and **XSS** phases each open with their own section header
  (SQLi in red, XSS in yellow).
- **`WARNING` → `WARN`** (orange), used for both WAF detection and confirmed
  vulnerabilities.
- **Live scan** (direct `-u` / file `-f`): green `[INFO]` progress lines, and
  `[WARN]` lines on confirmed findings with the parameter and the confidence
  `(critical/high/medium/low)` in red. Every confirmed finding is marked
  `injectable`.
- **Direct-test results:** `SQLi Test Result` (red) and `XSS Test Result`
  (yellow) headers with "Test Result" in blue; both engines are scanned first
  and their results are printed together at the end. Long evidence (e.g. the
  time-based delay-scaling trace) wraps onto its own line.
- **End-of-run summary:** a `SEARCH COMPLETE` banner marks the end of the search
  phase, and the **Search Statistics** block is printed at the very end — after
  the agents / crawl / dbscan phases — so it is no longer mistaken for the end
  of the whole run.

### Changed — agents
- **PII**, **email** and **subdomain** agents emit a single status line while
  working plus one summary line, instead of one line per result.
- Removed duplicate pipeline summary lines and the duplicate report-save line;
  the saved report path is marked with `[✓]`.

### Internal
- `dorkeye_agents.py`: standard-library imports moved to module scope.
- Web console colouring updated for the `WARN` rename.
