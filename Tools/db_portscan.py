#!/usr/bin/env python3
"""
DB Port Scanner for DorkEye Project
Scans exposed database ports on hosts extracted from dork results.

Lives in: DorkEye/Tools/db_portscan.py

Detects:
  - Open database ports: MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch,
    CouchDB, MSSQL, Oracle, Cassandra, Memcached, InfluxDB, Neo4j, RethinkDB
  - Unauthenticated access via no-auth probes (Redis PING, ES HTTP, CouchDB
    HTTP, MongoDB handshake, Memcached stats, InfluxDB /ping)
  - Service banner grabbing for port confirmation

Severity:
  CRITICAL  — port open + no-auth confirmed  (data directly accessible)
  HIGH      — port open + service confirmed  (auth likely required)
  MEDIUM    — port open, service unconfirmed
  INFO      — port closed / filtered / timeout

Author: xPloits3c | DorkEye Project
"""

from __future__ import annotations

import json
import queue
import random
import re
import socket
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# ── Optional rich console ─────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.markup import escape as _re
    _console = Console()
    def _log(msg: str, style: str = "cyan") -> None:
        if style:
            _console.print(f"[{style}]{msg}[/{style}]")
        else:
            _console.print(msg)
except ImportError:
    _console = None
    def _log(msg: str, style: str = "") -> None:
        print(msg)

# ── Optional requests (for HTTP probes) ──────────────────────────────────────
try:
    import requests as _requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

# ══════════════════════════════════════════════════════════════════════════════
#  DB PORT DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DBPortDef:
    port:         int
    name:         str                  # service name
    probe:        str                  # none | banner | http | redis | mongodb | memcached
    http_path:    str  = ""            # path for HTTP probe (e.g. "/" for ES)
    http_ok_keys: List[str] = field(default_factory=list)  # keys in response body confirming no-auth
    default_db:   bool = True          # include in default scan set


# Full DB port catalogue
DB_PORT_CATALOGUE: List[DBPortDef] = [
    # ── No-auth HTTP probes ──────────────────────────────────────────────────
    DBPortDef(9200,  "Elasticsearch",  "http",       "/",         ["cluster_name","version","tagline"]),
    DBPortDef(9300,  "Elasticsearch",  "banner",     "",          []),
    DBPortDef(5984,  "CouchDB",        "http",       "/",         ["couchdb","Welcome"]),
    DBPortDef(8086,  "InfluxDB",       "http",       "/ping",     []),          # 204 = alive
    DBPortDef(7474,  "Neo4j HTTP",     "http",       "/",         ["neo4j","bolt"]),
    DBPortDef(8098,  "Riak HTTP",      "http",       "/",         ["riak"]),
    DBPortDef(28015, "RethinkDB",      "banner",     "",          []),
    # ── Raw TCP banner/probe ─────────────────────────────────────────────────
    DBPortDef(3306,  "MySQL",          "banner",     "",          []),
    DBPortDef(5432,  "PostgreSQL",     "banner",     "",          []),
    DBPortDef(27017, "MongoDB",        "mongodb",    "",          []),
    DBPortDef(6379,  "Redis",          "redis",      "",          []),
    DBPortDef(11211, "Memcached",      "memcached",  "",          []),
    DBPortDef(1433,  "MSSQL",          "banner",     "",          []),
    DBPortDef(1521,  "Oracle",         "banner",     "",          []),
    DBPortDef(9042,  "Cassandra",      "banner",     "",          []),
    DBPortDef(5000,  "RethinkDB",      "banner",     "",          [],           False),
    DBPortDef(50000, "DB2",            "banner",     "",          [],           False),
    DBPortDef(27018, "MongoDB Shard",  "mongodb",    "",          [],           False),
    DBPortDef(27019, "MongoDB Config", "mongodb",    "",          [],           False),
]

# Quick lookup by port number
DB_PORT_MAP: Dict[int, DBPortDef] = {d.port: d for d in DB_PORT_CATALOGUE}

# Default scan set (only default_db=True)
DEFAULT_PORTS: List[int] = [d.port for d in DB_PORT_CATALOGUE if d.default_db]

