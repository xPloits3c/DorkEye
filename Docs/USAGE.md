# 🐲 DorkEye — Advanced Usage (Flag-by-Flag)

This document explains **every available flag in detail**, including behavior, examples, and recommended combinations.

---

## 📌 Basic Syntax

```bash
python3 dorkeye.py [OPTIONS]
```

Minimal required flags:
- `-d`
- `--dg`
- `-o`

Everything else refines *how* the scan behaves.

---

## 🔹 `-d` — Dork Input

**Purpose:**  
Defines the search query or file containing multiple dorks.

### Accepted values
- Single dork string
- Text file (`.txt`) with one dork per line

### Examples
```bash
# Single dork
python3 dorkeye.py -d "inurl:admin" -o output.txt

# Multiple dorks
python3 dorkeye.py -d dorks.txt -o output.html
```

💡 Recommended for automation: **use files**.

---

## 🔹 `-o` — Output Directory

**Purpose:**  
Specifies where all results, reports, and exports are saved.

### Behavior
- Directory is created automatically
- Timestamped subfolders may be generated

```bash
python3 dorkeye.py -d dorks.txt -o scan_results.csv
```

---

## 🔹 `-c` — Result Cap

**Purpose:**  
Limits the maximum number of URLs per dork.

```bash
python3 dorkeye.py -d dorks.txt -c 100 -o output.txt
```

### Notes
- Higher values = slower scans
- Stealth mode recommended with `-c > 100`

---

## 🔹 `--stealth` — Stealth Mode

**Purpose:**  
Reduces detection and blocking risks.

### What it does
- Randomized delays
- Browser fingerprint rotation
- Rate-limit evasion logic

```bash
python3 dorkeye.py -d dorks.txt --stealth -o stealth_scan.txt
```

✅ Strongly recommended for:
- Sensitive targets
- Long scans
- SQLi testing

---

## 🔹 `--sqli` — SQL Injection Testing

**Purpose:**  
Automatically tests discovered parameters for SQL Injection.

### SQLi Detection Techniques
- Strict URL pre-filtering (realistic SQLi candidates only)
- Lightweight parameter influence probing
- Error-based detection (DB-specific signatures)
- Boolean-based blind (response differential stability analysis)
- Time-based blind (low-impact controlled execution)
- Deterministic confidence scoring (NONE / LOW / MEDIUM / HIGH / CRITICAL)
- False-positive reduction through similarity thresholding

```bash
python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o sqli_scan.html
```

