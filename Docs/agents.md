# AI Agents v3.1
# DorkEye Project

The Agents pipeline runs automatically after a dork search when `--analyze` is active (or when the output file is `.json`). It requires no external AI — every step uses regex, heuristics, and structural analysis only.

---

## Activate

```bash
# Automatic (output .json triggers a prompt)
python dorkeye.py -d "site:example.com" -o results.json

# Explicit
python dorkeye.py -d "site:example.com" -o results.json --analyze

# With page content download
python dorkeye.py -d "site:example.com" -o results.json --analyze --analyze-fetch

# Standalone on saved results
python dorkeye_agents.py Dump/results.json --analyze-fetch --analyze-fmt html
```

---

## Pipeline — 11 Steps

| Step | Agent | Input | Output |
|------|-------|-------|--------|
| 1 | **TriageAgent** | All results | `triage_score`, `triage_label`, `triage_reason` per result |
| 2 | **PageFetchAgent** | HIGH / CRITICAL results | `page_content`, `response_headers`, `fetch_status` |
| 3 | **SecurityAgent** *(new v3.1)* | `page_content` + `response_headers` + URL | `security_verdict` dict with `threat_level`, `threat_score`, `indicators` |
| 4 | **HeaderIntelAgent** | `response_headers` | `header_intel` (info leaks, missing headers, outdated versions) |
| 5 | **TechFingerprintAgent** | `page_content` + headers + URL | `tech_fingerprint` (techs, versions, CVE dorks) |
| 6 | **SecretsAgent** | `page_content` + snippet | `secrets` list with type, value, severity, context |
| 7 | **PiiDetectorAgent** | `page_content` + snippet | `pii_found` list with type, censored value, context |
| 8 | **EmailHarvesterAgent** | `page_content` + snippet | `emails_found` list, global dedup |
| 9 | **SubdomainHarvesterAgent** | All text fields | `subdomains` list per result, global map |
| 10 | **LLM Analysis** | All triaged results | `analysis` dict (optional — requires `dorkeye_llm_plugin.py`) |
| 11 | **ReportAgent** | Everything above | HTML / MD / JSON / TXT report |

---

## TriageAgent

Assigns a score (0–100) and label (CRITICAL / HIGH / MEDIUM / LOW / SKIP) to every result.

**Scoring — two phases:**

Phase 1 — regex pattern matching (cap: 60 points):

| Pattern matched | Points |
|----------------|--------|
| `.env`, `.git`, `.sql`, backup files | 38 |
| Private key (`BEGIN PRIVATE KEY`) | 45 |
| AWS key ID (`AKIA...`) | 42 |
| JWT token in text | 36 |
| phpMyAdmin / Adminer / pgAdmin | 35 |
| API key / secret token | 28 |
| Config file (`config.php`, `settings.py`) | 28 |
| SQLi candidate URL pattern | 26 |
| Credentials / password in text | 24 |
| DevOps panels (Jenkins, Kibana, Grafana) | 18–22 |
| Cloud storage URLs | 18 |
| Directory listing | 22 |
| Server info exposed | 20 |
| Log files | 20 |
| Error / debug / traceback | 14 |
| ... 8 more rules | varies |

Phase 2 — runtime bonuses from existing result data:

| Condition | Bonus |
|-----------|-------|
| SQLi confirmed — confidence `critical` | +30 |
| SQLi confirmed — confidence `high` | +22 |
| SQLi confirmed — confidence `medium` or `low` | +12 |
| `accessible == True` and `status_code == 200` | +8 |
| URL has ≥ 5 GET parameters | +10 |
| URL has 2–4 GET parameters | +5 |

**Labels:**

| Score | Label |
|-------|-------|
| ≥ 90 | CRITICAL |
| ≥ 70 | HIGH |
| ≥ 50 | MEDIUM |
| ≥ 20 | LOW |
| < 20 | SKIP |

---

## SecurityAgent *(new in v3.1)*

Threat-detection middleware that operates in **two modes**:

