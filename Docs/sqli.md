# SQL Injection Detection — DorkEye v4.8

DorkEye includes a built-in multi-method SQL injection engine that works on any URL with query parameters — no external tools required.

---

## Enable SQLi Testing

### During a dork search

```bash
python dorkeye.py -d "inurl:.php?id=" --sqli -o results.json
python dorkeye.py --dg=sqli --mode=medium --sqli --stealth -o results.json
```

### Direct test on a single URL (v4.8)

```bash
# SQLi auto-enabled — no --sqli flag needed
python dorkeye.py -u "https://example.com/page.php?id=1"

# With stealth and output
python dorkeye.py -u "https://example.com/page.php?id=1" --sqli --stealth -o result.json
```

### Re-test a saved results file (v4.8)

```bash
python dorkeye.py -f Dump/results.json --sqli -o retest.json
```

---

## Detection Methods

DorkEye runs four complementary methods on every URL parameter, in this order:

### 1. Error-based

Injects payloads designed to trigger SQL error signatures in the response body. Supports:

| Database | Signatures detected |
|----------|-------------------|
| MySQL / MariaDB | `Warning: mysql_fetch`, `You have an error in your SQL syntax`, `extractvalue` errors |
| PostgreSQL | `pg_query()`, `unterminated quoted string`, `invalid input syntax` |
| Microsoft SQL Server | `Unclosed quotation mark`, `ODBC SQL Server Driver`, `CAST(...)` errors |
| Oracle | `ORA-01756`, `quoted string not properly terminated` |
| SQLite | `SQLite3::query()`, `sqlite3.OperationalError` |

### 2. UNION-based

Probes column count via `UNION SELECT NULL` sequences and detects column mismatch errors or abnormal response size changes when the UNION is processed by the server.

### 3. Boolean blind

Sends true/false condition pairs and compares response sizes:

```
1' AND '1'='1   →  true condition
1' AND '1'='2   →  false condition
```

If median response sizes differ significantly (>15%) with low internal variance, the parameter is flagged.

### 4. Time-based blind

Injects `SLEEP(5)` / `WAITFOR DELAY` payloads and measures actual elapsed time against a measured baseline. Threshold = baseline + sleep delay + safety margin.

---

## Parameter Prioritization

DorkEye does not test all parameters in random order. Parameters are ranked:

| Priority | Criteria |
|----------|----------|
| High | Numeric value (`?id=3`) or known high-risk name (`id`, `page`, `cat`, `user`) |
| Medium | Known medium-risk names (`search`, `q`, `query`, `lang`, `view`) |
| Low | Everything else |

High-priority parameters are tested first. If a CRITICAL vulnerability is found in the first parameter, testing stops immediately.

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| `critical` | Multiple methods confirmed — error-based + time-based or score ≥ 5 |
| `high` | Strong single method — error signature matched, score ≥ 3 |
| `medium` | Behavioral anomaly — UNION col mismatch or boolean differential |
| `low` | Weak signal — minor response variation |

---

## Terminal Output (v4.8 verbose)

When a URL is found vulnerable, DorkEye prints the method and evidence immediately:

```
[!] Potential SQLi found (critical): https://target.com/product.php?id=7
    ↳ method: error_based [param: id]  evidence: MYSQL error signature matched: extractvalue(0,...
    ↳ method: time_based_blind          evidence: SLEEP(5) triggered: elapsed=5.3s > threshold=5.2s
```

Same output appears during `-u` direct URL tests.

---

## WAF Detection

Before and during testing, DorkEye checks for WAF signatures in:
- Response header keys and values
- Response body (first 2000 chars)
- HTTP status codes (403, 406, 429 with short body)

Detected WAFs include: Cloudflare, Akamai, AWS WAF, F5 BIG-IP, Sucuri, Imperva, Barracuda, Fortinet, Wordfence, mod_security, and others. When a WAF is detected, aggressive payloads are skipped for that URL.

---

## SQLi in the HTML Report

Vulnerable URLs are shown with:
- Color-coded badge: 🟣 CRITICAL / 🔴 VULN / 🟢 SAFE / ⬛ UNTESTED
- WAF indicator in the WAF column
- ⓘ detail popup with method, payload evidence, and confidence level

In the JSON output:

```json
{
  "sqli_test": {
    "tested": true,
    "vulnerable": true,
    "overall_confidence": "critical",
    "waf_detected": null,
    "message": "Tested 3 parameter(s)",
    "tests": [
      {
        "method": "error_based",
        "vulnerable": true,
        "confidence": "high",
        "evidence": ["MYSQL error signature matched: extractvalue(0,concat(...)"]
      },
      {
        "method": "time_based_blind",
        "vulnerable": true,
        "confidence": "high",
        "evidence": ["SLEEP(5) triggered: elapsed=5.3s >= threshold=5.2s"]
      }
    ]
  }
}
```

---

## Stealth Mode

```bash
python dorkeye.py -d dorks.txt --sqli --stealth -o results.json
```

With `--stealth`:
- Random delays of 3–6s between parameters (vs 0.5s normally)
- Random delays of 1.5–3s between payloads within error-based testing
- Baseline measurements use slower timing
- Fingerprint rotation uses more conservative browser profiles