### --dg | Dork Generator Layer Purpose:
# Generates structured Google dorks using a modular YAML template engine.
# The Dork Generator allows controlled, scalable dork creation without hardcoded patterns.
# Read the FULL Dorks Generator System Bellow:
[![DORKS_GENERATOR](https://img.shields.io/badge/FULL%20DG-USAGE-blue?style=for-the-badge)](https://xploits3c.github.io/DorkEye/Docs/DORK_GENERATOR.md)
It uses:
- dork_generator.py
- dorks_templates.yaml
# Generator Capabilities
# Template-based dork generation
Dynamic variable expansion:
- {domain}
- {param}
- {extension}
# Category-based generation:
- sqli
- backups
- sensitive
- admin
Mode control:
- soft
- medium
- aggressive
```bash
--dg
--dg=<category>
--mode
--mode=<soft|medium|aggressive>
```

# Example — Generate SQLi Dorks
```bash
python3 dorkeye.py --dg=sqli --mode=aggressive
```

Example — Generate All Categories (default soft mode)
```bash
python3 dorkeye.py --dg
```

Example — Generate & Immediately Scan
```bash
python3 dorkeye.py --dg=sqli --mode=aggressive --sqli -o report.html
```

### 1️⃣ GENERATOR LAYER – ALL VALID VARIATIONS
- Basic Activation
```bash
python dorkeye.py --dg
```
✔ Generates all categories
✔ Mode = soft (default)

- Specific Category
```bash
python dorkeye.py --dg=sqli
python dorkeye.py --dg=backups
python dorkeye.py --dg=sensitive
python dorkeye.py --dg=admin
```
✔ Mode = soft (default)

Mode Only (Without Value)
```bash
python dorkeye.py --dg --mode
```
✔ Mode = soft

🔹 Explicit Mode
```bash
python dorkeye.py --dg --mode=soft
python dorkeye.py --dg --mode=medium
python dorkeye.py --dg --mode=aggressive
```

🔹 Category + Mode
```bash
python dorkeye.py --dg=sqli --mode=aggressive
python dorkeye.py --dg=admin --mode=medium
python dorkeye.py --dg=backups --mode=soft
python dorkeye.py --dg=sensitive --mode=aggressive
```

### 2️⃣ GENERATOR + DETECTION

Here the architectural separation becomes important:
```bash
--dg=sqli → Dork Generator category
--sqli → SQLi detection engine
```

🔹 Generator + SQL Detection
```bash
python dorkeye.py --dg=sqli --sqli
```

🔹 Generator + Aggressive Mode + SQL Detection
```bash
python dorkeye.py --dg=sqli --mode=aggressive --sqli
```

🔹 Generator + Stealth Mode
```bash
python dorkeye.py --dg=sqli --stealth
```

🔹 Generator + Detection + Stealth + Output
```bash
python dorkeye.py --dg --mode=aggressive --sqli --stealth -o report.html
python dorkeye.py --dg=sqli --mode=aggressive --templates=dorks_templates.yaml --sqli --stealth -o report.html
```

### 3️⃣ STANDARD MODE (Without Generator)

Nothing changes here.
```bash
python dorkeye.py -d "inurl:.php?id=" --sqli
python dorkeye.py -d dorks.txt --stealth
python dorkeye.py -d dorks.txt -c 100 -o results.json
```

### 4️⃣ ALL COMPATIBLE COMBINATIONS
🔹 You can combine with:
```bash
--stealth
--sqli
--no-analyze
--no-fingerprint
--blacklist .pdf .doc
--whitelist .sql .env
-c 100
-o output.html
--config custom.yaml
```

🔹 Full Example:
```bash
python dorkeye.py \
  --dg=sensitive \
  --mode=aggressive \
  --sqli \
  --stealth \
  --blacklist .pdf .doc \
  -c 80 \
  -o full_report.html
```

### Output
- Vulnerability type
- Confidence score
- Tested payload category
---

## 🔹 `--no-analyze` — Disable File Analysis

**Purpose:**  
Skips HEAD analysis for faster scans.

```bash
python3 dorkeye.py -d dorks.txt --no-analyze -o fast_scan
```

### Trade-off
| Mode | Speed | Metadata |
|----|------|----------|
| Default | Medium | Yes |
| `--no-analyze` | Fast | No |

---

## 🔹 `--whitelist` — Extension Whitelist

**Purpose:**  
Only includes specific file types.

```bash
python3 dorkeye.py -d "site:target.com" --whitelist .pdf .xls .docx -o documents
```

✔ Ideal for document harvesting  
❌ All other extensions ignored

---

## 🔹 `--blacklist` — Extension Blacklist

**Purpose:**  
Excludes unwanted file types.

```bash
python3 dorkeye.py -d "site:target.com" --blacklist .jpg .png .gif -o no_images
```

✔ Reduces noise  
✔ Faster analysis

---

## 🔹 `--config` — Custom Configuration File

**Purpose:**  
Loads a YAML or JSON configuration.

```bash
python3 dorkeye.py -d dorks.txt --config custom_config.yaml -o scan
```

Use for:
- Custom delays
- Headers
- Timeouts
- SQLi thresholds

📄 See `CONFIG.md`.

---

## 🔹 `--create-config` — Generate Default Config

**Purpose:**  
Creates a base configuration file.

```bash
python3 dorkeye.py --create-config
```

Use as:
- Starting template
- Backup of defaults

---

## 🔗 Recommended Combinations

### Stealth + SQLi (Professional Mode)
```bash
python3 dorkeye.py -d dorks.txt --stealth --sqli -c 150 -o pro_scan
```

### Fast Recon
```bash
python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o recon
```

### Documents Only
```bash
python3 dorkeye.py -d "site:.gov" --whitelist .pdf .docx -o docs
```

---

## ❌ Invalid / Dangerous Combos

| Combination | Reason |
|-----------|--------|
| `--sqli` without permission | Legal risk |
| High `-c` without `--stealth` | IP ban |
| `--no-analyze` for sensitive data | Loss of insight |

---

## ⚠️ Legal Reminder

Use **only** on:
- Authorized targets
- Public data
- Educational / research environments

🐲 Power without control is noise.  
Stay precise. Stay ethical.