- **passive** (default in `--analyze` pipeline) — analyses and tags every result with a `security_verdict`, no blocking.
- **active** — same as passive, plus blocks (`security_blocked = True`) results classified as DANGEROUS or CRITICAL.

It also hooks into the **live scanning flow** via `security_scan_hook(url, content, headers)` so threats can be intercepted before results are saved.

**Detection categories:**

| Category | Description |
|----------|-------------|
| `phishing` | Brand impersonation, credential harvesting pages, suspicious redirects |
| `malware` | JS code execution, obfuscated payloads, file droppers |
| `exploit` | Reverse shells, SQLi, XXE, SSTI, deserialization payloads |
| `obfuscation` | Hex/Unicode escaping, base64 chains, high-entropy strings |
| `suspicious_pattern` | Hidden iframes, missing security headers, executable downloads |

**Threat scoring — weighted model:**

The final `threat_score` (0–100) is computed as:
- **50%** from the single worst indicator
- **50%** from the weighted sum of all other indicators (capped)

| Score range | Threat level |
|-------------|-------------|
| ≤ 15 | CLEAN |
| 16 – 40 | LOW |
| 41 – 70 | SUSPICIOUS |
| 71 – 90 | DANGEROUS |
| > 90 | CRITICAL |

DANGEROUS and CRITICAL results are automatically blocked in `active` mode.

**CLI flags:**

```bash
--no-security                  # Disable SecurityAgent entirely
--security-mode active         # active: block DANGEROUS/CRITICAL | passive: report only (default)
--security-quarantine          # Save blocked content to dorkeye_quarantine/
```

**Output per result:**

```json
{
  "security_verdict": {
    "url":              "https://target.com/shell.php",
    "threat_level":     "DANGEROUS",
    "threat_score":     78,
    "badge":            "🔴 DANGEROUS",
    "blocked":          false,
    "summary":          "Reverse shell pattern detected in page content",
    "scan_duration_ms": 12.4,
    "timestamp":        "2025-01-01T12:00:00+00:00",
    "indicators": [
      {
        "category":    "exploit",
        "description": "Reverse shell pattern",
        "severity":    60,
        "evidence":    "bash -i >& /dev/tcp/..."
      }
    ]
  }
}
```

**Pipeline-level output keys** (added to the top-level report):

| Key | Content |
|-----|---------|
| `security_stats` | Counters: `clean`, `low`, `suspicious`, `dangerous`, `critical`, `blocked`, `mode` |
| `security_threats` | List of all verdicts with `threat_level` ≥ LOW |

**Inline usage (scanning flow):**

```python
from dorkeye_agents import security_scan_hook, get_security_agent

# Quick hook (uses global singleton)
verdict = security_scan_hook(url, response_text, resp_headers)
if verdict.blocked:
    continue  # skip malicious result

# Fine-grained control
agent = get_security_agent(mode="active", quarantine_dir="dorkeye_quarantine")
verdict = agent.scan_single(url, content, headers)
```

---

## PageFetchAgent

Downloads the actual HTML content of HIGH and CRITICAL results for deeper analysis.

**v4.8 improvements:**
- Up to 3 attempts per URL (1 initial + 2 retries with 1.5s / 3s backoff)
- UA rotation across 5 browser profiles on each attempt
- Saves `response_headers` dict and `fetch_status` code into the result — consumed by HeaderIntelAgent at zero extra HTTP cost

**CLI flags:**

```bash
--analyze-fetch               # enable download
--analyze-fetch-max 50        # download up to 50 pages (default: 20)
```

---

## HeaderIntelAgent

Analyzes `response_headers` saved by PageFetchAgent. Zero additional HTTP requests.

**Info leak detection** — scans these headers:

```
server · x-powered-by · x-aspnet-version · x-aspnetmvc-version
x-generator · x-drupal-cache · x-wordpress-cache
x-runtime · x-rack-cache · via · x-debug · x-cache-debug
```

**Outdated version detection** — extracts version strings for: Apache, Nginx, PHP, OpenSSL, IIS, Tomcat, Jetty, Lighttpd.

