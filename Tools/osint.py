#!/usr/bin/env python3
"""
DorkEye OSINT Graph
Passive, keyless OSINT collection engine for the DorkEye Project.

Lives in: DorkEye/Tools/osint.py

Idea (inspired by Facepager's seed -> request -> child-nodes model):
  * You start from one or more SEED nodes (a domain, host, IP or URL).
  * Each node is passed through a CHAIN of steps. Every step queries a
    PASSIVE, KEYLESS public source and stores what it finds as CHILD nodes
    under the node that produced them.
  * The output of one node feeds the next request through <placeholders>,
    exactly like Facepager (e.g. a <objectid> or a <dns.A[0]> field).
  * Everything is stored in a small SQLite graph and can be exported to CSV.

Passive sources (NO personal API keys required):
  - crt.sh          domain  -> subdomains from Certificate Transparency logs
  - RDAP (rdap.org) domain/ip -> registrar, creation/expiry dates, nameservers
  - DNS-over-HTTPS  host    -> A / AAAA / MX / NS / TXT records (Cloudflare DoH)
  - Wayback CDX     domain  -> sample of historically archived URLs
  - HTTP meta       url     -> status code, Server header, <title>, security.txt
  - Shodan InternetDB ip    -> open ports, CPEs, known CVEs, hostnames (keyless)
  - Reverse DNS     ip      -> PTR hostname (via Cloudflare DoH)
  - IP meta         ip      -> ASN, org/ISP, country/city (ipwho.is, keyless)

v1.1 adds the IP-enrichment resolvers above: the IP nodes discovered in v1.0
are no longer dead ends — each is expanded with ports/vulns, reverse DNS and
ASN/geo, all from passive, keyless public endpoints.

These query public archives and registries, not the target itself, so the
collection stays on the passive-OSINT side and pairs naturally with the dorks
DorkEye already produces: hosts/URLs found by dorks become seeds here, and
hosts discovered here can be fed back into dorking.

Author: xPloits3c | DorkEye Project
"""

from __future__ import annotations

import csv
import ipaddress
import json
import os
import re
import socket
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

# ── Optional rich console (same pattern as the other DorkEye tools) ───────────
try:
    from rich.console import Console
    from rich.markup import escape as _re
    _console = Console()

    def _log(msg: str, style: str = "cyan") -> None:
        # style="" means msg already carries its own Rich markup.
        if style:
            _console.print(f"[{style}]{msg}[/{style}]")
        else:
            _console.print(msg)
except Exception:  # pragma: no cover
    _console = None

    def _re(s: str) -> str:
        return s

    def _log(msg: str, style: str = "") -> None:
        print(msg)


USER_AGENT = "DorkEye-OSINT/1.2 (+https://github.com/xPloits3c/dorkeye)"

# ── MetaByte extractors ───────────────────────────────────────────────────────
# MetaByte (xPloits3c/MetaByte) only extracts emails/phones/IPs/URLs from text
# and deduplicates them. Those parsers live natively in DorkEye's main module
# (dorkeye.py: mb_extract_*). When osint runs under DorkEye we reuse that single
# source; the local copies below are the same MetaByte v1.2 logic and are used
# only when osint.py runs standalone (main module not loaded).
import sys as _sys


def _mb_email(content):
    _main = _sys.modules.get("dorkeye")
    if _main is not None and hasattr(_main, "mb_extract_email"):
        return _main.mb_extract_email(content)
    return sorted(set(re.findall(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content or "")))


def _mb_phone(content):
    _main = _sys.modules.get("dorkeye")
    if _main is not None and hasattr(_main, "mb_extract_phone"):
        return _main.mb_extract_phone(content)
    nums = re.findall(r"\+?\d[\d\s\-]{6,}\d", content or "")
    return sorted(set(re.sub(r"\s+|-", "", n) for n in nums))


def _extract_contacts(text: str) -> Tuple[List[str], List[str]]:
    """Run MetaByte (or the built-in fallback) and sanity-filter the phones."""
    if not text:
        return [], []
    emails = [e.lower() for e in _mb_email(text)
              if not e.lower().endswith((".png", ".jpg", ".gif", ".svg", ".webp"))]
    phones = []
    for p in _mb_phone(text):
        digits = re.sub(r"\D", "", p)
        # Keep plausible phone numbers only (E.164 is 8–15 digits); this drops
        # years, IDs, hashes and other numeric noise MetaByte would also catch.
        if 8 <= len(digits) <= 15 and len(set(digits)) > 2:
            phones.append(p)
    return sorted(set(emails)), sorted(set(phones))

# ══════════════════════════════════════════════════════════════════════════════
#  [1] Graph node
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class OsintNode:
    """A single node in the OSINT graph."""
    objectid: str                       # the entity value (domain, host, ip, url…)
    objtype: str                        # entity type: domain|host|ip|url|record|whois|meta
    source: str = "seed"                # which resolver produced it
    parent_id: Optional[int] = None
    depth: int = 0
    status: str = "new"                 # new|ok|empty|error
    data: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None            # assigned by the DB
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def key(self) -> Tuple[str, str]:
        """Dedup key: an entity is unique by (type, value)."""
        return (self.objtype, self.objectid.lower().strip())


# ══════════════════════════════════════════════════════════════════════════════
#  [2] SQLite storage (the local DB / graph)
# ══════════════════════════════════════════════════════════════════════════════


class OsintDB:
    """Minimal SQLite-backed node store. One table, parent_id -> tree/graph."""

    def __init__(self, path: str, fresh: bool = False):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if fresh:
            # One run = one graph: start from an empty database so every seed
            # is expanded again and earlier targets don't leak into the report.
            for suffix in ("", "-journal", "-wal", "-shm"):
                try:
                    os.remove(path + suffix)
                except FileNotFoundError:
                    pass
        # check_same_thread=False: the engine inserts from worker threads but
        # serialises every write through self._lock below.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    objectid  TEXT NOT NULL,
                    objtype   TEXT NOT NULL,
                    source    TEXT,
                    depth     INTEGER DEFAULT 0,
                    status    TEXT,
                    response  TEXT,
                    ts        TEXT,
                    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent ON nodes(parent_id)"
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_entity "
                "ON nodes(objtype, objectid)"
            )
            self._conn.commit()

    def add(self, node: OsintNode) -> Optional[int]:
        """Insert a node. Returns its id, or None if the entity already exists."""
        with self._lock:
            try:
                cur = self._conn.execute(
                    "INSERT INTO nodes "
                    "(parent_id, objectid, objtype, source, depth, status, response, ts) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        node.parent_id,
                        node.objectid,
                        node.objtype,
                        node.source,
                        node.depth,
                        node.status,
                        json.dumps(node.data, ensure_ascii=False),
                        node.ts,
                    ),
                )
                self._conn.commit()
                node.id = cur.lastrowid
                return node.id
            except sqlite3.IntegrityError:
                # Entity (objtype, objectid) already collected — skip duplicate.
                return None

    def update_status(self, node_id: int, status: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE nodes SET status=?, response=? WHERE id=?",
                (status, json.dumps(data, ensure_ascii=False), node_id),
            )
            self._conn.commit()

    def all_nodes(self) -> List[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute("SELECT * FROM nodes ORDER BY id"))

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    def by_type(self) -> Dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT objtype, COUNT(*) c FROM nodes GROUP BY objtype"
            )
            return {r["objtype"]: r["c"] for r in rows}

    def export_csv(self, path: str) -> str:
        rows = self.all_nodes()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "parent_id", "depth", "objtype", "objectid", "source", "status", "response"])
            for r in rows:
                w.writerow([
                    r["id"], r["parent_id"], r["depth"], r["objtype"],
                    r["objectid"], r["source"], r["status"], r["response"],
                ])
        return path

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  [3] Placeholder resolution (the Facepager <field> mechanic, in miniature)
# ══════════════════════════════════════════════════════════════════════════════

_PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")


def dict_get_path(data: Any, path: str, default: str = "") -> str:
    """
    Resolve a dotted path with optional list indexes against nested JSON.
      "dns.A[0]"   -> data["dns"]["A"][0]
      "whois.name" -> data["whois"]["name"]
    A bare list with no index collapses to its first element.
    """
    cur = data
    for part in path.split("."):
        m = re.match(r"^([^\[\]]+)((?:\[\d+\])*)$", part)
        if not m:
            return default
        name, idx = m.group(1), m.group(2)
        if isinstance(cur, dict):
            cur = cur.get(name)
        else:
            return default
        for i in re.findall(r"\[(\d+)\]", idx):
            if isinstance(cur, list) and int(i) < len(cur):
                cur = cur[int(i)]
            else:
                return default
        if cur is None:
            return default
    if isinstance(cur, list):
        cur = cur[0] if cur else default
    return str(cur)


def resolve_placeholders(template: str, node: OsintNode) -> str:
    """Replace <objectid> and <field.path> tokens using the node's own data."""
    def _sub(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in ("objectid", "Object ID"):
            return node.objectid
        if key == "objtype":
            return node.objtype
        return dict_get_path(node.data, key, default="")
    return _PLACEHOLDER_RE.sub(_sub, template)


# ══════════════════════════════════════════════════════════════════════════════
#  [4] HTTP helper
# ══════════════════════════════════════════════════════════════════════════════


class Http:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    def get_json(self, url: str, **kw) -> Any:
        r = self._s.get(url, timeout=self.timeout, **kw)
        r.raise_for_status()
        return r.json()

    def get(self, url: str, **kw) -> requests.Response:
        return self._s.get(url, timeout=self.timeout, **kw)


# ══════════════════════════════════════════════════════════════════════════════
#  [5] Resolvers — one passive, keyless source each.
#     A resolver takes (node, http) and returns a list of child OsintNodes.
# ══════════════════════════════════════════════════════════════════════════════

Resolver = Callable[[OsintNode, Http], List[OsintNode]]

_PRIVATE_NET = re.compile(
    r"^(?:localhost$|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.|169\.254\.|::1$|fc|fd)"
)


def _is_private(host: str) -> bool:
    return bool(_PRIVATE_NET.match(host.lower().strip()))


_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)


def _is_valid_hostname(name: str) -> bool:
    """Reject malformed / non-hostname crt.sh noise (spaces, bad labels, …)."""
    return bool(_HOSTNAME_RE.match(name.strip().lower()))


def _ip_is_public(value: str) -> bool:
    """True only for a syntactically valid, globally routable IP address."""
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def _child(node: OsintNode, objectid: str, objtype: str, source: str,
           data: Optional[Dict[str, Any]] = None) -> OsintNode:
    return OsintNode(
        objectid=objectid.strip(),
        objtype=objtype,
        source=source,
        parent_id=node.id,
        depth=node.depth + 1,
        status="ok",
        data=data or {},
    )


def resolve_crtsh(node: OsintNode, http: Http) -> List[OsintNode]:
    """domain -> subdomains from crt.sh Certificate Transparency logs."""
    domain = resolve_placeholders("<objectid>", node)
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    out: List[OsintNode] = []
    try:
        data = http.get_json(url)
    except Exception as exc:
        node.data["crtsh_error"] = str(exc)
        return out
    seen = set()
    for entry in data if isinstance(data, list) else []:
        for name in str(entry.get("name_value", "")).splitlines():
            name = name.strip().lstrip("*.").lower()
            if not name or name in seen or name == domain:
                continue
            if not name.endswith("." + domain) and name != domain:
                continue
            if not _is_valid_hostname(name):
                continue
            seen.add(name)
            out.append(_child(node, name, "host", "crtsh",
                              {"issuer": entry.get("issuer_name", "")}))
    return out


def resolve_rdap(node: OsintNode, http: Http) -> List[OsintNode]:
    """domain/ip -> RDAP whois summary (registrar, dates, nameservers)."""
    target = resolve_placeholders("<objectid>", node)
    url = f"https://rdap.org/domain/{target}"
    try:
        data = http.get_json(url)
    except Exception as exc:
        node.data["rdap_error"] = str(exc)
        return []

    events = {e.get("eventAction"): e.get("eventDate")
              for e in data.get("events", []) if isinstance(e, dict)}
    registrar = ""
    registrar_id = ""
    for ent in data.get("entities", []) or []:
        roles = ent.get("roles", []) or []
        if "registrar" in roles:
            # Prefer the human-readable vCard name; the bare handle is just the
            # IANA registrar ID (e.g. "376"), which is useless on its own.
            registrar = _vcard_name(ent)
            registrar_id = ent.get("handle", "")
            if not registrar:
                for pid in ent.get("publicIds", []) or []:
                    if pid.get("type", "").lower().startswith("iana"):
                        registrar_id = pid.get("identifier", registrar_id)
                registrar = registrar_id
            break
    nameservers = [ns.get("ldhName", "") for ns in data.get("nameservers", []) or []]

    whois = {
        "registrar": registrar,
        "registrar_id": registrar_id,
        "registered": events.get("registration", ""),
        "expires": events.get("expiration", ""),
        "last_changed": events.get("last changed", ""),
        "status": data.get("status", []),
        "nameservers": nameservers,
    }
    whois_node = _child(node, f"whois:{target}", "whois", "rdap", whois)
    children = [whois_node]
    for ns in nameservers:
        if ns:
            children.append(_child(node, ns.lower(), "host", "rdap-ns", {}))

    # Contact emails / phones from the RDAP vCards (often redacted, but not
    # always — registrant/abuse contacts sometimes expose a real address).
    emails, phones = set(), set()
    for ent in data.get("entities", []) or []:
        e, p = _vcard_contacts(ent)
        emails.update(e)
        phones.update(p)
    whois["emails"] = sorted(emails)
    whois["phones"] = sorted(phones)
    for e in sorted(emails):
        children.append(_child(whois_node, e, "email", "rdap", {"on": target}))
    for p in sorted(phones):
        children.append(_child(whois_node, p, "phone", "rdap", {"on": target}))
    return children


