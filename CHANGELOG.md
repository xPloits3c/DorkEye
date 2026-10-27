# Changelog

All notable changes to DorkEye are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

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
