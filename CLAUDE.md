# CLAUDE.md — DorkEye Codebase Guide

This file provides essential context for AI assistants working on the DorkEye codebase.

---

## Project Overview

**DorkEye** is a Python-based OSINT/security research tool for Google-style dorking via DuckDuckGo. It combines automated dork generation, multi-engine search, HTTP fingerprinting, and an autonomous 10-step analysis pipeline to surface exposed files, secrets, PII, SQLi vulnerabilities, and technology information.

- **Version:** 4.8
- **License:** MIT (2026 xPloits3c)
- **Python:** 3.9+
- **No LLM dependencies** — all analysis is regex/heuristic-based

---

## Repository Layout

```
DorkEye/
├── dorkeye.py                  # Main CLI entry point (~4,200 lines)
├── requirements.txt            # Python dependencies
├── http_fingerprints.json      # 22 browser/OS HTTP fingerprint profiles
├── README.md
├── Tools/                      # Analysis subpackage
│   ├── dork_generator.py       # YAML template engine for dork generation
│   ├── dorkeye_agents.py       # 10-step autonomous analysis pipeline (~2,500 lines)
│   ├── dorkeye_analyze.py      # Standalone URL analyzer CLI (~870 lines)
│   └── dorkeye_patterns.py     # Shared regex patterns and detection rules (~325 lines)
├── Templates/                  # YAML dork templates
│   ├── dorks_templates.yaml    # General-purpose templates
│   ├── sqli.yaml               # SQL injection dorks
│   ├── intel_dorks.yaml        # Intelligence gathering
│   ├── osint.yaml              # OSINT dorks
│   ├── epstein_files.yaml
│   └── example.yaml
├── Docs/                       # Full documentation (15+ guides)
│   ├── USAGE.md
│   ├── cli.md                  # All 26 CLI flags
│   ├── agents.md               # Pipeline step details
│   ├── sqli.md
│   ├── crawler.md
│   ├── dork_generator.md
│   ├── fingerprinting.md
│   ├── output_formats.md
│   └── Dorks/                  # Dork collections (170KB+)
└── .github/                    # Issue templates, workflows, code of conduct
    └── workflows/crda.yml      # Red Hat CRDA dependency security scan
```

---

## Key Classes (dorkeye.py)

| Class | Location | Purpose |
|---|---|---|
| `DorkEyeEnhanced` | line ~1734 | Main search engine orchestrator |
| `SQLiDetector` | line ~641 | SQL injection detection (4 methods) |
| `HTTPFingerprintRotator` | line ~368 | Rotates browser fingerprint profiles |
| `CircuitBreaker` | line ~475 | Rate-limit/IP-block protection |
| `UserAgentRotator` | line ~1589 | Cycles User-Agent strings |
| `FileAnalyzer` | line ~1611 | URL metadata and file-type classification |
| `SQLiConfidence` | — | Enum: `NONE / LOW / MEDIUM / HIGH / CRITICAL` |

---

## Tools Subpackage

### `dorkeye_patterns.py`
Single source of truth for all detection patterns. Import from here rather than defining patterns elsewhere:
- 42 secret/credential patterns
- 11 PII patterns (email, phone, IBAN, SSN, credit cards, passports, IPs)
- 28 triage scoring rules
- 35+ technology fingerprints

### `dorkeye_agents.py`
Implements 10 autonomous agents that run sequentially on each result URL:
1. **Triage** — prioritizes URLs by score
2. **Fetch** — HTTP retrieval with fingerprint rotation
3. **HeaderIntel** — server header analysis
4. **TechFingerprint** — CMS/framework detection
5. **Secrets** — credential/key extraction
6. **PII** — personal data detection
7. **Email** — email harvesting
8. **Subdomain** — subdomain discovery
9. **Report** — result aggregation
10. **Crawler** — adaptive recursive crawling

### `dork_generator.py`
YAML-driven template engine. Templates live in `Templates/`. Supports variable expansion, `--list-templates` for discovery, and `--mode` (default/aggressive/stealth).

---

## Technology Stack

- **Runtime:** Python 3.9+
- **Search:** `ddgs>=4.0.0` (DuckDuckGo)
- **HTTP:** `requests>=2.32.0` + `urllib3` with retry logic
- **Terminal UI:** `rich==13.7.0`
- **Config/Templates:** `PyYAML==6.0.1`
- **Concurrency:** `threading` + `queue` (standard library)
- **No AI/ML dependencies** — detection is pure regex + heuristics

---

## Running the Tool

```bash
# Install
python -m venv dorkeye_env
source dorkeye_env/bin/activate
pip install -r requirements.txt

# Interactive wizard
python dorkeye.py --wizard

# Direct dork search
python dorkeye.py -d "site:example.com filetype:pdf" -o results.json

# Dork generation + search
python dorkeye.py --dg=sqli --mode=aggressive -o out.html

# Standalone analysis (post-search)
python Tools/dorkeye_analyze.py results.json

# List available templates
python dorkeye.py --list-templates
```

---

## CLI Flags (summary of 26 flags)

See `Docs/cli.md` for the full reference. Key flags:

| Flag | Description |
|---|---|
| `-d / --dork` | Dork string to search |
| `-o / --output` | Output file (format inferred from extension: `.json`, `.csv`, `.html`, `.txt`) |
| `--wizard` | Interactive menu-driven mode |
| `--dg=<template>` | Use a YAML template for dork generation |
| `--mode=<mode>` | `default` / `aggressive` / `stealth` |
| `--sqli` | Enable SQL injection testing |
| `--crawl` | Enable adaptive recursive crawling |
| `--agents` | Run the 10-step analysis pipeline |
| `--config <file>` | Load settings from JSON/YAML file |
| `--create-config` | Generate a sample config file |
| `--list-templates` | List available YAML templates |
| `--max-results <n>` | Cap on number of results |
| `--threads <n>` | Concurrent analysis threads |
| `--delay <n>` | Request delay in seconds (stealth) |
| `--timeout <n>` | HTTP request timeout |
| `--no-verify` | Disable SSL verification |
| `--fingerprint` | Show HTTP fingerprint profile in use |

---

## Output Formats

Output format is determined by the file extension passed to `-o`:

| Extension | Format | Notes |
|---|---|---|
| `.html` | Interactive dark-theme report | Filterable, sortable |
| `.json` | Structured JSON | Full metadata |
| `.csv` | Spreadsheet-friendly | Flat fields |
| `.txt` | Plain URL list | Minimal |

---

## Detection Capabilities

**Secrets (42 patterns):** API keys, OAuth tokens, AWS/GCP/Azure credentials, JWT, private keys, DB URIs, password fields, hashes.

**PII (11 patterns):** Email, phone, IBAN, fiscal codes, credit cards (Luhn-validated), SSN, date-of-birth, passport numbers, IP addresses.

**SQLi (4 methods):** Error-based, UNION-based, boolean blind, time-based.

**Tech Detection (35+):** CMS (WordPress, Drupal, Joomla), frameworks (Laravel, Django, Rails), server versions, JS libraries.

**File Categories (7):** Documents, archives, databases, config files, scripts, media, data files.

---

## HTTP Fingerprinting

`http_fingerprints.json` defines 22 browser/OS profiles (Chrome/Windows, Firefox/Linux, Safari/iOS, Edge, mobile, etc.). `HTTPFingerprintRotator` cycles through these to reduce detection and rate-limiting. Profiles include User-Agent, Accept headers, Accept-Language, and connection settings.

---

## Code Conventions

1. **Pattern centralization:** All detection regex lives in `dorkeye_patterns.py`. Never define new patterns in other files.
2. **Type hints:** Use `from typing import List, Dict, Optional, Tuple` throughout.
3. **Dataclasses:** Use `@dataclass` for structured result/config objects.
4. **Enums:** Use `Enum` for multi-state values (e.g., `SQLiConfidence`).
5. **Rich output:** Use `rich.console.Console` for all terminal output — no raw `print()`.
6. **Error handling:** Wrap network calls in `try/except` with graceful degradation.
7. **SSL:** `verify=False` is intentional for security testing; suppress `urllib3` warnings explicitly.
8. **No global state:** Pass config/options through function arguments or class constructors.
9. **Docstrings:** All public classes and functions should have docstrings.
10. **Logging:** Use `rich` Console rather than Python `logging` module.

---

## Adding New Features

### New detection pattern
Add to `Tools/dorkeye_patterns.py` in the appropriate section (secrets, PII, tech, triage). Document the pattern with an inline comment.

### New CLI flag
1. Add `argparse` entry in `dorkeye.py` `parse_args()` / argument setup block.
2. Document in `Docs/cli.md`.
3. Wire through `DorkEyeEnhanced` config.

### New YAML template
Create `Templates/<name>.yaml` following the structure in `Templates/example.yaml`. Templates are auto-discovered via `--list-templates`.

### New agent step
Add a method to the agent pipeline in `Tools/dorkeye_agents.py`. Register it in the 10-step execution sequence and document in `Docs/agents.md`.

### New output format
Add a format handler in the output section of `dorkeye.py` and update `Docs/output_formats.md`.

---

## Testing

There is no automated test suite. Manual testing approach:

```bash
# Verify config generation
python dorkeye.py --create-config

# Run with a benign dork
python dorkeye.py -d "site:example.com" --max-results 5 -o test.json

# Test analysis pipeline separately
python Tools/dorkeye_analyze.py test.json

# Validate template expansion
python dorkeye.py --dg=example --list-templates
```

When adding new detection patterns, manually test with sample strings before committing.

---

## CI/CD

`.github/workflows/crda.yml` runs Red Hat CodeReady Dependency Analysis on every push and pull request to scan `requirements.txt` for known vulnerabilities. No build step is needed (pure Python). The workflow can also be triggered manually via `workflow_dispatch`.

---

## Security Considerations

- This tool is designed for **authorized security testing and OSINT research only**.
- SSL verification is disabled by default for testing flexibility — never enable in production environments.
- Stealth mode (`--mode=stealth`) adds randomized delays; use it to avoid unintentional service disruption.
- Never commit output files containing real credentials, PII, or sensitive findings.
- `.gitignore` already excludes common output file patterns (`*.json`, `*.html` output, `*.csv`, etc.).

---

## Useful References

- Full CLI reference: `Docs/cli.md`
- Analysis pipeline details: `Docs/agents.md`
- Template syntax: `Docs/dork_generator.md`
- Installation: `Docs/INSTALL.md`
- Usage examples: `Docs/USAGE.md`
- HTML report structure: `Docs/REPORT_HTML.md`