def _vcard_contacts(entity: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Pull email + tel values out of an RDAP entity's jCard, MetaByte-filtered."""
    text_bits: List[str] = []
    try:
        for item in entity.get("vcardArray", [[], []])[1]:
            if item and item[0] in ("email", "tel"):
                text_bits.append(str(item[3]))
    except Exception:
        pass
    return _extract_contacts(" ".join(text_bits))


def _vcard_name(entity: Dict[str, Any]) -> str:
    try:
        for item in entity.get("vcardArray", [[], []])[1]:
            if item and item[0] == "fn":
                return str(item[3])
    except Exception:
        pass
    return ""


def resolve_dns(node: OsintNode, http: Http) -> List[OsintNode]:
    """host -> A / AAAA / MX / NS / TXT via Cloudflare DNS-over-HTTPS."""
    host = resolve_placeholders("<objectid>", node)
    if _is_private(host):
        return []
    records: Dict[str, List[str]] = {}
    for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
        try:
            data = http.get_json(
                f"https://cloudflare-dns.com/dns-query?name={host}&type={rtype}",
                headers={"Accept": "application/dns-json"},
            )
            answers = [a.get("data", "").strip('"')
                       for a in data.get("Answer", []) if isinstance(a, dict)]
            if answers:
                records[rtype] = answers
        except Exception:
            continue
    if not records:
        return []
    node.data.setdefault("dns", records)
    children: List[OsintNode] = []
    for ip in records.get("A", []) + records.get("AAAA", []):
        children.append(_child(node, ip, "ip", "dns", {}))
    return children


def resolve_wayback(node: OsintNode, http: Http) -> List[OsintNode]:
    """domain -> sample of archived URLs from the Wayback CDX API."""
    domain = resolve_placeholders("<objectid>", node)
    url = (
        f"https://web.archive.org/cdx/search/cdx?url={domain}/*"
        "&output=json&fl=original&collapse=urlkey&limit=40"
    )
    try:
        rows = http.get_json(url)
    except Exception as exc:
        node.data["wayback_error"] = str(exc)
        return []
    out: List[OsintNode] = []
    for row in rows[1:] if isinstance(rows, list) and rows else []:
        original = row[0] if isinstance(row, list) and row else None
        if original:
            out.append(_child(node, original, "url", "wayback", {}))
    return out


def resolve_http_meta(node: OsintNode, http: Http) -> List[OsintNode]:
    """url/host -> status, Server header, <title>, security.txt presence."""
    target = resolve_placeholders("<objectid>", node)
    if not target.startswith(("http://", "https://")):
        target = "https://" + target
    host = urlparse(target).netloc
    if _is_private(host):
        return []
    meta: Dict[str, Any] = {}
    try:
        r = http.get(target, allow_redirects=True)
        meta["status"] = r.status_code
        meta["server"] = r.headers.get("Server", "")
        meta["final_url"] = r.url
        body = r.text[:200000]
        m = re.search(r"<title[^>]*>(.*?)</title>", body[:20000],
                      re.IGNORECASE | re.DOTALL)
        meta["title"] = m.group(1).strip()[:200] if m else ""
    except Exception as exc:
        meta["error"] = str(exc)
        body = ""
    # security.txt (RFC 9116) — a passive, well-known public endpoint; also a
    # rich source of contact emails.
    sec_txt = ""
    try:
        base = f"{urlparse(target).scheme}://{host}"
        sr = http.get(base + "/.well-known/security.txt", allow_redirects=True)
        meta["security_txt"] = (sr.status_code == 200)
        if sr.status_code == 200:
            sec_txt = sr.text[:20000]
    except Exception:
        meta["security_txt"] = False

    children = [_child(node, f"meta:{target}", "meta", "http", meta)]
    # Harvest contacts from the page body + security.txt (MetaByte parsers).
    emails, phones = _extract_contacts(body + "\n" + sec_txt)
    meta["emails"] = emails
    meta["phones"] = phones
    for e in emails:
        children.append(_child(node, e, "email", "http", {"on": host}))
    for p in phones:
        children.append(_child(node, p, "phone", "http", {"on": host}))
    return children


# ── v1.1 IP-enrichment resolvers (all passive, all keyless) ───────────────────


def resolve_internetdb(node: OsintNode, http: Http) -> List[OsintNode]:
    """
    ip -> Shodan InternetDB: open ports, CPEs, known CVEs and hostnames.
    This is Shodan's *passive* free endpoint (no key, no active scan): it only
    returns what Shodan already observed. Private/invalid IPs are skipped.
    """
    ip = resolve_placeholders("<objectid>", node)
    if not _ip_is_public(ip):
        return []
    try:
        data = http.get_json(f"https://internetdb.shodan.io/{ip}")
    except requests.exceptions.HTTPError as exc:
        # 404 = IP simply not in Shodan's dataset — normal, not an error.
        if getattr(exc.response, "status_code", None) != 404:
            node.data["internetdb_error"] = str(exc)
        return []
    except Exception as exc:
        node.data["internetdb_error"] = str(exc)
        return []

    node.data["ports"] = data.get("ports", [])
    node.data["cpes"] = data.get("cpes", [])
    node.data["vulns"] = data.get("vulns", [])
    children: List[OsintNode] = []
    seen = set()
    for hn in data.get("hostnames", []) or []:
        hn = str(hn).strip().lower()
        if hn and hn not in seen and _is_valid_hostname(hn):
            seen.add(hn)
            children.append(_child(node, hn, "host", "internetdb", {}))
    return children


def resolve_ptr(node: OsintNode, http: Http) -> List[OsintNode]:
    """ip -> reverse-DNS (PTR) hostname via Cloudflare DoH."""
    ip = resolve_placeholders("<objectid>", node)
    if not _ip_is_public(ip):
        return []
    try:
        pointer = ipaddress.ip_address(ip).reverse_pointer
    except ValueError:
        return []
    try:
        data = http.get_json(
            f"https://cloudflare-dns.com/dns-query?name={pointer}&type=PTR",
            headers={"Accept": "application/dns-json"},
        )
    except Exception:
        return []
    children: List[OsintNode] = []
    seen = set()
    for ans in data.get("Answer", []) or []:
        name = str(ans.get("data", "")).strip().rstrip(".").lower()
        if name and name not in seen and _is_valid_hostname(name):
            seen.add(name)
            node.data.setdefault("ptr", []).append(name)
            children.append(_child(node, name, "host", "ptr", {}))
    return children


def resolve_ipmeta(node: OsintNode, http: Http) -> List[OsintNode]:
    """ip -> ASN, org/ISP and country/city via ipwho.is (keyless). Emits an ASN node."""
    ip = resolve_placeholders("<objectid>", node)
    if not _ip_is_public(ip):
        return []
    try:
        data = http.get_json(f"https://ipwho.is/{ip}")
    except Exception as exc:
        node.data["ipmeta_error"] = str(exc)
        return []
    if not data.get("success", False):
        return []
    conn = data.get("connection", {}) or {}
    node.data["geo"] = {
        "country": data.get("country", ""),
        "country_code": data.get("country_code", ""),
        "city": data.get("city", ""),
    }
    node.data["asn"] = conn.get("asn", "")
    node.data["org"] = conn.get("org", "") or conn.get("isp", "")
    asn = conn.get("asn", "")
    if asn:
        asn_id = f"AS{asn}"
        return [_child(node, asn_id, "asn", "ipmeta", {
            "org": conn.get("org", ""),
            "isp": conn.get("isp", ""),
            "domain": conn.get("domain", ""),
        })]
    return []


# Registry of available sources.
RESOLVERS: Dict[str, Resolver] = {
    "crtsh": resolve_crtsh,
    "rdap": resolve_rdap,
    "dns": resolve_dns,
    "wayback": resolve_wayback,
    "http": resolve_http_meta,
    "internetdb": resolve_internetdb,
    "ptr": resolve_ptr,
    "ipmeta": resolve_ipmeta,
}


# ══════════════════════════════════════════════════════════════════════════════
#  [6] Chains — ordered steps. Each step runs a source over nodes of a type.
# ══════════════════════════════════════════════════════════════════════════════

# A step: {"source": <name>, "on": [<objtype>, ...]}  (which node types to expand)
BUILTIN_CHAINS: Dict[str, List[Dict[str, Any]]] = {
    # Fast, registry/CT only — good default on low-RAM devices.
    "recon-basic": [
        {"source": "rdap",  "on": ["domain"]},
        {"source": "crtsh", "on": ["domain"]},
        {"source": "dns",   "on": ["domain", "host"]},
    ],
    # recon-basic + IP enrichment: every discovered IP is expanded with
    # Shodan InternetDB (ports/CVEs), reverse DNS and ASN/geo. Keyless, passive.
    "recon-ip": [
        {"source": "rdap",       "on": ["domain"]},
        {"source": "crtsh",      "on": ["domain"]},
        {"source": "dns",        "on": ["domain", "host"]},
        {"source": "internetdb", "on": ["ip"]},
        {"source": "ptr",        "on": ["ip"]},
        {"source": "ipmeta",     "on": ["ip"]},
    ],
    # recon-ip + contact harvesting: probes discovered hosts over HTTP and mines
    # emails/phones from page bodies, security.txt and whois (MetaByte parsers).
    "recon-contacts": [
        {"source": "rdap",       "on": ["domain"]},
        {"source": "crtsh",      "on": ["domain"]},
        {"source": "dns",        "on": ["domain", "host"]},
        {"source": "internetdb", "on": ["ip"]},
        {"source": "ipmeta",     "on": ["ip"]},
        {"source": "http",       "on": ["host", "domain"]},
    ],
    # Adds archived URLs and a light live-meta probe of discovered hosts.
    "recon-passive": [
        {"source": "rdap",       "on": ["domain"]},
        {"source": "crtsh",      "on": ["domain"]},
        {"source": "dns",        "on": ["domain", "host"]},
        {"source": "wayback",    "on": ["domain"]},
        {"source": "http",       "on": ["host"]},
        {"source": "internetdb", "on": ["ip"]},
        {"source": "ptr",        "on": ["ip"]},
        {"source": "ipmeta",     "on": ["ip"]},
    ],
}


def default_db_path(seeds: List[str], dump_dir: str = "Dump") -> str:
    """Per-run default DB path: Dump/osint_<first seed>_<YYYYmmdd_HHMMSS>.sqlite."""
    first = str(seeds[0]) if seeds else "graph"
    host = urlparse(first).netloc if "://" in first else first
    slug = re.sub(r"[^a-z0-9.-]+", "_", host.lower()).strip("._-")[:40] or "graph"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(dump_dir, f"osint_{slug}_{stamp}.sqlite")


def load_chain(name_or_path: str) -> List[Dict[str, Any]]:
    """Load a built-in chain by name, or a custom chain from a JSON file."""
    if name_or_path in BUILTIN_CHAINS:
        return BUILTIN_CHAINS[name_or_path]
    if os.path.isfile(name_or_path):
        with open(name_or_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("chain", data) if isinstance(data, dict) else data
    raise ValueError(
        f"Unknown chain '{name_or_path}'. "
        f"Built-in: {', '.join(BUILTIN_CHAINS)} — or pass a .json file path."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  [7] Report object (mirrors db_portscan's report/save contract)
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class OsintReport:
    seeds: List[str]
    chain: str
    db_path: str
    counts: Dict[str, int]
    total: int
    started: str
    finished: str

    def print_summary(self) -> None:
        _log("\n┌─[ OSINT Graph — summary ]", style="bold cyan")
        _log(f"│  Seeds   : {', '.join(self.seeds) or '-'}", style="cyan")
        _log(f"│  Chain   : {self.chain}", style="cyan")
        _log(f"│  Nodes   : {self.total}", style="cyan")
        for t, c in sorted(self.counts.items(), key=lambda kv: -kv[1]):
            _log(f"│    {t:<8}: {c}", style="dim")
        _log(f"└─ DB → {self.db_path}", style="bold green")


def save_osint_report(report: OsintReport, base_path: str) -> str:
    """Write a JSON summary next to the SQLite DB; returns the path written."""
    os.makedirs(os.path.dirname(os.path.abspath(base_path)), exist_ok=True)
    out = base_path if base_path.lower().endswith(".json") else base_path + ".json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report.__dict__, fh, indent=2, ensure_ascii=False)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  [8] The engine
# ══════════════════════════════════════════════════════════════════════════════


class OsintGraphAgent:
    """
    BFS graph walker. Seeds go in, the chain is applied level by level, every
    discovery is stored as a child node. A small thread pool parallelises the
    network calls of a single step; defaults stay low for low-RAM devices.
    """

    def __init__(
        self,
        db_path: str = "Dump/osint_graph.sqlite",
        chain: str = "recon-basic",
        threads: int = 2,
        timeout: float = 15.0,
        max_nodes: int = 2000,
        rate: float = 0.5,
        fresh: bool = True,
    ):
        # Load the chain first: an invalid chain must not wipe an existing DB.
        self.chain_name = chain
        self.chain = load_chain(chain)
        self.db = OsintDB(db_path, fresh=fresh)
        self.threads = max(1, int(threads))
        self.http = Http(timeout=timeout)
        self.max_nodes = max_nodes
        self.rate = rate                      # min seconds between calls per worker
        self._emitted = 0
        self._lock = threading.Lock()

    # -- seeding ---------------------------------------------------------------
    @staticmethod
    def classify_seed(value: str) -> Tuple[str, str]:
        """Guess the entity type of a raw seed string."""
        v = value.strip()
        if v.startswith(("http://", "https://")):
            return (urlparse(v).netloc, "domain")
        try:
            socket.inet_aton(v)
            return (v, "ip")
        except OSError:
            pass
        return (v.lower(), "domain")

    def seed(self, raw_seeds: List[str]) -> List[OsintNode]:
        nodes: List[OsintNode] = []
        for raw in raw_seeds:
            objectid, objtype = self.classify_seed(raw)
            if not objectid:
                continue
            n = OsintNode(objectid=objectid, objtype=objtype, source="seed", depth=0)
            if self.db.add(n) is not None:
                nodes.append(n)
        return nodes

    @staticmethod
    def seeds_from_results(results: List[Dict[str, Any]]) -> List[str]:
        """Extract unique hostnames from DorkEye search results (the bridge)."""
        seeds: List[str] = []
        seen = set()
        for r in results or []:
            url = r.get("url") or r.get("href") or ""
            host = urlparse(url).netloc if "://" in url else url
            host = host.split("@")[-1].split(":")[0].strip().lower()
            if host and host not in seen and not _is_private(host):
                seen.add(host)
                seeds.append(host)
        return seeds

    # -- running ---------------------------------------------------------------
    def _expand_node(self, node: OsintNode, source: str) -> int:
        resolver = RESOLVERS.get(source)
        if resolver is None:
            return 0
        time.sleep(self.rate)
        try:
            children = resolver(node, self.http)
        except Exception as exc:
            _log(f"[osint] {source} failed on {_re(node.objectid)}: {_re(str(exc))}",
                 style="yellow")
            return 0
        # Persist any data the resolver stored on the parent (e.g. dns records).
        if node.id is not None:
            self.db.update_status(node.id, "ok", node.data)
        added = 0
        for ch in children:
            with self._lock:
                if self._emitted >= self.max_nodes:
                    break
                if self.db.add(ch) is not None:
                    self._emitted += 1
                    added += 1
        return added

    def run(self, raw_seeds: List[str]) -> OsintReport:
        started = datetime.now(timezone.utc).isoformat()
        seed_nodes = self.seed(raw_seeds)
        self._emitted = len(seed_nodes)
        _log(f"[osint] {len(seed_nodes)} seed node(s) · chain '{self.chain_name}' · "
             f"{self.threads} thread(s)", style="bold cyan")

        # Nodes available for expansion, keyed by type. Start with the seeds.
        frontier: List[OsintNode] = list(seed_nodes)

        for step in self.chain:
            source = step.get("source")
            on_types = set(step.get("on", []))
            targets = [n for n in frontier if n.objtype in on_types]
            if not targets:
                continue
            _log(f"[osint] step '{source}' → {len(targets)} node(s)", style="cyan")

            produced: List[OsintNode] = []
            q: "Queue[OsintNode]" = Queue()
            for t in targets:
                q.put(t)

            def worker() -> None:
                while True:
                    try:
                        n = q.get_nowait()
                    except Empty:
                        return
                    self._expand_node(n, source)
                    q.task_done()

            pool = [threading.Thread(target=worker, daemon=True)
                    for _ in range(min(self.threads, len(targets)))]
            for th in pool:
                th.start()
            for th in pool:
                th.join()

            # Rebuild the frontier from the DB so later steps see new nodes.
            frontier = self._load_frontier()
            if self._emitted >= self.max_nodes:
                _log(f"[osint] node cap {self.max_nodes} reached — stopping.",
                     style="yellow")
                break

        finished = datetime.now(timezone.utc).isoformat()
        report = OsintReport(
            seeds=raw_seeds,
            chain=self.chain_name,
            db_path=self.db.path,
            counts=self.db.by_type(),
            total=self.db.count(),
            started=started,
            finished=finished,
        )
        return report

    def _load_frontier(self) -> List[OsintNode]:
        nodes: List[OsintNode] = []
        for r in self.db.all_nodes():
            try:
                data = json.loads(r["response"] or "{}")
            except Exception:
                data = {}
            nodes.append(OsintNode(
                objectid=r["objectid"], objtype=r["objtype"], source=r["source"],
                parent_id=r["parent_id"], depth=r["depth"], status=r["status"],
                data=data, id=r["id"], ts=r["ts"],
            ))
        return nodes

    def export_csv(self, path: str) -> str:
        return self.db.export_csv(path)

    def build_graph(self) -> Dict[str, Any]:
        return build_graph(self.db)

    def close(self) -> None:
        self.db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  [9] Correlation / pivoting graph (v2)
#     Reconstructs a richer graph than the raw parent->child tree: shared-IP and
#     shared-ASN relationships are recovered from each node's stored data, so an
#     IP hosting several subdomains shows up as a pivot even though it is stored
#     only once (unique entity index).
# ══════════════════════════════════════════════════════════════════════════════

# Subdomain keywords worth surfacing in the report (light triage).
_INTERESTING = (
    "dev", "staging", "stage", "test", "qa", "uat", "admin", "vpn", "git",
    "gitlab", "jenkins", "ci", "api", "internal", "intranet", "corp", "old",
    "legacy", "backup", "bak", "db", "sql", "jira", "confluence", "portal",
    "dashboard", "grafana", "kibana", "s3", "beta", "demo", "mail", "owa",
)


def _eid(objtype: str, objectid: str) -> str:
    """Stable graph node id = type:value."""
    return f"{objtype}:{objectid.lower().strip()}"


def _host_is_interesting(host: str) -> bool:
    label = host.split(".")[0].lower()
    return label in _INTERESTING or any(host.lower().startswith(k + ".") for k in _INTERESTING)


def build_graph(db: "OsintDB") -> Dict[str, Any]:
    """
    Build a correlation graph from the stored nodes.
    Returns: {nodes, edges, clusters, findings, counts}.
    """
    rows = db.all_nodes()
    id2entity: Dict[int, str] = {}
    nodes: Dict[str, Dict[str, Any]] = {}
    parsed: List[Dict[str, Any]] = []

    for r in rows:
        try:
            data = json.loads(r["response"] or "{}")
        except Exception:
            data = {}
        ent = _eid(r["objtype"], r["objectid"])
        id2entity[r["id"]] = ent
        nodes.setdefault(ent, {
            "id": ent, "type": r["objtype"], "label": r["objectid"],
            "source": r["source"], "data": data,
        })
        parsed.append({"row_id": r["id"], "parent_id": r["parent_id"],
                       "type": r["objtype"], "objectid": r["objectid"],
                       "ent": ent, "data": data})

    edges: List[Dict[str, str]] = []
    seen_edges: set = set()

    def add_edge(src: str, dst: str, rel: str) -> None:
        if src == dst or src not in nodes or dst not in nodes:
            return
        k = (src, dst, rel)
        if k in seen_edges:
            return
        seen_edges.add(k)
        edges.append({"src": src, "dst": dst, "rel": rel})

    # 1) Tree edges (parent -> child).
    for p in parsed:
        if p["parent_id"] and p["parent_id"] in id2entity:
            add_edge(id2entity[p["parent_id"]], p["ent"], "child")

    # 2) resolves: host/domain -> ip, recovered from stored A/AAAA records.
    #    This is what captures SHARED IPs across different hosts.
    ip_to_hosts: Dict[str, set] = defaultdict(set)
    for p in parsed:
        if p["type"] in ("host", "domain"):
            dns = (p["data"].get("dns") or {})
            for ip in (dns.get("A", []) or []) + (dns.get("AAAA", []) or []):
                ip_ent = _eid("ip", ip)
                if ip_ent in nodes:
                    add_edge(p["ent"], ip_ent, "resolves")
                    ip_to_hosts[ip].add(p["objectid"].lower())

    # 3) announced_by: ip -> asn, from stored data.asn.
    asn_to_ips: Dict[str, set] = defaultdict(set)
    for p in parsed:
        if p["type"] == "ip" and p["data"].get("asn"):
            asn_ent = _eid("asn", f"AS{p['data']['asn']}")
            if asn_ent in nodes:
                add_edge(p["ent"], asn_ent, "announced_by")
                asn_to_ips[f"AS{p['data']['asn']}"].add(p["objectid"])

    # 4) nameserver edges from whois data.
    for p in parsed:
        if p["type"] in ("whois", "domain"):
            for ns in (p["data"].get("nameservers") or []):
                ns_ent = _eid("host", str(ns).lower().rstrip("."))
                if ns_ent in nodes:
                    add_edge(p["ent"], ns_ent, "ns")

    # ── Clusters (the pivots) ────────────────────────────────────────────────
    shared_ip = sorted(
        ({"ip": ip, "hosts": sorted(h)} for ip, h in ip_to_hosts.items() if len(h) >= 2),
        key=lambda c: -len(c["hosts"]),
    )
    asn_clusters = sorted(
        ({"asn": a, "org": next((nodes[_eid('asn', a)]["data"].get("org", "")
                                 for _ in [0]), ""), "ips": sorted(i)}
         for a, i in asn_to_ips.items() if len(i) >= 1),
        key=lambda c: -len(c["ips"]),
    )

    # ── Findings (light triage) ──────────────────────────────────────────────
    vulnerable = []
    open_ports: Dict[int, int] = defaultdict(int)
    for p in parsed:
        if p["type"] == "ip":
            for port in (p["data"].get("ports") or []):
                open_ports[port] += 1
            vulns = p["data"].get("vulns") or []
            if vulns:
                vulnerable.append({"ip": p["objectid"], "vulns": sorted(vulns),
                                   "ports": p["data"].get("ports", [])})
    interesting_hosts = sorted({
        p["objectid"].lower() for p in parsed
        if p["type"] == "host" and _host_is_interesting(p["objectid"])
    })

    findings = {
        "vulnerable_ips": vulnerable,
        "interesting_hosts": interesting_hosts,
        "top_ports": sorted(open_ports.items(), key=lambda kv: -kv[1])[:15],
    }

    counts: Dict[str, int] = defaultdict(int)
    for n in nodes.values():
        counts[n["type"]] += 1

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "clusters": {"shared_ip": shared_ip, "asn": asn_clusters},
        "findings": findings,
        "counts": dict(counts),
    }


# ── GraphML export (Gephi / yEd / Cytoscape) ──────────────────────────────────


def export_graphml(graph: Dict[str, Any], path: str) -> str:
    """Write the correlation graph as GraphML for Gephi/yEd/Cytoscape."""
    import xml.sax.saxutils as sx

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="d_type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="d_label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="d_rel" for="edge" attr.name="relation" attr.type="string"/>',
        '  <graph edgedefault="directed">',
    ]
    for n in graph["nodes"]:
        out.append(f'    <node id={sx.quoteattr(n["id"])}>')
        out.append(f'      <data key="d_type">{sx.escape(str(n["type"]))}</data>')
        out.append(f'      <data key="d_label">{sx.escape(str(n["label"]))}</data>')
        out.append('    </node>')
    for i, e in enumerate(graph["edges"]):
        out.append(
            f'    <edge id="e{i}" source={sx.quoteattr(e["src"])} '
            f'target={sx.quoteattr(e["dst"])}>'
        )
        out.append(f'      <data key="d_rel">{sx.escape(str(e["rel"]))}</data>')
        out.append('    </edge>')
    out.append('  </graph>')
    out.append('</graphml>')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    return path


# ══════════════════════════════════════════════════════════════════════════════
#  [10] Self-contained HTML report (offline; in-browser export to other formats)
# ══════════════════════════════════════════════════════════════════════════════


def render_html(report: "OsintReport", graph: Dict[str, Any],
                sqlite_b64: str = "") -> str:
    """
    Build a single self-contained dark-theme HTML report. All node/edge data is
    embedded as JSON, so the in-page buttons can export JSON / CSV / TXT /
    GraphML client-side without any server or network. When sqlite_b64 is given,
    the SQLite database is embedded too and downloadable from the page.
    """
    payload = {
        "meta": {
            "seeds": report.seeds, "chain": report.chain,
            "total": report.total, "started": report.started,
            "finished": report.finished,
        },
        "nodes": graph["nodes"], "edges": graph["edges"],
        "clusters": graph["clusters"], "findings": graph["findings"],
        "counts": graph["counts"],
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    f = graph["findings"]
    vuln_rows = "".join(
        f"<tr><td>{_h(v['ip'])}</td><td>{_h(', '.join(v['vulns']))}</td>"
        f"<td>{_h(', '.join(map(str, v['ports'])))}</td></tr>"
        for v in f["vulnerable_ips"]
    ) or '<tr><td colspan="3" class="dim">none</td></tr>'
    ihosts = "".join(f"<span class=tag>{_h(h)}</span>" for h in f["interesting_hosts"]) \
        or '<span class="dim">none</span>'
    ports = "".join(f"<span class=tag>{_h(p)}<small>×{_h(c)}</small></span>"
                    for p, c in f["top_ports"]) or '<span class="dim">none</span>'
    shared = "".join(
        f"<tr><td>{_h(c['ip'])}</td><td>{len(c['hosts'])}</td>"
        f"<td>{_h(', '.join(c['hosts']))}</td></tr>"
        for c in graph["clusters"]["shared_ip"]
    ) or '<tr><td colspan="3" class="dim">no shared-IP pivots</td></tr>'
    asn_rows = "".join(
        f"<tr><td>{_h(c['asn'])}</td><td>{_h(c.get('org',''))}</td>"
        f"<td>{len(c['ips'])}</td></tr>"
        for c in graph["clusters"]["asn"]
    ) or '<tr><td colspan="3" class="dim">none</td></tr>'
    counts = " · ".join(f"{k}: <b>{v}</b>" for k, v in sorted(graph["counts"].items()))

    # Full IP table — every IP node with its enrichment (fixes "not all IPs shown").
    ip_rows = ""
    for n in graph["nodes"]:
        if n["type"] != "ip":
            continue
        d = n.get("data", {})
        geo = d.get("geo", {}) or {}
        ip_rows += (
            f"<tr><td>{_h(n['label'])}</td>"
            f"<td>{_h(', '.join(map(str, d.get('ports', []))))}</td>"
            f"<td>{_h(('AS'+str(d['asn'])) if d.get('asn') else '')}</td>"
            f"<td>{_h(d.get('org',''))}</td>"
            f"<td>{_h(geo.get('country_code','') or geo.get('country',''))}</td>"
            f"<td>{_h(', '.join(d.get('ptr', [])))}</td></tr>"
        )
    ip_rows = ip_rows or '<tr><td colspan="6" class="dim">no IP nodes</td></tr>'

    # Contacts — email / phone nodes harvested via MetaByte.
    emails = sorted({n["label"] for n in graph["nodes"] if n["type"] == "email"})
    phones = sorted({n["label"] for n in graph["nodes"] if n["type"] == "phone"})
    emails_html = "".join(f"<span class=tag>{_h(e)}</span>" for e in emails) \
        or '<span class="dim">none</span>'
    phones_html = "".join(f"<span class=tag>{_h(p)}</span>" for p in phones) \
        or '<span class="dim">none</span>'

    sqlite_btn = (
        '<button onclick="dl(\'sqlite\')">⬇ SQLite</button>' if sqlite_b64 else ''
    )
    sqlite_script = (
        f'<script id="sqlite" type="application/octet-stream">{sqlite_b64}</script>'
        if sqlite_b64 else ''
    )

    return _HTML_TEMPLATE.format(
        seeds=_h(", ".join(report.seeds)), chain=_h(report.chain),
        total=report.total, finished=_h(report.finished),
        counts=counts, vuln_rows=vuln_rows, ihosts=ihosts, ports=ports,
        shared=shared, asn_rows=asn_rows, ip_rows=ip_rows,
        emails_html=emails_html, phones_html=phones_html,
        sqlite_btn=sqlite_btn, sqlite_script=sqlite_script,
        data_json=data_json,
    )


def _h(s: Any) -> str:
    import html
    return html.escape(str(s))


def build_osint_html(report: "OsintReport", graph: Dict[str, Any],
                     db_path: Optional[str] = None) -> str:
    """Return the OSINT report HTML string (embedding the SQLite DB when small)."""
    sqlite_b64 = ""
    if db_path and os.path.isfile(db_path):
        try:
            import base64
            if os.path.getsize(db_path) <= 8 * 1024 * 1024:   # cap embed at 8 MB
                with open(db_path, "rb") as dbf:
                    sqlite_b64 = base64.b64encode(dbf.read()).decode("ascii")
        except Exception:
            sqlite_b64 = ""
    return render_html(report, graph, sqlite_b64)


def write_html_report(report: "OsintReport", graph: Dict[str, Any], path: str,
                      db_path: Optional[str] = None) -> str:
    """Write the OSINT HTML report to disk."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_osint_html(report, graph, db_path))
    return path


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DorkEye OSINT Report</title>
<style>
:root{{--bg:#000;--panel:rgba(0,12,0,0.85);--line:#00aa2a;--fg:#00ff41;--accent:#00ff41;
--accent2:#00cc99;--warn:#ffaa00;--crit:#ff3344;--dim:#009922;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;padding:24px}}
h1{{font-size:20px;margin:0 0 2px;color:var(--accent);letter-spacing:.5px}}
h2{{font-size:14px;margin:26px 0 10px;color:var(--accent2);
border-bottom:1px solid var(--line);padding-bottom:6px;text-transform:uppercase;letter-spacing:1px}}
.sub{{color:var(--dim);margin:0 0 14px}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}}
.bar button{{background:var(--panel);color:var(--fg);border:1px solid var(--line);
border-radius:7px;padding:7px 12px;cursor:pointer;font:inherit}}
.bar button:hover{{border-color:var(--accent);color:var(--accent)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}}
.k{{color:var(--dim)}} .b{{font-weight:700}}
table{{width:100%;border-collapse:collapse;margin-top:6px}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);
vertical-align:top;word-break:break-all}}
th{{color:var(--dim);font-weight:600}}
.tag{{display:inline-block;background:#0f1b16;border:1px solid var(--line);
border-radius:6px;padding:2px 8px;margin:2px}}
.tag small{{color:var(--dim)}}
.dim{{color:var(--dim)}}
.crit{{color:var(--crit)}} .warn{{color:var(--warn)}}
#svg{{width:100%;height:520px;background:var(--panel);border:1px solid var(--line);border-radius:10px}}
.legend span{{margin-right:14px}}
.footer{{margin-top:28px;color:var(--dim);font-size:12px}}
</style></head><body>
<h1>◢ DorkEye — OSINT Correlation Report</h1>
<p class="sub">Seeds: <b>{seeds}</b> · Chain: <b>{chain}</b> · Nodes: <b>{total}</b> · {finished}</p>

<div class="bar">
  <button onclick="dl('json')">⬇ JSON</button>
  <button onclick="dl('csv')">⬇ CSV (nodes)</button>
  <button onclick="dl('edges')">⬇ CSV (edges)</button>
  <button onclick="dl('txt')">⬇ TXT summary</button>
  <button onclick="dl('graphml')">⬇ GraphML</button>
  {sqlite_btn}
</div>

<div class="card"><span class="k">Entity counts</span><br>{counts}</div>

<h2>Graph</h2>
<div class="legend card" style="padding:8px 14px">
<span style="color:#4aa3ff">● domain</span><span style="color:#39d98a">● host</span>
<span style="color:#ffb454">● ip</span><span style="color:#ff5d6c">● asn</span>
<span style="color:#9b8cff">● whois</span><span style="color:#f78fb3">● email</span>
<span style="color:#ffd93d">● phone</span><span style="color:#6b7d7a">● other</span>
</div>
<svg id="svg"></svg>

<h2>Findings</h2>
<div class="grid">
  <div class="card"><div class="k">Interesting subdomains</div><div style="margin-top:6px">{ihosts}</div></div>
  <div class="card"><div class="k">Top open ports</div><div style="margin-top:6px">{ports}</div></div>
</div>
<div class="card" style="margin-top:12px">
  <div class="k">IPs with known CVEs (Shodan InternetDB)</div>
  <table><tr><th>IP</th><th>CVEs</th><th>Ports</th></tr>{vuln_rows}</table>
</div>

<h2>Contacts (MetaByte)</h2>
<div class="grid">
  <div class="card"><div class="k">Emails</div><div style="margin-top:6px">{emails_html}</div></div>
  <div class="card"><div class="k">Phones</div><div style="margin-top:6px">{phones_html}</div></div>
</div>

<h2>All IPs</h2>
<div class="card"><table>
<tr><th>IP</th><th>Ports</th><th>ASN</th><th>Org</th><th>CC</th><th>PTR</th></tr>
{ip_rows}</table></div>

<h2>Pivots — shared IP</h2>
<div class="card"><table><tr><th>IP</th><th>#hosts</th><th>Hosts</th></tr>{shared}</table></div>

<h2>ASN clusters</h2>
<div class="card"><table><tr><th>ASN</th><th>Org</th><th>#IPs</th></tr>{asn_rows}</table></div>

<p class="footer">Generated by DorkEye OSINT · data embedded below · all exports run in your browser, offline.</p>

<script id="data" type="application/json">{data_json}</script>
{sqlite_script}
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const COLOR = {{domain:'#4aa3ff',host:'#39d98a',ip:'#ffb454',asn:'#ff5d6c',
whois:'#9b8cff',email:'#f78fb3',phone:'#ffd93d',url:'#6b7d7a',meta:'#6b7d7a'}};

// --- lightweight columnar graph (no external libs, deterministic layout) ---
(function draw(){{
  const svg=document.getElementById('svg');
  const W=svg.clientWidth||900,H=520;
  const order=['domain','whois','host','ip','asn','email','phone','url','meta'];
  const cols={{}}; order.forEach((t,i)=>cols[t]=i);
  const byType={{}}; DATA.nodes.forEach(n=>(byType[n.type]=byType[n.type]||[]).push(n));
  const used=order.filter(t=>byType[t]&&byType[t].length);
  const colW=W/Math.max(used.length,1);
  const pos={{}};
  used.forEach((t,ci)=>{{
    const arr=byType[t], n=arr.length;
    arr.forEach((nd,ri)=>{{
      pos[nd.id]={{x:colW*ci+colW/2, y:H*(ri+1)/(n+1)}};
    }});
  }});
  const NS='http://www.w3.org/2000/svg';
  DATA.edges.forEach(e=>{{
    const a=pos[e.src],b=pos[e.dst]; if(!a||!b)return;
    const l=document.createElementNS(NS,'line');
    l.setAttribute('x1',a.x);l.setAttribute('y1',a.y);
    l.setAttribute('x2',b.x);l.setAttribute('y2',b.y);
    l.setAttribute('stroke',e.rel==='resolves'?'#2b4a3f':'#1e2a2c');
    l.setAttribute('stroke-width',e.rel==='resolves'?1.4:0.8);
    svg.appendChild(l);
  }});
  DATA.nodes.forEach(nd=>{{
    const p=pos[nd.id]; if(!p)return;
    const c=document.createElementNS(NS,'circle');
    c.setAttribute('cx',p.x);c.setAttribute('cy',p.y);c.setAttribute('r',4.5);
    c.setAttribute('fill',COLOR[nd.type]||'#6b7d7a');
    const tt=document.createElementNS(NS,'title');
    tt.textContent=nd.type+': '+nd.label; c.appendChild(tt);
    svg.appendChild(c);
    if(byType[nd.type].length<=26){{
      const t=document.createElementNS(NS,'text');
      t.setAttribute('x',p.x+7);t.setAttribute('y',p.y+3);
      t.setAttribute('fill','#8aa');t.setAttribute('font-size','9');
      t.textContent=nd.label.length>26?nd.label.slice(0,26)+'…':nd.label;
      svg.appendChild(t);
    }}
  }});
}})();

// --- client-side exporters ---
function save(name,txt,mime){{
  const b=new Blob([txt],{{type:mime||'text/plain'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}}
function csvRow(a){{return a.map(x=>'"'+String(x==null?'':x).replace(/"/g,'""')+'"').join(',');}}
function dl(kind){{
  const stamp=(DATA.meta.seeds[0]||'osint').replace(/[^a-z0-9.-]/gi,'_');
  if(kind==='json'){{save(stamp+'.json',JSON.stringify(DATA,null,2),'application/json');}}
  else if(kind==='csv'){{
    const rows=[csvRow(['id','type','label','source'])];
    DATA.nodes.forEach(n=>rows.push(csvRow([n.id,n.type,n.label,n.source])));
    save(stamp+'_nodes.csv',rows.join('\n'),'text/csv');
  }}
  else if(kind==='edges'){{
    const rows=[csvRow(['src','dst','relation'])];
    DATA.edges.forEach(e=>rows.push(csvRow([e.src,e.dst,e.rel])));
    save(stamp+'_edges.csv',rows.join('\n'),'text/csv');
  }}
  else if(kind==='txt'){{
    let t='DorkEye OSINT report\nSeeds: '+DATA.meta.seeds.join(', ')
      +'\nChain: '+DATA.meta.chain+'\nNodes: '+DATA.meta.total+'\n\nCounts:\n';
    for(const k in DATA.counts)t+='  '+k+': '+DATA.counts[k]+'\n';
    t+='\nVulnerable IPs:\n';
    DATA.findings.vulnerable_ips.forEach(v=>t+='  '+v.ip+' -> '+v.vulns.join(', ')+'\n');
    t+='\nShared-IP pivots:\n';
    DATA.clusters.shared_ip.forEach(c=>t+='  '+c.ip+' <- '+c.hosts.join(', ')+'\n');
    save(stamp+'.txt',t,'text/plain');
  }}
  else if(kind==='sqlite'){{
    const el=document.getElementById('sqlite'); if(!el){{return;}}
    const bin=atob(el.textContent.trim());
    const arr=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
    const b=new Blob([arr],{{type:'application/x-sqlite3'}});
    const a=document.createElement('a');
    a.href=URL.createObjectURL(b);a.download=stamp+'.sqlite';a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href),2000);
  }}
  else if(kind==='graphml'){{
    const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    let x='<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n';
    x+='<key id="d_type" for="node" attr.name="type" attr.type="string"/>\n';
    x+='<key id="d_label" for="node" attr.name="label" attr.type="string"/>\n';
    x+='<key id="d_rel" for="edge" attr.name="relation" attr.type="string"/>\n<graph edgedefault="directed">\n';
    DATA.nodes.forEach(n=>{{x+='<node id="'+esc(n.id)+'"><data key="d_type">'+esc(n.type)
      +'</data><data key="d_label">'+esc(n.label)+'</data></node>\n';}});
    DATA.edges.forEach((e,i)=>{{x+='<edge id="e'+i+'" source="'+esc(e.src)+'" target="'+esc(e.dst)
      +'"><data key="d_rel">'+esc(e.rel)+'</data></edge>\n';}});
    x+='</graph>\n</graphml>\n';
    save(stamp+'.graphml',x,'application/xml');
  }}
}}
</script>
</body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  [11] Standalone entry point (for quick local testing).
#      In normal use this module is driven by the DorkEye dispatcher.
# ══════════════════════════════════════════════════════════════════════════════


def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser(
        description="DorkEye OSINT Graph — passive, keyless recon (standalone test mode)."
    )
    p.add_argument("--seed", action="append", default=[],
                   help="Seed value (domain/host/ip/url). Repeatable.")
    p.add_argument("--chain", default="recon-basic",
                   help=f"Built-in ({', '.join(BUILTIN_CHAINS)}) or path to a .json chain.")
    p.add_argument("--db", default=None,
                   help="SQLite output path, recreated on every run "
                        "(default: Dump/osint_<seed>_<timestamp>.sqlite).")
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--max-nodes", type=int, default=2000)
    p.add_argument("--html", default=None,
                   help="HTML report path (default: alongside the DB).")
    p.add_argument("--export", default="",
                   help="Extra files to also write: comma list of csv,json,graphml,txt.")
    args = p.parse_args()

    if not args.seed:
        p.error("at least one --seed is required in standalone mode")
    if not args.db:
        args.db = default_db_path(args.seed)

    agent = OsintGraphAgent(
        db_path=args.db, chain=args.chain, threads=args.threads,
        timeout=args.timeout, max_nodes=args.max_nodes,
    )
    try:
        report = agent.run(args.seed)
        report.print_summary()
        graph = agent.build_graph()
        html_path = args.html or (os.path.splitext(args.db)[0] + ".html")
        write_html_report(report, graph, html_path, db_path=args.db)
        _log(f"[osint] report → {html_path}  "
             f"(embedded SQLite + export JSON/CSV/TXT/GraphML from the page)",
             style="green")
        for extra in write_extra_exports(agent, report, graph,
                                         os.path.splitext(args.db)[0], args.export):
            _log(f"[osint] {extra}", style="green")
    finally:
        agent.close()


def export_txt_summary(report: "OsintReport", graph: Dict[str, Any], path: str) -> str:
    """Plain-text run summary — same content as the report's "TXT summary" button."""
    f = graph.get("findings", {}) or {}
    cl = graph.get("clusters", {}) or {}
    lines = [
        "DorkEye OSINT report",
        "Seeds: " + ", ".join(report.seeds),
        "Chain: " + str(report.chain),
        "Nodes: " + str(report.total),
        "Started: " + str(report.started),
        "Finished: " + str(report.finished),
        "",
        "Counts:",
    ]
    lines += [f"  {k}: {v}" for k, v in sorted((graph.get("counts") or {}).items())]
    lines += ["", "Vulnerable IPs:"]
    lines += [f"  {v['ip']} -> {', '.join(v['vulns'])}" for v in f.get("vulnerable_ips", [])] \
        or ["  none"]
    lines += ["", "Interesting hosts:"]
    lines += [f"  {h}" for h in f.get("interesting_hosts", [])] or ["  none"]
    lines += ["", "Shared-IP pivots:"]
    lines += [f"  {c['ip']} <- {', '.join(c['hosts'])}" for c in cl.get("shared_ip", [])] \
        or ["  none"]
    contacts = sorted({n["label"] for n in graph.get("nodes", [])
                       if n.get("type") in ("email", "phone")})
    lines += ["", "Contacts:"]
    lines += [f"  {c}" for c in contacts] or ["  none"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def write_extra_exports(agent: "OsintGraphAgent", report: "OsintReport",
                        graph: Dict[str, Any], base: str, spec: str) -> List[str]:
    """Write optional extra files (csv/json/graphml/txt). Returns log lines."""
    out: List[str] = []
    for fmt in [s.strip().lower() for s in (spec or "").split(",") if s.strip()]:
        try:
            if fmt == "csv":
                out.append("CSV → " + agent.export_csv(base + ".csv"))
            elif fmt == "json":
                with open(base + "_graph.json", "w", encoding="utf-8") as fh:
                    json.dump(graph, fh, indent=2, ensure_ascii=False)
                out.append("JSON → " + base + "_graph.json")
            elif fmt == "graphml":
                out.append("GraphML → " + export_graphml(graph, base + ".graphml"))
            elif fmt == "txt":
                out.append("TXT → " + export_txt_summary(report, graph, base + "_summary.txt"))
            else:
                out.append(f"[skip] unknown export '{fmt}'")
        except Exception as exc:
            out.append(f"[err] export '{fmt}': {exc}")
    return out


if __name__ == "__main__":
    _cli()