# Severity weights per probe outcome
_SEVERITY_MAP = {
    "no_auth":   "CRITICAL",
    "confirmed": "HIGH",
    "open":      "MEDIUM",
}

# ── Dork-pattern → port hints ─────────────────────────────────────────────────
# If a URL/title/dork snippet matches these patterns, those ports are
# promoted to the front of the scan queue for that host.
DORK_PORT_HINTS: List[Tuple[re.Pattern, List[int]]] = [
    (re.compile(r"phpmyadmin|mysqladmin",        re.I), [3306]),
    (re.compile(r"pgadmin|postgresql|postgres",  re.I), [5432]),
    (re.compile(r"mongodb|mongo|robo3t",         re.I), [27017, 27018]),
    (re.compile(r"redis|redisinsight",           re.I), [6379]),
    (re.compile(r"elasticsearch|kibana",         re.I), [9200, 9300]),
    (re.compile(r"couchdb|fauxton",              re.I), [5984]),
    (re.compile(r"influx",                       re.I), [8086]),
    (re.compile(r"neo4j",                        re.I), [7474]),
    (re.compile(r"mssql|sqlserver|sql.server",   re.I), [1433]),
    (re.compile(r"oracle|tns.listener",          re.I), [1521]),
    (re.compile(r"cassandra",                    re.I), [9042]),
    (re.compile(r"memcache",                     re.I), [11211]),
]

# ══════════════════════════════════════════════════════════════════════════════
#  RESULT DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PortFinding:
    host:        str
    port:        int
    service:     str
    status:      str        # open | closed | timeout | error
    severity:    str        # CRITICAL | HIGH | MEDIUM | INFO
    probe:       str        # none | banner | http | redis | mongodb | memcached
    no_auth:     bool = False
    banner:      str  = ""
    detail:      str  = ""
    source_url:  str  = ""
    timestamp:   str  = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def label(self) -> str:
        if self.no_auth:
            return f"CRITICAL — {self.service} no-auth"
        if self.status == "open":
            return f"{self.severity} — {self.service} open"
        return f"INFO — {self.service} {self.status}"