**Missing security headers** — flags absence of:

| Header | Risk |
|--------|------|
| `Strict-Transport-Security` | HSTS absent — MITM risk |
| `Content-Security-Policy` | CSP absent — XSS risk |
| `X-Frame-Options` | Clickjacking protection absent |
| `X-Content-Type-Options` | MIME sniffing protection absent |
| `Referrer-Policy` | Referrer-Policy absent |
| `Permissions-Policy` | Permissions-Policy absent |

**Output per result:**

```json
{
  "header_intel": {
    "info_leaks":       [{"header": "x-powered-by", "value": "PHP/5.6.40", "version": "PHP/5.6"}],
    "missing_security": [{"header": "content-security-policy", "reason": "CSP absent — XSS risk"}],
    "outdated":         [{"header": "server", "value": "Apache/2.2.34", "version": "Apache/2.2"}]
  }
}
```

---

## TechFingerprintAgent

Identifies technologies from `page_content`, `response_headers`, snippet, URL, and title. Attempts version extraction where possible.

**35 signatures in 7 categories:**

| Category | Technologies |
|----------|-------------|
| CMS | WordPress, Joomla, Drupal, Magento, PrestaShop, TYPO3, Shopify, Wix |
| Framework | Laravel, Django, Rails, Flask, Express.js, Next.js, Nuxt.js |
| JS libraries | jQuery (versioned), React, Vue.js, Angular, Bootstrap (versioned) |
| Server | Apache, Nginx, IIS, OpenSSL (all versioned) |
| Language | PHP, Python, Node.js (all versioned) |
| DevOps | Jenkins, GitLab, Kibana, Grafana, Docker, Kubernetes, Elasticsearch |
| DB panels | phpMyAdmin, Adminer, pgAdmin |

**CVE dork generation** — for 10 tech families, targeted dorks are generated and fed to DorkCrawlerAgent:

```
site:target.com inurl:wp-login.php
site:target.com inurl:xmlrpc.php
site:target.com inurl:app/kibana
```

**Output per result:**

```json
{
  "tech_fingerprint": {
    "techs": [
      {"name": "WordPress", "category": "cms"},
      {"name": "jQuery", "category": "js_lib", "version": "3.6.0"},
      {"name": "PHP", "category": "lang", "version": "7.4"}
    ],
    "cve_dorks": ["site:target.com inurl:wp-login.php", "..."]
  }
}
```

---

## SecretsAgent

Scans `page_content` and snippet for 50+ credential and secret patterns.

**Secret categories with severity:**

| Severity | Types |
|----------|-------|
| CRITICAL | Private keys, AWS keys, bcrypt hashes, NTLM hashes, Stripe keys |
| HIGH | DB connections, JWTs, GCP keys, Azure keys, GitHub PATs, passwords, SendGrid, Twilio, GitLab PAT, Docker PAT, NPM token |
| MEDIUM | Generic API keys, tokens, Slack keys, webhooks, SSH credentials, `.env` variables, Mailgun, Heroku |
| LOW | MD5 / SHA1 / SHA256 / SHA512 hashes, internal IPs |

**v4.8 improvements:**
- Dedup by normalized value — same secret found 10 times = 1 finding
- `severity` field on every finding
- Hash detection: bcrypt `$2y$`, MD5 (32 hex), SHA1 (40 hex), SHA256 (64 hex), SHA512 (128 hex), NTLM pairs

**Output per result:**

```json
{
  "secrets": [
    {
      "type":       "AWS_KEY",
      "detection":  "REGEX",
      "value":      "AKIA…0A2",
      "confidence": "HIGH",
      "severity":   "CRITICAL",
      "context":    "...aws_access_key_id = AKIA...",
      "source":     "https://target.com/config.php",
      "desc":       "AWS Access Key ID"
    }
  ]
}
```

---

## PiiDetectorAgent

Detects personally identifiable information. Separated from SecretsAgent by design — PII requires different handling than technical credentials.

