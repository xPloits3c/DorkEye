# 🐲 DorkEye — Advanced Usage (Flag-by-Flag)

> 🔥 *I don't hack systems. I expose their secrets.*

This document explains **every available flag in detail**, including behavior, examples, and recommended combinations.

---

## 📌 Basic Syntax

```bash
python3 dorkeye.py [OPTIONS]
```

Minimal required flags:
- `-d`
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
python3 dorkeye.py -d "inurl:admin" -o output

# Multiple dorks
python3 dorkeye.py -d dorks.txt -o output
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
python3 dorkeye.py -d dorks.txt -o scan_results
```

---

## 🔹 `-c` — Result Cap

**Purpose:**  
Limits the maximum number of URLs per dork.

```bash
python3 dorkeye.py -d dorks.txt -c 100 -o output
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
python3 dorkeye.py -d dorks.txt --stealth -o stealth_scan
```

✅ Strongly recommended for:
- Sensitive targets
- Long scans
- SQLi testing

---

## 🔹 `--sqli` — SQL Injection Testing

**Purpose:**  
Automatically tests discovered parameters for SQL Injection.

### Techniques
- Error-based
- Boolean-based blind
- Time-based blind

```bash
python3 dorkeye.py -d "site:example.com .php?id=" --sqli -o sqli_scan
```

### Output
- Vulnerability type
- Confidence score
- Tested payload category

⚠️ Always ensure **authorization**.

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
