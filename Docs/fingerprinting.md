# HTTP Fingerprinting — DorkEye v4.8

HTTP fingerprinting makes DorkEye's requests look like real browser traffic instead of a Python script. Each request is built from a complete browser profile — not just a user-agent string.

---

## What Gets Rotated

Every HTTP request sent by DorkEye (dork search, file analysis, SQLi testing, page fetch) uses a randomly selected fingerprint that sets:

| Header | Example |
|--------|---------|
| `User-Agent` | Full browser + OS + version string |
| `Accept` | Browser-specific MIME preference order |
| `Accept-Language` | Language profile matching the browser's region |
| `Accept-Encoding` | `gzip, deflate, br` or `gzip, deflate, br, zstd` |
| `Sec-Fetch-Dest` | `document`, `image`, `script`, etc. |
| `Sec-Fetch-Mode` | `navigate`, `cors`, `no-cors` |
| `Sec-Fetch-Site` | `none`, `cross-site`, `same-origin` |
| `Cache-Control` | `no-cache` or `max-age=0` |

This combination is much harder to fingerprint as a bot than a single static header.

---

## Fingerprint Dataset — v2.0

`http_fingerprints.json` ships with 22 profiles covering:

| Dimension | Coverage |
|-----------|----------|
| Browser families | Chrome, Firefox, Safari, Edge, Opera, Samsung Internet, Brave |
| OS / platform | Windows, macOS, Linux, Android, iOS |
| Mobile support | Pixel 8 (Android), Samsung S928B, iPhone iOS 17–18, iPad |
| Browser versions | 2025–2026 (updated from the 2024 set in v4.6) |
| Language profiles | 22 regional profiles |

---

## Enable / Disable

Fingerprinting is **on by default**.

```bash
# Disable fingerprinting (uses plain UA rotation only)
python dorkeye.py -d dorks.txt --no-fingerprint -o results.html

# Fingerprinting is always active unless disabled
python dorkeye.py -d dorks.txt -o results.html
```

In the configuration file:

```yaml
http_fingerprinting: true   # default
user_agent_rotation: true   # fallback when fingerprinting is off
```

---

## PageFetchAgent UA Pool (v4.8)

When `--analyze-fetch` downloads page content, the `PageFetchAgent` uses its own 5-profile UA pool independently of the main fingerprint rotator:

```
Chrome 124 — Windows 10
Chrome 123 — macOS Ventura
Firefox 125 — Windows 10
Chrome 122 — Linux x86_64
Safari 17.4 — macOS Sonoma
```

Each fetch attempt (including retries) picks a random profile from this pool.

---

## Stealth Mode

`--stealth` builds on top of fingerprinting with additional behavioural controls:

| Control | Normal | Stealth |
|---------|--------|---------|
| Delay between dorks | 8–28s | 12–50s |
| Extended cooldown trigger | every 100 results | every 100 results |
| Extended cooldown duration | 85–110s | 120–150s |
| SQLi delay between params | random 0–0.5s | 2–4s |
| SQLi delay between payloads | minimal | 1.5–3s |
| Baseline latency measurement | 2 samples | 2 samples |

```bash
python dorkeye.py -d dorks.txt --stealth --sqli -o results.json
```

---

## Custom Fingerprints

You can extend `http_fingerprints.json` with your own profiles. The file supports two schema modes:

**Legacy mode** — flat list of fingerprint objects:

```json
{
  "browser_name": {
    "browser": "Chrome",
    "os": "Windows",
    "user_agent": "Mozilla/5.0 ...",
    "accept_language": "en-US,en;q=0.9",
    "accept_encoding": "gzip, deflate, br",
    "accept": "text/html,application/xhtml+xml,...",
    "sec_fetch_dest": "document",
    "sec_fetch_mode": "navigate",
    "sec_fetch_site": "none",
    "cache_control": "max-age=0"
  }
}
```

**Advanced mode** — shared header references + language profiles (used by the v2.0 dataset). Both modes are auto-detected at load time.