**Detected types:**

| Type | Coverage |
|------|----------|
| `EMAIL` | Standard email format |
| `PHONE_IT` | Italian mobile (+39 3xx) and landline (0x…) |
| `PHONE_EU` | FR, ES, GB, DE, NL, BE, CH, AT, PL, PT, IE |
| `PHONE_US` | US format with optional +1 |
| `IBAN` | Generic IBAN — country code + check digits + BBAN |
| `CF_IT` | Italian codice fiscale |
| `CREDIT_CARD` | Visa, Mastercard, Discover, Amex — **Luhn-validated** |
| `SSN_US` | US SSN with exclusion of invalid blocks (000, 666, 9xx) |
| `DOB` | Date of birth in context keywords |
| `PASSPORT` | Generic EU passport pattern |
| `PUBLIC_IP` | Non-RFC-1918, non-loopback IPv4 |

Credit card numbers are validated with the Luhn algorithm — false positives from random numeric strings are eliminated.

Values are censored to 3 visible characters per end.

---

## EmailHarvesterAgent

Collects email addresses from snippet and page content, deduplicates globally across all results, and categorizes by prefix.

| Category | Prefix patterns |
|----------|----------------|
| `admin` | admin, administrator, root, sysadmin, webmaster, hostmaster, postmaster |
| `security` | security, abuse, vuln, pentest, csirt, cert, soc, noc, infosec |
| `info` | info, contact, hello, support, help, service, sales, marketing |
| `noreply` | noreply, no-reply, donotreply, mailer-daemon, bounce |
| `personal` | everything else |

Global dedup: same address found in 10 pages = counted once. Results sorted by category priority (admin first, noreply last).

---

## SubdomainHarvesterAgent

Extracts subdomains from all text fields (URL, snippet, page_content, title). Deduplicates globally per base domain.

**Base domain extraction:** takes the last two labels — `api.v2.target.com` → `target.com`.

**Follow-up dork generation** — 3 dork variants per subdomain:

```
site:api.target.com
site:api.target.com inurl:admin
site:api.target.com inurl:.env OR inurl:.git
```

These are merged with TechFingerprintAgent's CVE dorks and passed to DorkCrawlerAgent as seeds for the next round.

---

## ReportAgent

Produces the final analysis report. Accepts `html`, `md`, `json`, `txt`.

**HTML report sections:**
- Metrics bar — CRITICAL / HIGH / MEDIUM / LOW / TOTAL / SECRETS / PII / EMAILS
- Top Findings (CRITICAL & HIGH)
- Secrets Found — with severity badge (CRITICAL/HIGH/MEDIUM/LOW), detection source (REGEX/LLM)
- PII Detected
- Emails Harvested
- Subdomains Found
- CVE / Follow-up Dorks
- All Results table

**JSON report top-level keys:**

```json
{
  "meta":       { "generated_at": "...", "target": "...", "engine": "DorkEye v4.8 + Agents v3.1" },
  "metrics":    { "total": N, "by_label": {...}, "secrets": N, "pii": N, "emails": N, "subdomains": N },
  "analysis":   {},
  "secrets":    [...],
  "pii":        [...],
  "emails":     [...],
  "subdomains": { "target.com": ["api.target.com", "..."] },
  "cve_dorks":  [...],
  "results":    [...]
}
```

---

## Standalone Usage

`dorkeye_agents.py` can run directly on any existing DorkEye result file:

```bash
# Basic analysis
python dorkeye_agents.py Dump/results.json

# With page fetch
python dorkeye_agents.py Dump/results.json --analyze-fetch --analyze-fetch-max 50

# HTML report to specific path
python dorkeye_agents.py Dump/results.json \
  --analyze-fetch --analyze-fmt html --analyze-out report.html

# With target label for the report title
python dorkeye_agents.py Dump/results.json --target "example.com" --analyze-fetch

# Skip LLM triage (regex only, even if LLM plugin available)
python dorkeye_agents.py Dump/results.json --analyze-no-llm-triage
```
