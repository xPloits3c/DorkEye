# CLI Reference — DorkEye v4.8

> All 26 flags, all accepted values, all combinations.

---

## Input Sources — one required, mutually exclusive

| Flag | Type | Description |
|------|------|-------------|
| `--wizard` | bool | Launch the interactive guided session |
| `-d DORK`, `--dork` | str | Single dork string or path to `.txt` file (one dork per line) |
| `-u URL`, `--url` | str | Single URL to test directly for SQL injection |
| `-f FILE`, `--file` | str | Load saved DorkEye results (`.json` or `.txt`) for re-processing |
| `--dg[=CATEGORY]` | str | Activate Dork Generator; optional value = category (`all` if omitted) |

## Output

| Flag | Default | Description |
|------|---------|-------------|
| `-o FILE`, `--output` | `report_TIMESTAMP.html` | Output file — extension sets format |
| `-c N`, `--count` | `50` | Results per dork from DuckDuckGo |

## Configuration

| Flag | Description |
|------|-------------|
| `--config FILE` | Custom YAML or JSON configuration file |
| `--create-config` | Generate a sample config file and exit |

## Scan Behaviour

| Flag | Description |
|------|-------------|
| `--sqli` | Enable SQL injection detection |
| `--stealth` | Stealth mode — longer delays, safer fingerprinting |
| `--no-analyze` | Skip HEAD requests on found URLs (faster) |
| `--no-fingerprint` | Disable HTTP fingerprint rotation |
| `--blacklist EXT…` | Exclude these file extensions |
| `--whitelist EXT…` | Include only these file extensions |

## Dork Generator

| Flag | Default | Description |
|------|---------|-------------|
| `--dg[=CATEGORY]` | `all` | Category to generate |
| `--dg-max N` | `800` | Max dork combinations per template |
| `--mode MODE` | `soft` | `soft` / `medium` / `aggressive` |
| `--templates=FILE` | `dorks_templates.yaml` | Template file in `Templates/`; `all` = every YAML |

## Agents v3.0 — Integrated Analysis

| Flag | Default | Description |
|------|---------|-------------|
| `--analyze` | off | Run post-search analysis pipeline |
| `--analyze-fetch` | off | Download page content for HIGH/CRITICAL results |
| `--analyze-fetch-max N` | `20` | Max pages to download |
| `--analyze-fmt FORMAT` | `html` | `html` / `md` / `json` / `txt` |
| `--analyze-out FILE` | auto | Path for the analysis report |

## Adaptive Crawl

| Flag | Default | Description |
|------|---------|-------------|
| `--crawl` | off | Enable adaptive recursive crawl |
| `--crawl-rounds N` | `4` | Max crawl rounds |
| `--crawl-max N` | `300` | Total result limit across all rounds |
| `--crawl-per-dork N` | `20` | DuckDuckGo results per dork per round |
| `--crawl-stealth` | off | Longer delays between crawl searches |
| `--crawl-report` | off | Generate a dedicated crawl HTML report |
| `--crawl-out FILE` | auto | Path for the crawl report |

---

## Accepted Values

### `--mode`

| Value | Dorks included | Footprint |
|-------|---------------|-----------|
| `soft` | Low-risk dorks only | Minimal |
| `medium` | Soft + medium coverage | Moderate |
| `aggressive` | All dorks — maximum coverage | Maximum |

### `-o` / `--output` extensions

| Extension | Output type |
|-----------|-------------|
| `.html` | Interactive dark-theme HTML report with filter bar, search, panels, ⓘ popup |
| `.json` | Structured JSON — also triggers automatic analysis prompt |
| `.csv` | Spreadsheet-friendly, all metadata columns |
| `.txt` | Plain numbered list |

### `--analyze-fmt`

| Value | Output |
|-------|--------|
| `html` | Full dark-theme HTML with all Agents v3.0 sections |
| `md` | Markdown with tables |
| `json` | Structured JSON with pii, emails, subdomains, cve_dorks keys |
| `txt` | Plain text |

---

## Compatibility Rules

**Mutually exclusive inputs:**
```
--wizard  ←→  -d  ←→  -u  ←→  -f  ←→  --dg  ←→  --create-config
```

**`-u` constraints:** not compatible with `--analyze`, `--crawl`, `-d`, `-f`, `--dg`. SQLi is auto-enabled even without `--sqli`. Stops after the test.

**`--dg` constraints:** one value only — `--dg=sqli` ✓, two `--dg` flags ✗. Use `--templates=FILE` syntax (with `=`, no space). `-c` / `--count` has no effect with `--dg`.

**`--analyze-*` constraints:** `--analyze-fetch-max` requires `--analyze-fetch`. `--analyze-out` requires `--analyze` or `.json` output.

**`.json` output special behaviour:** triggers interactive prompt *"Vuoi analizzare i risultati? [y/N]"*. Use `--analyze` to skip the prompt and force yes.

---

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
python dorkeye.py --dg=all --mode=aggressive --dg-max 10000 -o results.json
python dorkeye.py --dg=sqli --sqli --analyze --analyze-fetch -o results.json

# ── DIRECT URL TEST ───────────────────────────────────────────────────────
python dorkeye.py -u "https://target.com/page.php?id=1"
python dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o out.json

# ── FILE RE-PROCESSING ────────────────────────────────────────────────────
python dorkeye.py -f Dump/results.json --sqli -o retest.json
python dorkeye.py -f Dump/results.json --analyze --analyze-fetch -o reanalysis.json
python dorkeye.py -f Dump/results.json --sqli --analyze --crawl -o full.json

# ── STANDALONE AGENTS ─────────────────────────────────────────────────────
python dorkeye_agents.py Dump/results.json --analyze-fetch --analyze-fmt html
```
