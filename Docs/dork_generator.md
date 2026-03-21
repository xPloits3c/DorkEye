# Dork Generator — DorkEye v4.8

The Dork Generator produces structured Google dorks automatically from YAML template files. Instead of writing dorks manually, you define variables and templates once and let DorkEye generate every combination.

---

## Quick Start

```bash
# All categories, soft mode
python dorkeye.py --dg=all -o results.html

# Specific category, medium mode
python dorkeye.py --dg=sqli --mode=medium -o results.json

# Aggressive mode, high combination limit
python dorkeye.py --dg=all --mode=aggressive --dg-max 10000 -o big.json
```

---

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--dg[=CATEGORY]` | `all` | Category to generate; omit value = `all` |
| `--mode MODE` | `soft` | `soft` / `medium` / `aggressive` |
| `--dg-max N` | `800` | Max combinations generated per template |
| `--templates=FILE` | `dorks_templates.yaml` | Template file in `Templates/`; `all` = every YAML |

> Always use `--templates=filename.yaml` with `=` — never with a space.

---

## Generation Modes

| Mode | Dorks included | Use case |
|------|---------------|----------|
| `soft` | Low-risk, minimal footprint | Passive recon, first pass |
| `medium` | Soft + broader coverage | Standard assessments |
| `aggressive` | All templates — maximum combinations | Deep enumeration |

Each mode is a superset of the previous: `aggressive` includes everything in `medium`, which includes everything in `soft`.

---

## Template Structure

Templates are YAML files in the `Templates/` folder. DorkEye ships with `dorks_templates.yaml` and `dorks_templates_research.yaml`.

### Basic structure

```yaml
variables:
  domain:
    - "example.com"
    - "target.org"
  ext:
    - "php"
    - "asp"

templates:
  sqli:
    dorks:
      soft:
        - 'site:{domain} inurl:.{ext}?id='
        - 'site:{domain} inurl:page.{ext}?cat='
      medium:
        - 'site:{domain} inurl:.{ext}?id= intext:error'
      aggressive:
        - 'site:{domain} inurl:.{ext}?id= "mysql_fetch"'

  backups:
    dorks:
      soft:
        - 'site:{domain} filetype:bak'
      medium:
        - 'site:{domain} filetype:bak OR filetype:backup'
```

### Variable interpolation

Any `{variable_name}` placeholder in a template is replaced with every value defined in `variables`. For `{domain}` with 3 values and `{ext}` with 4 values, one template produces 12 dorks.

### Flat (legacy) structure

```yaml
templates:
  admin:
    mode: soft
    dorks:
      - 'inurl:admin intitle:login'
      - 'inurl:administrator'
```

Both structures are supported in the same file.

---

## Available Categories (default template)

| Category | Focus |
|----------|-------|
| `sqli` | Endpoints likely vulnerable to SQL injection |
| `backups` | Backup files, dumps, archives left exposed |
| `admin` | Admin and management panels |
| `credentials` | `.env`, `.git`, `.htpasswd`, key files |
| `configs` | Configuration files (YAML, XML, INI, conf) |
| `exposed` | Directory listings, open indexes |

Run `--wizard` → option 2 to see the exact categories available in each template at runtime.

---

## Combination Limit

DorkEye caps combinations per template at `--dg-max` (default `800`). When the theoretical total exceeds the cap, it samples randomly without replacement, so you always get a representative spread rather than just the first N combinations.

```bash
# Default cap
python dorkeye.py --dg=all

# Raise the cap for exhaustive runs
python dorkeye.py --dg=all --mode=aggressive --dg-max 10000 -o big.json
```

---

## Combining with Other Features

```bash
# Generator + SQLi testing
python dorkeye.py --dg=sqli --mode=medium --sqli --stealth -o results.json

# Generator + analysis pipeline
python dorkeye.py --dg=all --analyze --analyze-fetch -o results.json

# Generator + adaptive crawl
python dorkeye.py --dg=sqli --crawl --crawl-rounds 5 -o crawl.json

# Full pipeline
python dorkeye.py --dg=sqli --mode=aggressive --dg-max 5000 \
  --sqli --stealth \
  --analyze --analyze-fetch --analyze-fetch-max 50 \
  --crawl --crawl-rounds 6 --crawl-stealth \
  -o results.json

# Custom template
python dorkeye.py --dg=backups --templates=dorks_templates_research.yaml -o results.json

# All template files
python dorkeye.py --dg=all --templates=all -o results.json
```
