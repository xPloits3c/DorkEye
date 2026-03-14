# DorkEye — HTTP Fingerprints

> **File:** `http_fingerprints.json`
> **Version:** 2.0
> **Used by:** `HTTPFingerprintRotator` class in `dorkeye.py`

The fingerprint system makes DorkEye's HTTP requests look like those of real browsers from real users around the world. Instead of sending a generic `User-Agent: python-requests/2.x` header that is trivially blocked or logged, each request is crafted with a full, coherent set of headers that matches what a specific browser on a specific OS would actually send.

---

## Table of Contents

1. [Why HTTP Fingerprinting Matters](#why-http-fingerprinting-matters)
2. [File Structure](#file-structure)
3. [_meta Block](#_meta-block)
4. [common_headers Block](#common_headers-block)
5. [language_profiles Block](#language_profiles-block)
6. [fingerprints Block](#fingerprints-block)
7. [Reference Resolution (@syntax)](#reference-resolution-syntax)
8. [How DorkEye Loads and Uses the File](#how-dorkeye-loads-and-uses-the-file)
9. [Fingerprint Inventory](#fingerprint-inventory)
10. [Headers Explained](#headers-explained)
11. [Adding Custom Fingerprints](#adding-custom-fingerprints)
12. [Disabling Fingerprinting](#disabling-fingerprinting)

---

## Why HTTP Fingerprinting Matters

When a crawler sends requests to web servers, the server logs every detail: User-Agent, Accept headers, language, encoding preference, and Sec-Fetch-* directives. A generic Python `requests` signature is trivially identifiable and is commonly used to:

- Trigger rate-limiting or bot-detection (Cloudflare, Akamai, etc.)
- Return different content or block the request entirely
- Log the activity as automated/tool traffic

A complete HTTP fingerprint makes DorkEye's requests indistinguishable from legitimate browser traffic at the header level.

---

## File Structure

```json
{
  "_meta":            { ... },        // metadata about this file
  "common_headers":   { ... },        // reusable header value strings
  "language_profiles": { ... },       // Accept-Language strings by locale
  "fingerprints":     { ... }         // named browser fingerprint profiles
}
```

All four top-level keys are required. The file is loaded once at startup by `load_http_fingerprints()` and kept in memory for the duration of the session.

---

## `_meta` Block

Informational only — not used at runtime. Documents the file's identity and version.

```json
"_meta": {
  "name":             "DorkEye Advanced HTTP Fingerprints",
  "version":          "2.0",
  "description":      "...",
  "generated_at":     "2026-03-14",
  "fingerprint_count": 22
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable name |
| `version` | string | Semver-style version for tracking changes |
| `description` | string | Brief summary |
| `generated_at` | string | ISO date when the file was last updated |
| `fingerprint_count` | integer | Total number of fingerprint entries (for quick sanity check) |

---

## `common_headers` Block

Stores reusable header value strings that can be referenced from fingerprints using `@key` syntax. This avoids duplicating long strings across dozens of fingerprint entries.

```json
"common_headers": {
  "accept_html_chrome":  "text/html,application/xhtml+xml,...",
  "accept_html_firefox": "text/html,application/xhtml+xml,...",
  "accept_html_safari":  "text/html,application/xhtml+xml,...",
  "accept_html_edge":    "text/html,application/xhtml+xml,...",
  "accept_encoding_br":  "gzip, deflate, br, zstd",
  "accept_encoding_std": "gzip, deflate, br",
  "cache_no_cache":      "no-cache",
  "cache_max_age":       "max-age=0"
}
```

### Accept header variants

Different browsers send slightly different `Accept` headers. Using the correct one per browser makes the fingerprint more realistic.

| Key | Used by | Notable difference |
|-----|--------|--------------------|
| `accept_html_chrome` | Chrome, Edge, Opera, Brave, Samsung | Includes `image/apng`, `application/signed-exchange;v=b3` |
| `accept_html_firefox` | Firefox (desktop + mobile) | No `apng`, no `signed-exchange` |
| `accept_html_safari` | Safari (macOS + iOS) | Shorter — just `*/*;q=0.8`, no `avif` |
| `accept_html_edge` | Edge (Chromium-based) | Identical to Chrome's format |

### Accept-Encoding variants

| Key | Value | Notes |
|-----|-------|-------|
| `accept_encoding_br` | `gzip, deflate, br, zstd` | Chrome 120+ supports `zstd` |
| `accept_encoding_std` | `gzip, deflate, br` | Older browsers, Firefox, Safari, mobile |

### Cache-Control variants

| Key | Value | When browsers use it |
|-----|-------|----------------------|
| `cache_no_cache` | `no-cache` | Fresh navigation (Ctrl+L, typed URL) |
| `cache_max_age` | `max-age=0` | Reload, Safari navigation |

---

## `language_profiles` Block

Maps locale codes to full `Accept-Language` header values. These are assigned to fingerprints as a list of candidates — the rotator picks one at random for each request, adding realistic geographic diversity.

```json
"language_profiles": {
  "en-US": "en-US,en;q=0.9",
  "it-IT": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
  ...
}
```

### Full profile list (v2.0)

| Locale code | Language | Region |
|------------|----------|--------|
| `en-US` | English | United States |
| `en-GB` | English | United Kingdom |
| `it-IT` | Italian | Italy |
| `fr-FR` | French | France |
| `de-DE` | German | Germany |
| `es-ES` | Spanish | Spain |
| `es-MX` | Spanish | Mexico |
| `pt-BR` | Portuguese | Brazil |
| `pt-PT` | Portuguese | Portugal |
| `ru-RU` | Russian | Russia |
| `pl-PL` | Polish | Poland |
| `nl-NL` | Dutch | Netherlands |
| `tr-TR` | Turkish | Turkey |
| `zh-CN` | Chinese (Simplified) | China |
| `zh-TW` | Chinese (Traditional) | Taiwan |
| `ja-JP` | Japanese | Japan |
| `ko-KR` | Korean | South Korea |
| `ar-SA` | Arabic | Saudi Arabia |
| `hi-IN` | Hindi | India |
| `vi-VN` | Vietnamese | Vietnam |
| `id-ID` | Indonesian | Indonesia |
| `uk-UA` | Ukrainian | Ukraine |

Each profile uses correct `q` (quality factor) values that match real browser behavior — the primary language has `q=0.9`, fallback languages progressively lower (`0.8`, `0.7`, etc.).

---

## `fingerprints` Block

Each key is a unique fingerprint identifier. The value is a fingerprint object describing a specific browser + OS combination.

### Fingerprint object structure

```json
"chrome_131_windows11": {
  "browser":  "chrome",
  "os":       "windows",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
  "headers": {
    "accept":                    "@accept_html_chrome",
    "accept_encoding":           "@accept_encoding_br",
    "cache_control":             "@cache_no_cache",
    "accept_language_profiles":  ["en-US", "it-IT", "de-DE", "fr-FR", "es-ES", "pl-PL"],
    "sec_fetch": {
      "dest": "document",
      "mode": "navigate",
      "site": "none"
    }
  }
}
```

### Top-level fingerprint fields

| Field | Type | Description |
|-------|------|-------------|
| `browser` | string | Browser family identifier (see values below) |
| `os` | string | Operating system: `windows`, `macos`, `linux`, `android`, `ios` |
| `user_agent` | string | Full User-Agent string for this browser/OS combination |
| `headers` | object | HTTP headers configuration (see below) |

### `browser` field values

| Value | Description |
|-------|-------------|
| `chrome` | Google Chrome desktop |
| `chrome_mobile` | Chrome for Android |
| `firefox` | Mozilla Firefox desktop |
| `firefox_mobile` | Firefox for Android |
| `safari` | Apple Safari macOS |
| `safari_mobile` | Safari on iPhone / iPad |
| `edge` | Microsoft Edge (Chromium) desktop |
| `edge_mobile` | Edge for Android |
| `opera` | Opera desktop |
| `samsung_internet` | Samsung Internet (Android) |
| `brave` | Brave browser desktop |

### `headers` sub-object fields

| Field | Type | Description |
|-------|------|-------------|
| `accept` | string | `@key` reference to a `common_headers` Accept value |
| `accept_encoding` | string | `@key` reference to an encoding profile |
| `cache_control` | string | `@key` reference to a cache control value |
| `accept_language_profiles` | array of strings | List of locale codes to pick from randomly |
| `sec_fetch` | object | Sec-Fetch-* directives (see below) |

### `sec_fetch` sub-object

The `Sec-Fetch-*` headers are security hints added by Chromium-based browsers and Firefox. They tell the server about the navigation context.

| Field | Sent as header | Possible values |
|-------|---------------|-----------------|
| `dest` | `Sec-Fetch-Dest` | `document` (always for page navigation) |
| `mode` | `Sec-Fetch-Mode` | `navigate` (always for top-level navigation) |
| `site` | `Sec-Fetch-Site` | `none` (typed URL / bookmark) or `cross-site` (link from other domain) |

**`site: "none"`** simulates a user typing the URL directly or opening a bookmark.
**`site: "cross-site"`** simulates following a link from another domain (e.g. from a search engine result).

Using both values realistically across fingerprints prevents pattern detection based on this header alone.

---

## Reference Resolution (`@` syntax)

When a header value starts with `@`, DorkEye resolves it by looking up the remainder as a key in `common_headers`. This is handled by `resolve_reference()` in `dorkeye.py`.

```python
def resolve_reference(value: str, common_headers: Dict) -> str:
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        return common_headers.get(key, "")
    return value
```

`accept_language_profiles` is handled separately by `resolve_accept_language()`, which picks one locale at random from the list and looks it up in `language_profiles`.

```python
def resolve_accept_language(fp_headers: Dict, language_profiles: Dict) -> str:
    profiles = fp_headers.get("accept_language_profiles")
    if not profiles:
        return ""
    profile = random.choice(profiles)
    return language_profiles.get(profile, "")
```

This means every request randomly selects one of the listed language profiles for that fingerprint — giving geographic diversity within the same browser identity.

---

## How DorkEye Loads and Uses the File

### Loading

```python
# Called once at startup
fingerprints_data = load_http_fingerprints()
```

`load_http_fingerprints()` reads the JSON file from the same directory as `dorkeye.py`. It detects two modes:

| Mode | Detection | Behavior |
|------|-----------|----------|
| `advanced` | `"fingerprints"` key present in root | Full resolution with `@references` and language profiles |
| `legacy` | Flat dict (old format) | Direct field mapping, no `@reference` resolution |
| `disabled` | File missing or invalid | Falls back to a minimal generic User-Agent header |

### Runtime usage

The `HTTPFingerprintRotator` class manages a list of pre-built `HTTPFingerprint` dataclass instances. Two rotation strategies are available:

| Method | Behavior |
|--------|----------|
| `get_random()` | Picks a uniformly random fingerprint for each request |
| `get_next()` | Round-robins through the list sequentially |

DorkEye uses `get_random()` in the `SQLiDetector._get()` method so each HTTP request gets a randomly selected fingerprint.

### Final header set built per request

`build_headers(referer="")` assembles the following headers from the resolved fingerprint:

```
User-Agent
Accept
Accept-Language
Accept-Encoding
Sec-Fetch-Dest
Sec-Fetch-Mode
Sec-Fetch-Site
Cache-Control
Pragma            → always "no-cache"
DNT               → always "1"
Connection        → always "keep-alive"
Upgrade-Insecure-Requests → always "1"
Referer           → optional, passed at call time
```

---

## Fingerprint Inventory

### v2.0 — 22 fingerprints

| ID | Browser | Version | OS | Mobile | Sec-Fetch-Site |
|----|---------|---------|-----|--------|----------------|
| `chrome_131_windows11` | Chrome | 131 | Windows 11 | No | `none` |
| `chrome_131_windows10` | Chrome | 130 | Windows 10 | No | `cross-site` |
| `chrome_131_macos` | Chrome | 131 | macOS 10.15 | No | `none` |
| `chrome_131_linux` | Chrome | 131 | Linux x86_64 | No | `none` |
| `chrome_android_pixel` | Chrome Mobile | 131 | Android 14 (Pixel 8) | Yes | `cross-site` |
| `chrome_android_samsung` | Chrome Mobile | 131 | Android 14 (SM-S928B) | Yes | `cross-site` |
| `firefox_133_windows` | Firefox | 133 | Windows 10 | No | `none` |
| `firefox_133_macos` | Firefox | 133 | macOS 14.7 | No | `none` |
| `firefox_133_linux` | Firefox | 133 | Linux x86_64 | No | `cross-site` |
| `firefox_android` | Firefox Mobile | 133 | Android 14 | Yes | `cross-site` |
| `safari_macos_sequoia` | Safari | 18.2 | macOS 15.2 Sequoia | No | `none` |
| `safari_macos_ventura` | Safari | 17.4.1 | macOS 13.7 Ventura | No | `none` |
| `safari_iphone_ios18` | Safari Mobile | 18.2 | iOS 18.2 (iPhone) | Yes | `cross-site` |
| `safari_iphone_ios17` | Safari Mobile | 17.4.1 | iOS 17.7 (iPhone) | Yes | `cross-site` |
| `safari_ipad_ios18` | Safari Mobile | 18.2 | iOS 18.2 (iPad) | Yes | `none` |
| `edge_131_windows` | Edge | 131 | Windows 10 | No | `none` |
| `edge_131_macos` | Edge | 131 | macOS 10.15 | No | `none` |
| `edge_android` | Edge Mobile | 131 | Android 14 (Pixel 8) | Yes | `cross-site` |
| `opera_windows` | Opera | 116 | Windows 10 | No | `none` |
| `opera_macos` | Opera | 116 | macOS 14.7 | No | `none` |
| `samsung_browser_android` | Samsung Internet | 27 | Android 14 (SM-S928B) | Yes | `cross-site` |
| `brave_windows` | Brave | 131 (Chromium) | Windows 10 | No | `none` |

### Coverage summary

| Dimension | Values |
|-----------|--------|
| OS | Windows, macOS, Linux, Android, iOS |
| Browser families | Chrome, Firefox, Safari, Edge, Opera, Samsung Internet, Brave |
| Mobile devices | Pixel 8, Samsung Galaxy S24 Ultra, iPhone (iOS 17 + 18), iPad |
| Desktop total | 13 fingerprints |
| Mobile total | 9 fingerprints |
| Language profiles | 22 locales across 6 continents |

---

## Headers Explained

### User-Agent

The most important header for browser identification. It encodes browser engine, version, OS, and architecture. DorkEye uses only real, currently active UA strings — no synthetic or outdated ones.

**Structure example (Chrome):**
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64)           ← OS info
AppleWebKit/537.36 (KHTML, like Gecko)               ← rendering engine
Chrome/131.0.0.0                                     ← browser name + version
Safari/537.36                                        ← legacy Safari compat token
```

**Structure example (Safari mobile):**
```
Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X)
AppleWebKit/605.1.15 (KHTML, like Gecko)
Version/18.2 Mobile/15E148 Safari/604.1
```

### Accept

Tells the server what content types the browser can handle, in priority order. Different browsers have measurably different Accept strings:

- **Chrome/Edge:** includes `image/apng` and `application/signed-exchange;v=b3`
- **Firefox:** simpler — no `apng`, no signed-exchange
- **Safari:** minimal — just `text/html`, `application/xhtml+xml`, `*/*;q=0.8`

### Accept-Encoding

Lists compression algorithms the browser supports:

| Value | Description |
|-------|-------------|
| `gzip` | Standard — supported by all browsers |
| `deflate` | Legacy — all browsers |
| `br` | Brotli — Chrome 50+, Firefox 44+, Safari 13+ |
| `zstd` | Zstandard — Chrome 118+, Edge 118+ (newer only) |

### Accept-Language

Signals the user's language preference. Format: `primary;q=1.0, fallback1;q=0.9, fallback2;q=0.8`.
The `q` value is the quality factor (preference weight, 0.0–1.0).

### Sec-Fetch-Dest

What the request is for: `document` = main HTML page, `image`, `script`, `fetch`, etc. DorkEye always uses `document` since it is performing page-level requests.

### Sec-Fetch-Mode

How the request was initiated: `navigate` = user navigation, `cors`, `no-cors`, `same-origin`. DorkEye always uses `navigate`.

### Sec-Fetch-Site

Relationship between the request origin and destination:

| Value | Meaning |
|-------|---------|
| `none` | No referrer context (typed URL, bookmark, new tab) |
| `cross-site` | Request came from a different domain |
| `same-origin` | Same domain |
| `same-site` | Same site, different subdomain |

DorkEye uses both `none` and `cross-site` to simulate both direct navigation and link-following behavior.

### Pragma

Legacy HTTP/1.0 cache directive. Always set to `no-cache` — still sent by modern browsers for backwards compatibility.

### DNT (Do Not Track)

`1` = user has requested not to be tracked. Always set to `1` — adds realism without any practical effect.

### Connection

`keep-alive` — maintains persistent TCP connections. All modern browsers use this.

### Upgrade-Insecure-Requests

`1` — browser prefers HTTPS over HTTP when available. All modern browsers send this.

---

## Adding Custom Fingerprints

To add a new browser fingerprint:

1. Add a new entry to the `"fingerprints"` object with a descriptive unique key
2. Set `browser` and `os` to appropriate values
3. Use a real, current User-Agent string (check [useragents.me](https://useragents.me) or browser devtools)
4. Set `accept` to `@accept_html_chrome` (or the appropriate variant)
5. Set `accept_encoding` to `@accept_encoding_br` for modern Chromium or `@accept_encoding_std` for others
6. Set `cache_control` to `@cache_no_cache` or `@cache_max_age`
7. List realistic `accept_language_profiles` for that browser's typical user base
8. Set `sec_fetch.site` to `none` for desktop direct navigation or `cross-site` for mobile/referred

Update `_meta.fingerprint_count` to match the new total.

**Example — adding a new Chrome version:**

```json
"chrome_132_windows": {
  "browser": "chrome",
  "os": "windows",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
  "headers": {
    "accept":                   "@accept_html_chrome",
    "accept_encoding":          "@accept_encoding_br",
    "cache_control":            "@cache_no_cache",
    "accept_language_profiles": ["en-US", "de-DE", "fr-FR"],
    "sec_fetch": {
      "dest": "document",
      "mode": "navigate",
      "site": "none"
    }
  }
}
```

---

## Disabling Fingerprinting

HTTP fingerprinting can be disabled in three ways:

**CLI flag:**
```bash
python dorkeye.py -d "your dork" --no-fingerprint
```

**Config file:**
```yaml
# dorkeye_config.yaml
http_fingerprinting: false
```

**Missing file:** if `http_fingerprints.json` is not found or is invalid, DorkEye logs a warning and falls back to a minimal generic header set (`User-Agent: Mozilla/5.0`, `Accept: */*`, `Connection: keep-alive`).

When fingerprinting is disabled, standard User-Agent rotation via `UserAgentRotator` is still active (if `user_agent_rotation: true` in config), providing basic rotation using the `USER_AGENTS` dict defined in `dorkeye.py`.

---

*DorkEye v4.6 — For authorized security research only.*