@dataclass
class HostScanResult:
    host:     str
    findings: List[PortFinding] = field(default_factory=list)
    scanned:  int = 0
    duration: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")

    @property
    def open_ports(self) -> List[int]:
        return [f.port for f in self.findings if f.status == "open"]

    def to_dict(self) -> dict:
        return {
            "host":      self.host,
            "scanned":   self.scanned,
            "duration":  round(self.duration, 2),
            "critical":  self.critical_count,
            "high":      self.high_count,
            "findings":  [f.to_dict() for f in self.findings],
            "open_ports": self.open_ports,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL PROBES
# ══════════════════════════════════════════════════════════════════════════════

def _tcp_connect(host: str, port: int, timeout: float) -> Optional[socket.socket]:
    """Return connected socket or None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return s
    except Exception:
        return None


def _probe_banner(host: str, port: int, timeout: float) -> Tuple[str, str]:
    """
    Connect, wait for a banner, close.
    Returns (status, banner_snippet).
    status: 'open' | 'closed' | 'timeout'
    """
    s = _tcp_connect(host, port, timeout)
    if s is None:
        return "closed", ""
    try:
        s.settimeout(timeout)
        try:
            data = s.recv(512)
            banner = data.decode("utf-8", errors="replace").strip()[:200]
        except Exception:
            banner = ""
        return "open", banner
    finally:
        try:
            s.close()
        except Exception:
            pass


def _probe_redis(host: str, port: int, timeout: float) -> Tuple[str, bool, str]:
    """
    Send PING. If +PONG received → no-auth.
    Returns (status, no_auth, detail).
    """
    s = _tcp_connect(host, port, timeout)
    if s is None:
        return "closed", False, ""
    try:
        s.settimeout(timeout)
        s.sendall(b"PING\r\n")
        data = s.recv(128).decode("utf-8", errors="replace").strip()
        if "+PONG" in data:
            return "open", True, "Unauthenticated PING/PONG — data directly accessible"
        if "-NOAUTH" in data or "NOAUTH" in data:
            return "open", False, "Auth required (NOAUTH error received)"
        if "-ERR" in data:
            return "open", False, f"Open, auth response: {data[:80]}"
        return "open", False, data[:80]
    except Exception as e:
        return "open", False, str(e)[:80]
    finally:
        try:
            s.close()
        except Exception:
            pass


def _probe_mongodb(host: str, port: int, timeout: float) -> Tuple[str, bool, str]:
    """
    Send a minimal MongoDB OP_MSG isMaster probe.
    A successful reply means the port is open; lack of auth error → no-auth.
    """
    # Minimal OP_MSG: isMaster command
    # MsgHeader(16) + flagBits(4) + section(kind=0 + BSON doc)
    # BSON: {isMaster: 1}
    _bson_doc = (
        b"\x13\x00\x00\x00"     # doc length = 19
        b"\x10"                 # int32 type
        b"isMaster\x00"         # key
        b"\x01\x00\x00\x00"     # value = 1
        b"\x00"                 # doc terminator
    )
    _section = b"\x00" + _bson_doc                  # kind byte + body
    _flag    = b"\x00\x00\x00\x00"                  # flagBits
    _payload = _flag + _section
    _msg_len = (16 + len(_payload)).to_bytes(4, "little")
    _header  = _msg_len + b"\x01\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\xdd\x07\x00\x00"
    _packet  = _header + _payload

    s = _tcp_connect(host, port, timeout)
    if s is None:
        return "closed", False, ""
    try:
        s.settimeout(timeout)
        s.sendall(_packet)
        data = s.recv(512)
        if len(data) > 16:
            body = data[20:].decode("utf-8", errors="replace")
            if "ismaster" in body.lower() or "isWritablePrimary" in body.lower():
                return "open", True, "MongoDB responded to isMaster — no auth required"
            return "open", False, "MongoDB port open, auth state unclear"
        return "open", False, "MongoDB port open (short response)"
    except Exception as e:
        # Connection accepted but errored → port is open
        return "open", False, f"Open (probe error: {str(e)[:60]})"
    finally:
        try:
            s.close()
        except Exception:
            pass


def _probe_memcached(host: str, port: int, timeout: float) -> Tuple[str, bool, str]:
    """
    Send 'stats\r\n'. A STAT response → no-auth (memcached has no auth by default).
    """
    s = _tcp_connect(host, port, timeout)
    if s is None:
        return "closed", False, ""
    try:
        s.settimeout(timeout)
        s.sendall(b"stats\r\n")
        data = s.recv(512).decode("utf-8", errors="replace").strip()
        if data.startswith("STAT"):
            version_match = re.search(r"STAT version (\S+)", data)
            ver = version_match.group(1) if version_match else "?"
            return "open", True, f"Memcached v{ver} — unauthenticated stats accessible"
        return "open", False, data[:80]
    except Exception:
        return "open", False, ""
    finally:
        try:
            s.close()
        except Exception:
            pass


def _probe_http(
    host: str,
    port: int,
    path: str,
    ok_keys: List[str],
    timeout: float,
) -> Tuple[str, bool, str]:
    """
    HTTP GET probe. Returns (status, no_auth, detail).
    no_auth is True if response contains all ok_keys (service open without credentials).
    Falls back to raw TCP if requests is unavailable.
    """
    if not _REQUESTS_OK:
        # Fallback: raw TCP banner
        status, banner = _probe_banner(host, port, timeout)
        return status, False, banner

    for scheme in ("http", "https"):
        url = f"{scheme}://{host}:{port}{path}"
        try:
            r = _requests.get(
                url,
                timeout=timeout,
                verify=False,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 DorkEye DBScan/1.0"},
            )
            body = r.text[:1000]
            # Check for no-auth indicators
            if ok_keys and all(k.lower() in body.lower() for k in ok_keys):
                detail = f"HTTP {r.status_code} — unauthenticated access confirmed"
                return "open", True, detail
            if r.status_code in (200, 201, 204):
                return "open", False, f"HTTP {r.status_code} — service responding"
            if r.status_code == 401:
                return "open", False, f"HTTP 401 — auth required"
            if r.status_code == 403:
                return "open", False, f"HTTP 403 — access restricted"
            return "open", False, f"HTTP {r.status_code}"
        except _requests.exceptions.SSLError:
            continue
        except _requests.exceptions.ConnectionError:
            continue
        except Exception:
            continue
    return "closed", False, ""


# ══════════════════════════════════════════════════════════════════════════════
#  PER-PORT SCAN DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

def _scan_port(
    host:        str,
    port_def:    DBPortDef,
    timeout:     float,
    source_url:  str = "",
) -> Optional[PortFinding]:
    """
    Scan a single port on a host.
    Returns a PortFinding only if the port is open.
    """
    probe = port_def.probe

    # ── Dispatch probe type ───────────────────────────────────────────────────
    if probe == "redis":
        status, no_auth, detail = _probe_redis(host, port_def.port, timeout)

    elif probe == "mongodb":
        status, no_auth, detail = _probe_mongodb(host, port_def.port, timeout)

    elif probe == "memcached":
        status, no_auth, detail = _probe_memcached(host, port_def.port, timeout)

    elif probe == "http":
        status, no_auth, detail = _probe_http(
            host, port_def.port, port_def.http_path, port_def.http_ok_keys, timeout
        )

    else:  # banner
        status, banner = _probe_banner(host, port_def.port, timeout)
        no_auth = False
        detail  = banner

    # Only return a finding if the port is open
    if status != "open":
        return None

    # Compute severity
    if no_auth:
        severity = "CRITICAL"
    else:
        # Attempt banner-based confirmation
        banner_lower = detail.lower()
        confirmed = any(kw in banner_lower for kw in [
            port_def.name.lower(), "mysql", "postgre", "mongo",
            "redis", "elastic", "couch", "memcache", "influx", "neo4j",
            "cassandra", "mssql", "oracle", "db2",
        ])
        severity = "HIGH" if confirmed else "MEDIUM"

    return PortFinding(
        host       = host,
        port       = port_def.port,
        service    = port_def.name,
        status     = status,
        severity   = severity,
        probe      = probe,
        no_auth    = no_auth,
        banner     = detail[:200],
        detail     = detail[:400],
        source_url = source_url,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL INTERRUPT FLAG (mirrors sqli.py pattern)
# ══════════════════════════════════════════════════════════════════════════════

_exit_requested: bool  = False
_skip_current:   bool  = False


# ══════════════════════════════════════════════════════════════════════════════
#  DB PORT SCAN AGENT
# ══════════════════════════════════════════════════════════════════════════════

class DBPortScanAgent:
    """
    Extracts hosts from DorkEye result dicts and scans them for exposed
    database ports.

    Usage:
        agent = DBPortScanAgent(timeout=2.0, threads=50)
        scan_results = agent.run(dorkeye_results)

    Each entry in dorkeye_results must have at least a 'url' key.
    Optionally 'title', 'snippet', 'dork' are used for port-hint detection.

    Returns a DBScanReport with per-host findings.
    """

    def __init__(
        self,
        timeout:     float      = 2.5,
        threads:     int        = 60,
        ports:       List[int]  = None,
        stealth:     bool       = False,
        max_hosts:   int        = 200,
    ):
        self.timeout   = timeout
        self.threads   = min(threads, 200)
        self.ports     = ports if ports is not None else list(DEFAULT_PORTS)
        self.stealth   = stealth
        self.max_hosts = max_hosts

        # Results accumulator
        self._host_results: Dict[str, HostScanResult] = {}
        self._lock = threading.Lock()

        # Stats
        self.stats = {
            "hosts_scanned":    0,
            "ports_scanned":    0,
            "open_ports":       0,
            "critical":         0,
            "high":             0,
            "medium":           0,
        }

    # ── Host extraction ───────────────────────────────────────────────────────

    def _extract_hosts(self, results: List[dict]) -> List[Tuple[str, str, List[int]]]:
        """
        Extract unique (hostname, source_url, priority_ports) tuples from results.
        priority_ports: ports hinted by dork/title/snippet pattern matching.
        """
        seen:  Set[str] = set()
        hosts: List[Tuple[str, str, List[int]]] = []

        for r in results:
            url = r.get("url", "")
            if not url:
                continue
            try:
                parsed = urlparse(url)
                host   = parsed.hostname or ""
            except Exception:
                continue
            if not host or host in seen:
                continue
            # Skip private / loopback addresses
            if self._is_private_or_local(host):
                continue
            seen.add(host)

            # Port hints from dork/title/snippet content
            context   = " ".join(filter(None, [
                r.get("dork", ""),
                r.get("title", ""),
                r.get("snippet", ""),
                url,
            ]))
            hint_ports: List[int] = []
            for pattern, ports in DORK_PORT_HINTS:
                if pattern.search(context):
                    hint_ports.extend(p for p in ports if p not in hint_ports)

            hosts.append((host, url, hint_ports))

            if len(hosts) >= self.max_hosts:
                break

        return hosts

    @staticmethod
    def _is_private_or_local(host: str) -> bool:
        """Skip private IPs and localhost."""
        private = (
            "localhost", "127.0.0.1", "0.0.0.0",
            "::1", "192.168.", "10.", "172.16.",
            "172.17.", "172.18.", "172.19.", "172.20.",
            "172.21.", "172.22.", "172.23.", "172.24.",
            "172.25.", "172.26.", "172.27.", "172.28.",
            "172.29.", "172.30.", "172.31.",
        )
        return any(host.startswith(p) for p in private)

    # ── Port ordering ──────────────────────────────────────────────────────────

    def _ordered_ports(self, hint_ports: List[int]) -> List[int]:
        """Return scan port list with hint_ports first, rest shuffled."""
        base = [p for p in self.ports if p not in hint_ports]
        random.shuffle(base)
        return hint_ports + base

    # ── Single host scan ───────────────────────────────────────────────────────

    def _scan_host(self, host: str, source_url: str, hint_ports: List[int]) -> HostScanResult:
        """Scan all configured ports on one host (threaded internally)."""
        global _exit_requested, _skip_current

        ordered  = self._ordered_ports(hint_ports)
        result   = HostScanResult(host=host)
        t_start  = time.monotonic()

        port_q: queue.Queue = queue.Queue()
        for p in ordered:
            port_q.put(p)

        findings_buf: List[PortFinding] = []
        buf_lock = threading.Lock()

        def _worker():
            while True:
                if _exit_requested or _skip_current:
                    break
                try:
                    port = port_q.get_nowait()
                except queue.Empty:
                    break
                pdef = DB_PORT_MAP.get(port)
                if not pdef:
                    port_q.task_done()
                    continue
                finding = _scan_port(host, pdef, self.timeout, source_url)
                if finding:
                    with buf_lock:
                        findings_buf.append(finding)
                port_q.task_done()

        n_workers = min(self.threads, len(ordered))
        workers   = [
            threading.Thread(target=_worker, daemon=True)
            for _ in range(n_workers)
        ]
        for w in workers:
            w.start()
        port_q.join()

        result.findings  = sorted(
            findings_buf,
            key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(f.severity, 3)
        )
        result.scanned   = len(ordered)
        result.duration  = time.monotonic() - t_start
        return result

    # ── Main run ───────────────────────────────────────────────────────────────

    def run(self, results: List[dict]) -> "DBScanReport":
        """
        Run DB port scan on all unique hosts from the given result list.
        Returns a DBScanReport.
        """
        global _exit_requested, _skip_current

        hosts = self._extract_hosts(results)
        if not hosts:
            _log("[DBScan] No scannable hosts extracted from results.", style="yellow")
            return DBScanReport(host_results=[], stats=dict(self.stats))

        _log(
            f"[DBScan] Scanning {len(hosts)} host(s) × {len(self.ports)} port(s) "
            f"— timeout: {self.timeout}s  threads/host: {self.threads}",
            style="bold cyan"
        )

        host_scan_results: List[HostScanResult] = []

        for idx, (host, source_url, hint_ports) in enumerate(hosts, 1):
            if _exit_requested:
                _log("[DBScan] Exit requested — stopping scan.", style="bold red")
                break
            if _skip_current:
                _log("[DBScan] Skip requested — stopping scan.", style="yellow")
                _skip_current = False
                break

            _log(
                f"[DBScan] [{idx}/{len(hosts)}] {host}"
                + (f"  [dim](hints: {hint_ports})[/dim]" if hint_ports and _console else ""),
                style="cyan"
            )

            hsr = self._scan_host(host, source_url, hint_ports)
            host_scan_results.append(hsr)

            # Print per-host findings immediately
            _open_badge   = "[bold green][ Open   ][/bold green]"
            _closed_badge = "[bold red][ Closed ][/bold red]"

            for f in hsr.findings:
                if f.severity == "CRITICAL":
                    _log(
                        f"  {_open_badge} [bold magenta]⚠ CRITICAL[/bold magenta] "
                        f"{f.host}:{f.port} [{f.service}] — {f.detail[:120]}",
                        style=""
                    )
                elif f.severity == "HIGH":
                    _log(
                        f"  {_open_badge} [bold red]! HIGH[/bold red] "
                        f"{f.host}:{f.port} [{f.service}] — {f.detail[:120]}",
                        style=""
                    )
                else:
                    _log(
                        f"  {_open_badge} [yellow]~ MEDIUM[/yellow] "
                        f"{f.host}:{f.port} [{f.service}]",
                        style=""
                    )

            # Closed-port summary — one compact line instead of per-port spam
            _closed_cnt = hsr.scanned - len(hsr.open_ports)
            if _closed_cnt > 0:
                _log(
                    f"  {_closed_badge} [dim]{_closed_cnt} port(s) closed / filtered[/dim]",
                    style=""
                )

            # Update global stats
            self.stats["hosts_scanned"]  += 1
            self.stats["ports_scanned"]  += hsr.scanned
            self.stats["open_ports"]     += len(hsr.open_ports)
            self.stats["critical"]       += hsr.critical_count
            self.stats["high"]           += hsr.high_count
            self.stats["medium"]         += sum(
                1 for f in hsr.findings if f.severity == "MEDIUM"
            )

            # Stealth inter-host delay
            if self.stealth and idx < len(hosts):
                time.sleep(random.uniform(1.5, 3.5))

        return DBScanReport(
            host_results = host_scan_results,
            stats        = dict(self.stats),
        )


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DBScanReport:
    host_results: List[HostScanResult]
    stats:        dict = field(default_factory=dict)

    # ── Aggregated views ──────────────────────────────────────────────────────

    @property
    def critical_findings(self) -> List[PortFinding]:
        return [
            f for h in self.host_results
            for f in h.findings if f.severity == "CRITICAL"
        ]

    @property
    def high_findings(self) -> List[PortFinding]:
        return [
            f for h in self.host_results
            for f in h.findings if f.severity == "HIGH"
        ]

    @property
    def all_findings(self) -> List[PortFinding]:
        return [f for h in self.host_results for f in h.findings]

    @property
    def has_findings(self) -> bool:
        return bool(self.all_findings)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats":        self.stats,
            "hosts":        [h.to_dict() for h in self.host_results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ── Text summary (terminal) ───────────────────────────────────────────────

    def print_summary(self) -> None:
        stats = self.stats
        _log("\n[bold cyan]┌─[ DB Port Scan — Summary ][/bold cyan]", style="")
        _log(f"[bold cyan]│[/bold cyan]  Hosts scanned  : {stats.get('hosts_scanned', 0)}", style="")
        _log(f"[bold cyan]│[/bold cyan]  Ports scanned  : {stats.get('ports_scanned', 0)}", style="")
        _log(f"[bold cyan]│[/bold cyan]  Open ports     : {stats.get('open_ports', 0)}", style="")
        _log(f"[bold magenta]│[/bold magenta]  CRITICAL (no-auth): {stats.get('critical', 0)}", style="")
        _log(f"[bold red]│[/bold red]  HIGH           : {stats.get('high', 0)}", style="")
        _log(f"[bold yellow]│[/bold yellow]  MEDIUM         : {stats.get('medium', 0)}", style="")
        _log("[bold cyan]└─>[/bold cyan]", style="")

        if self.critical_findings:
            _log("\n[bold magenta]⚠ CRITICAL — Unauthenticated DB exposure:[/bold magenta]", style="")
            for f in self.critical_findings:
                _log(f"  {f.host}:{f.port}  [{f.service}]  {f.detail[:120]}", style="bold magenta")

    # ── Sqlmap-friendly TXT ───────────────────────────────────────────────────

    def to_txt_report(self) -> str:
        """
        Human-readable TXT report of open DB ports, usable as a
        reference list for follow-up tooling.
        """
        lines = [
            "# DorkEye DB Port Scan Report",
            f"# Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Hosts     : {self.stats.get('hosts_scanned', 0)}",
            f"# Open ports: {self.stats.get('open_ports', 0)}",
            f"# CRITICAL  : {self.stats.get('critical', 0)}  (no-auth confirmed)",
            f"# HIGH      : {self.stats.get('high', 0)}",
            "#",
            "# Severity legend:",
            "#   CRITICAL = unauthenticated access confirmed",
            "#   HIGH     = service confirmed, auth likely required",
            "#   MEDIUM   = port open, service unclear",
            "",
        ]
        for hsr in self.host_results:
            if not hsr.findings:
                continue
            lines.append(f"## Host: {hsr.host}  ({len(hsr.open_ports)} open port(s))")
            for f in hsr.findings:
                lines.append(
                    f"  [{f.severity:8}] {f.host}:{f.port:<6} {f.service:<18} "
                    f"{'NO-AUTH ' if f.no_auth else ''}{f.detail[:100]}"
                )
            lines.append("")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SAVE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def save_dbscan_report(report: DBScanReport, base_path: str) -> str:
    """
    Save DBScanReport alongside the main results file.
    Writes: <base>_dbscan_<ts>.json  and  <base>_dbscan_<ts>.txt
    Returns the JSON path.
    """
    from pathlib import Path as _Path

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = _Path(base_path).stem.replace("_dbscan", "")
    dump = _Path(base_path).parent

    # Ensure the output directory exists (e.g. Dump/ may not yet be created)
    dump.mkdir(parents=True, exist_ok=True)

    json_path = dump / f"{stem}_dbscan_{ts}.json"
    txt_path  = dump / f"{stem}_dbscan_{ts}.txt"

    json_path.write_text(report.to_json(), encoding="utf-8")
    txt_path.write_text(report.to_txt_report(), encoding="utf-8")

    _log(f"[DBScan] Report saved: {json_path}", style="bold green")
    _log(f"[DBScan] TXT report  : {txt_path}",  style="bold green")
    return str(json_path)


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(
        description="DorkEye DB Port Scanner v1.0 — standalone mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python db_portscan.py results.json\n"
            "  python db_portscan.py results.json --timeout 3 --threads 80\n"
            "  python db_portscan.py results.json --ports 3306 5432 27017 6379\n"
            "  python db_portscan.py results.json --stealth --max-hosts 50\n"
        ),
    )
    p.add_argument("results_file",
                   help="DorkEye JSON results file")
    p.add_argument("--timeout",   type=float, default=2.5,
                   help="TCP connect timeout in seconds (default: 2.5)")
    p.add_argument("--threads",   type=int,   default=60,
                   help="Worker threads per host (default: 60)")
    p.add_argument("--ports",     type=int,   nargs="+", default=None,
                   help="Port list to scan (default: all DB ports)")
    p.add_argument("--max-hosts", type=int,   default=200,
                   help="Max hosts to scan (default: 200)")
    p.add_argument("--stealth",   action="store_true",
                   help="Add inter-host delay (1.5–3.5s)")
    p.add_argument("--out",       type=str,   default=None,
                   help="Output base path (default: same dir as results file)")
    args = p.parse_args()

    src = args.results_file
    try:
        raw = json.loads(open(src, encoding="utf-8").read())
        results_data = raw if isinstance(raw, list) else raw.get("results", [])
    except Exception as e:
        print(f"[!] Cannot read '{src}': {e}", file=sys.stderr)
        sys.exit(1)

    if not results_data:
        print(f"[!] No results in '{src}'.", file=sys.stderr)
        sys.exit(1)

    agent  = DBPortScanAgent(
        timeout   = args.timeout,
        threads   = args.threads,
        ports     = args.ports,
        stealth   = args.stealth,
        max_hosts = args.max_hosts,
    )
    report = agent.run(results_data)
    report.print_summary()

    out_base = args.out or src
    save_dbscan_report(report, out_base)
