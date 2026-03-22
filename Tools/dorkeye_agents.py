# “””
DorkEye Agents v3.1

Post-search analysis pipeline for DorkEye v4.8+

Agents are invoked AFTER DorkEye has completed the search.
They do not interfere with the search flow — they work on already collected results.

Pipeline (activated with –analyze):

1. TriageAgent             — classifies results by OSINT priority (+ sqli/accessible bonus)
1. PageFetchAgent          — downloads HIGH/CRITICAL pages (retry, UA rotation, saves headers)
1. SecurityAgent [NEW]     — threat detection: phishing, malware, exploits, obfuscation
1. HeaderIntelAgent        — analyses response headers: info leaks, missing security headers
1. TechFingerprintAgent    — detects CMS, frameworks, JS/server versions from content
1. SecretsAgent            — regex scan for secrets/credentials + hash detection + severity
1. PiiDetectorAgent        — detects PII: email, phone, IBAN, CF, CC, SSN, DOB
1. EmailHarvesterAgent     — collects and categorises emails from all results
1. SubdomainHarvesterAgent — extracts subdomains and generates dorks for DorkCrawler
1. ReportAgent             — report HTML/MD/JSON with all new sections (incl. security)
1. DorkCrawlerAgent        — adaptive recursive crawl (fed by TechFP + SubHarvest)

SecurityAgent operates as a middleware — it hooks into BOTH:

- The scanning flow (automatic, via security_scan_hook)
- The –analyze flow (on-demand, as pipeline step 3)

Uso CLI:
python dorkeye.py –dg=all –analyze -o results.json
python dorkeye.py -d dorks.txt –analyze –analyze-fetch –analyze-fmt=html

```
# Security-specific flags:
python dorkeye.py --dg=all --analyze --security-mode=active --security-quarantine
python dorkeye.py --dg=all --analyze --no-security   # disabilita agente
```

Standalone usage (from results file):
python dorkeye_agents.py results.json –analyze-fmt=html –analyze-out=report.html

Autore: DorkEye Project
“””

from **future** import annotations

import hashlib
import json
import math
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from html.parser import HTMLParser as _HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests

# ── Rich console ──────────────────────────────────────────────────────────────

try:
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table
_console = Console()

```
def _log(msg: str, style: str = "cyan") -> None:
    _console.print(f"[{style}]{msg}[/{style}]")

def _panel(body: str, title: str = "", border: str = "cyan") -> None:
    _console.print(Panel(body, title=title, border_style=border))
```

except ImportError:
_console = None  # type: ignore

```
def _log(msg: str, style: str = "") -> None:  # type: ignore
    print(msg)

def _panel(body: str, title: str = "", border: str = "") -> None:  # type: ignore
    print(f"\n[{title}]\n{body}")
```

# ══════════════════════════════════════════════════════════════════════════════

# PATTERN LIBRARY — imported from dorkeye_patterns.py

# ══════════════════════════════════════════════════════════════════════════════

from dorkeye_patterns import (
TRIAGE_RULES       as _TRIAGE_PATTERNS,
SECRET_RULES       as _SECRET_PATTERNS,
SECRET_SEVERITY    as _SECRET_SEVERITY,
PII_RULES          as _PII_PATTERNS,
SCORE_TO_LABEL     as _LABEL_FROM_SCORE,
FETCH_UA           as _FETCH_UA_SHARED,
FETCH_UA_POOL      as _FETCH_UA_POOL,
SKIP_EXTENSIONS    as _SKIP_EXTENSIONS_SHARED,
label_from_score,
censor             as _censor_shared,
luhn_check         as _luhn_check,
)

# ══════════════════════════════════════════════════════════════════════════════

# BASE AGENT

# ══════════════════════════════════════════════════════════════════════════════

def _safe_json_local(raw: str, expected_type: type = dict):
“””
Robust JSON parser — standalone, no external dependencies.
Handles: markdown fences, trailing commas, extra text around JSON.
“””
import re as _re
text = _re.sub(r”`(?:json)?\s*", "", raw).replace("`”, “”).strip()
text = _re.sub(r”,\s*([}]])”, r”\1”, text)

```
open_c  = "{" if expected_type == dict else "["
close_c = "}" if expected_type == dict else "]"
start   = text.find(open_c)
if start == -1:
    return {} if expected_type == dict else []

depth, end = 0, -1
for i, ch in enumerate(text[start:], start):
    if ch == open_c:  depth += 1
    elif ch == close_c:
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end == -1:
    return {} if expected_type == dict else []

try:
    return json.loads(text[start:end])
except json.JSONDecodeError:
    return {} if expected_type == dict else []
```

class BaseAgent(ABC):
“””
Base class for all DorkEye agents.
Works without LLM (plugin=None) — agents use regex by default.
If plugin is provided, LLM steps are activated as enhancements.
“””

```
def __init__(self, plugin=None, name: str = "Agent"):
    self.plugin = plugin   # None = autonomous mode (no LLM)
    self.name   = name

def _call_llm(self, prompt: str, max_tokens: int = 700) -> str:
    """Calls the LLM if available, otherwise raises RuntimeError."""
    if not self.plugin:
        raise RuntimeError(f"[{self.name}] LLM not available — falling back to regex mode")
    return self.plugin._call(
        prompt,
        max_tokens=max_tokens,
        cache=True,
        mem_user=f"[{self.name}] {prompt[:100]}",
    )

@property
def has_llm(self) -> bool:
    """True if the LLM plugin is active and available."""
    return self.plugin is not None

def _safe_json(self, raw: str, expected_type: type = dict):
    """Robust JSON parser — does not depend on dorkeye_llm_plugin."""
    return _safe_json_local(raw, expected_type=expected_type)

@staticmethod
def _label(score: int) -> str:
    """Delegates to dorkeye_patterns.label_from_score() — single source of truth."""
    return label_from_score(score)

@abstractmethod
def run(self, *args, **kwargs):
    pass
```

# ══════════════════════════════════════════════════════════════════════════════

# TRIAGE AGENT

# ══════════════════════════════════════════════════════════════════════════════

class TriageAgent(BaseAgent):
“””
Classifies each result by OSINT priority.

```
Step 1 — Regex pre-scoring (always, without LLM): 0-50 points
Step 2 — LLM scoring (optional, batch_size results at a time): 0-100 points
Final score = max(regex*2, llm_score)

Adds to each result: triage_score (0-100), triage_label, triage_reason.
Sorts by descending score.
"""

def __init__(self, plugin=None, batch_size: int = 15):
    super().__init__(plugin, name="TriageAgent")
    self.batch_size = batch_size

def run(self, results: List[dict], use_llm: bool = True) -> List[dict]:
    if not results:
        return results

    _log(
        f"[{self.name}] Triaging {len(results)} results "
        f"(LLM: {'on' if use_llm and self.plugin else 'off'})...",
        style="bold cyan"
    )

    # Step 1: regex pre-scoring
    for r in results:
        bonus, reasons = self._regex_score(r)
        r["_rx_bonus"]   = bonus
        r["_rx_reasons"] = reasons

    # Step 2: LLM scoring opzionale
    if use_llm and self.plugin:
        batches = [results[i:i+self.batch_size] for i in range(0, len(results), self.batch_size)]
        for b_idx, batch in enumerate(batches, 1):
            _log(f"[{self.name}] LLM scoring batch {b_idx}/{len(batches)}...", style="dim")
            self._llm_score_batch(batch, b_idx)

    # Compute final score and clean up temporary fields
    for r in results:
        if "triage_score" not in r:
            bonus = r.get("_rx_bonus", 0)
            r["triage_score"]  = min(bonus * 2, 100)
            r["triage_label"]  = self._label(r["triage_score"])
            r["triage_reason"] = ", ".join(r.get("_rx_reasons", [])) or "no pattern"
        r.pop("_rx_bonus",   None)
        r.pop("_rx_reasons", None)

    results.sort(key=lambda x: x.get("triage_score", 0), reverse=True)

    # Riepilogo
    counts = {l: 0 for l in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "SKIP")}
    for r in results:
        lbl = r.get("triage_label", "LOW")
        counts[lbl] = counts.get(lbl, 0) + 1

    _log(
        f"[{self.name}] CRITICAL:{counts['CRITICAL']} HIGH:{counts['HIGH']} "
        f"MEDIUM:{counts['MEDIUM']} LOW:{counts['LOW']} SKIP:{counts['SKIP']}",
        style="bold green"
    )
    return results

def _llm_score_batch(self, batch: List[dict], b_idx: int) -> None:
    lines = [
        f"[{i}] {r.get('url','')} | {r.get('title','N/A')[:55]} | {str(r.get('snippet',''))[:75]}"
        for i, r in enumerate(batch)
    ]
    prompt = (
        "You are an OSINT analyst. Assign an OSINT score from 0-100 to each result.\n\n"
        "CRITERIA:\n"
        "  90-100 CRITICAL — credentials, DB admin, shell, exposed config\n"
        "  70-89  HIGH     — admin panels, .env, .git, backups, config files\n"
        "  50-69  MEDIUM   — directory listing, vulnerable CMS, interesting login page\n"
        "  20-49  LOW      — standard login pages, generic pages\n"
        "   0-19  SKIP     — irrelevant\n\n"
        f"RISULTATI:\n" + "\n".join(lines) + "\n\n"
        "Reply ONLY with a JSON array (one element per result, same order):\n"
        '[{"id":0,"score":85,"label":"HIGH","reason":"exposed phpMyAdmin panel"},...]\n###'
    )
    try:
        raw    = self._call_llm(prompt, max_tokens=len(batch) * 60)
        scores = self._safe_json(raw, expected_type=list)
        if not isinstance(scores, list):
            return
        for entry in scores:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("id")
            if not isinstance(idx, int) or idx >= len(batch):
                continue
            r          = batch[idx]
            llm_score  = max(0, min(100, int(entry.get("score", 0))))
            final      = max(llm_score, r.get("_rx_bonus", 0) * 2)
            r["triage_score"]  = final
            r["triage_label"]  = self._label(final)
            r["triage_reason"] = str(entry.get("reason", "LLM scored"))[:120]
    except Exception as e:
        _log(f"[{self.name}] LLM batch {b_idx} failed: {e}", style="yellow")

@staticmethod
def _regex_score(result: dict) -> Tuple[int, List[str]]:
    text = " ".join([
        result.get("url", "") or "",
        result.get("title", "") or "",
        result.get("snippet", "") or "",
    ])
    bonus, reasons = 0, []
    for pattern, pts, hint in _TRIAGE_PATTERNS:
        if pattern.search(text):
            bonus += pts
            reasons.append(hint)

    # ── Runtime bonus from data already present in result (v4.8) ─────────────
    sqli = result.get("sqli_test", {})
    if sqli.get("vulnerable"):
        conf = sqli.get("overall_confidence", "")
        if conf == "critical":
            bonus += 30
            reasons.append("sqli:critical confirmed")
        elif conf == "high":
            bonus += 22
            reasons.append("sqli:high confirmed")
        elif conf in ("medium", "low"):
            bonus += 12
            reasons.append(f"sqli:{conf} confirmed")

    if result.get("accessible") is True and result.get("status_code") == 200:
        bonus += 8
        reasons.append("accessible:200")

    # Number of GET parameters — more parameters = larger attack surface
    url = result.get("url", "")
    if "?" in url:
        try:
            from urllib.parse import parse_qs, urlparse
            n_params = len(parse_qs(urlparse(url).query))
            if n_params >= 5:
                bonus += 10
                reasons.append(f"get_params:{n_params}")
            elif n_params >= 2:
                bonus += 5
                reasons.append(f"get_params:{n_params}")
        except Exception:
            pass

    return min(bonus, 60), reasons  # cap alzato a 60 (era 50)

def get_by_label(self, results: List[dict], *labels: str) -> List[dict]:
    labels_set = {l.upper() for l in labels}
    return [r for r in results if r.get("triage_label", "").upper() in labels_set]
```

# ══════════════════════════════════════════════════════════════════════════════

# PAGE FETCH AGENT

# ══════════════════════════════════════════════════════════════════════════════

class _ScriptStyleStripper(_HTMLParser):
“”“HTMLParser che rimuove blocchi <script> e <style> in modo sicuro.

```
Replaces the bypassable regex (CWE-20/116/185/186) with the parser
built-in that correctly handles all syntactically
valide del tag di chiusura (es. </script  >, </SCRIPT\\n>, ecc.).
"""

def __init__(self):
    super().__init__(convert_charrefs=False)
    self._skip_tags: set = {"script", "style"}
    self._in_skip: int   = 0
    self._parts: list    = []

def handle_starttag(self, tag, attrs):
    if tag.lower() in self._skip_tags:
        self._in_skip += 1

def handle_endtag(self, tag):
    if tag.lower() in self._skip_tags and self._in_skip:
        self._in_skip -= 1

def handle_data(self, data):
    if not self._in_skip:
        self._parts.append(data)

def handle_entityref(self, name):
    if not self._in_skip:
        self._parts.append(f"&{name};")

def handle_charref(self, name):
    if not self._in_skip:
        self._parts.append(f"&#{name};")

def get_result(self) -> str:
    return "".join(self._parts)
```

# Fallback regex — used ONLY if HTMLParser raises an exception on HTML

# that is severely malformed. This is NOT the primary path.

# 

# FIX CWE-20/116/185/186 (“Bad HTML filtering regexp”):

# - Opening : `(?:[^>]*)` unchanged (handles attributes without unquoted `>`)

# - Closing : replaced `s*>` with `[^>]*>` to cover browser-accepted variants

# come `</script anything>` o `</  script  foo>` (spazi dopo `</`

# (spaces after `</` handled by `s*` added before tag name).

# This path is intentionally a last-resort: the primary path uses

# _ScriptStyleStripper (built-in HTMLParser) which is immune to these variants.

_SCRIPT_STYLE_RE_FALLBACK = re.compile(  # noqa: S608
r”<(?:script|style)(?:[^>]*)>[\s\S]*?</\s*(?:script|style)[^>]*>”,
re.IGNORECASE,
)

def _strip_page_content(text: str) -> str:
“”“Rimuove tag script/style con HTMLParser, poi ripulisce i restanti tag HTML.”””
stripper = _ScriptStyleStripper()
try:
stripper.feed(text)
stripper.close()
text = stripper.get_result()
except Exception:
text = _SCRIPT_STYLE_RE_FALLBACK.sub(” “, text)
text = re.sub(r”<[^>]+>”, “ “, text)
text = re.sub(r”\s{3,}”, “\n”, text).strip()
return text

# Local aliases for compatibility with existing references in the code

_FETCH_UA        = _FETCH_UA_SHARED
_SKIP_EXTENSIONS = _SKIP_EXTENSIONS_SHARED

class PageFetchAgent(BaseAgent):
“””
Downloads the real HTML content of HIGH and CRITICAL pages.

```
Instead of analysing DDG snippets (100-200 characters, often useless),
this agent downloads the real HTML/text of the page to give the
SecretsAgent concrete material to work with.

Adds 'page_content' (str) to each processed result.
Respects rate limiting with a small delay between fetches.
"""

def __init__(
    self,
    plugin=None,
    max_pages:    int   = 20,
    timeout:      int   = 10,
    max_chars:    int   = 8000,
    delay_s:      float = 1.0,
    min_label:    str   = "HIGH",
):
    super().__init__(plugin, name="PageFetchAgent")
    self.max_pages  = max_pages
    self.timeout    = timeout
    self.max_chars  = max_chars
    self.delay_s    = delay_s
    self.min_label  = min_label
    self._last_headers: dict = {}
    self._last_status:  int  = 0

def run(self, results: List[dict]) -> List[dict]:
    """
    Downloads the content of priority pages.
    Modifies results in-place by adding 'page_content'.
    Returns the updated list.
    """
    _label_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "SKIP": 0}
    min_rank    = _label_rank.get(self.min_label.upper(), 3)

    targets = [
        r for r in results
        if _label_rank.get(r.get("triage_label", "LOW"), 1) >= min_rank
        and "page_content" not in r
    ][:self.max_pages]

    if not targets:
        _log(f"[{self.name}] No pages to download (min_label={self.min_label}).", style="dim")
        return results

    _log(
        f"[{self.name}] Fetching {len(targets)} pages "
        f"(max={self.max_pages}, timeout={self.timeout}s)...",
        style="bold cyan"
    )

    fetched = 0
    for r in targets:
        url = r.get("url", "")
        if not url:
            continue

        # Salta estensioni binarie / non-testo
        ext = Path(urlparse(url).path).suffix.lower()
        if ext in _SKIP_EXTENSIONS:
            r["page_content"] = ""
            _log(f"[{self.name}] Skip {ext}: {url[:60]}", style="dim")
            continue

        content = self._fetch(url)
        r["page_content"] = content
        # v4.8 — save raw headers for HeaderIntelAgent
        if self._last_headers:
            r["response_headers"] = self._last_headers
            r["fetch_status"]     = self._last_status
            self._last_headers    = {}
            self._last_status     = 0
        status = f"+{len(content)}c" if content else "failed"
        _log(f"[{self.name}] [{r.get('triage_label','?')}] {status} — {url[:70]}", style="dim")
        fetched += 1

        if fetched < len(targets):
            time.sleep(self.delay_s)

    ok_count = sum(1 for r in targets if r.get("page_content"))
    _log(
        f"[{self.name}] Completed: {ok_count}/{len(targets)} pages downloaded.",
        style="green"
    )
    return results

def _fetch(self, url: str) -> str:
    """Downloads and returns the page text (truncated to max_chars).
    v4.8: retry max 2, UA rotation, saves response_headers in result.
    """
    import random as _random
    last_exc = None
    for attempt in range(3):  # 1 tentativo + 2 retry
        ua = _random.choice(_FETCH_UA_POOL)
        try:
            resp = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent":      ua,
                    "Accept":          "text/html,application/xhtml+xml,text/plain",
                    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection":      "keep-alive",
                },
                allow_redirects=True,
                stream=True,
                verify=False,
            )
            if resp.status_code >= 400:
                return ""

            # Leggi al massimo max_chars*3 byte
            raw = b""
            for chunk in resp.iter_content(chunk_size=4096):
                raw += chunk
                if len(raw) > self.max_chars * 3:
                    break

            content_type = resp.headers.get("Content-Type", "")
            if "text" not in content_type and "json" not in content_type:
                return ""

            # Save raw headers in _fetch_meta (will be used by HeaderIntelAgent)
            self._last_headers = dict(resp.headers)
            self._last_status  = resp.status_code

            text = raw.decode("utf-8", errors="replace")
            text = _strip_page_content(text)
            return text[:self.max_chars]

        except Exception as e:
            last_exc = e
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
            continue

    _log(f"[{self.name}] Fetch failed after 3 attempts: {url[:60]} — {last_exc}", style="dim")
    return ""
```

# ══════════════════════════════════════════════════════════════════════════════

# SECURITY AGENT — Threat detection middleware (v3.1)

# ══════════════════════════════════════════════════════════════════════════════

# 

# Operates as a pipeline middleware that hooks into BOTH flows:

# 1. Scanning flow  → security_scan_hook(url, content, headers)

# 2. –analyze flow → SecurityAgent.run(results) as pipeline step 3

# 

# Detection categories:

# - phishing:           brand impersonation, credential harvesting, redirects

# - malware:            JS code execution, obfuscated payloads, droppers

# - exploit:            reverse shells, SQLi, XXE, SSTI, deserialization

# - obfuscation:        hex/unicode escaping, base64 chains, high entropy

# - suspicious_pattern: hidden iframes, missing security headers, executables

# 

# Threat scoring uses a weighted model (not simple sum):

# 50% from worst single indicator

# 30% from average of remaining

# 20% accumulation bonus (capped at +30)

# ══════════════════════════════════════════════════════════════════════════════

_SECURITY_AGENT_VERSION = “1.0.0”

# Soglie di threat score

_THRESHOLD_SAFE       = 15
_THRESHOLD_SUSPICIOUS = 40
_THRESHOLD_DANGEROUS  = 70
_THRESHOLD_CRITICAL   = 90

class ThreatLevel(Enum):
“”“Livello di minaccia assegnato a un risultato.”””
CLEAN      = auto()
LOW        = auto()
SUSPICIOUS = auto()
DANGEROUS  = auto()
CRITICAL   = auto()

```
@classmethod
def from_score(cls, score: int) -> "ThreatLevel":
    if score <= _THRESHOLD_SAFE:
        return cls.CLEAN
    elif score <= _THRESHOLD_SUSPICIOUS:
        return cls.LOW
    elif score <= _THRESHOLD_DANGEROUS:
        return cls.SUSPICIOUS
    elif score <= _THRESHOLD_CRITICAL:
        return cls.DANGEROUS
    return cls.CRITICAL

@property
def badge(self) -> str:
    badges = {
        ThreatLevel.CLEAN:      "🟢 CLEAN",
        ThreatLevel.LOW:        "🟡 LOW",
        ThreatLevel.SUSPICIOUS: "🟠 SUSPICIOUS",
        ThreatLevel.DANGEROUS:  "🔴 DANGEROUS",
        ThreatLevel.CRITICAL:   "💀 CRITICAL",
    }
    return badges.get(self, "⚪ UNKNOWN")

@property
def should_block(self) -> bool:
    return self in (ThreatLevel.DANGEROUS, ThreatLevel.CRITICAL)
```

@dataclass
class ThreatIndicator:
“”“Singolo indicatore di minaccia rilevato.”””
category:    str          # phishing | malware | exploit | obfuscation | suspicious_pattern
description: str          # Descrizione leggibile
severity:    int          # 1-100 contributo al threat score
evidence:    str = “”     # Pattern/snippet che ha triggerato la detection
cwe_id:      str = “”     # CWE reference opzionale (es. CWE-79)
mitre_id:    str = “”     # MITRE ATT&CK opzionale (es. T1566)

@dataclass
class SecurityVerdict:
“”“Verdetto finale di sicurezza per un risultato.”””
url:              str
threat_level:     ThreatLevel
threat_score:     int
indicators:       List[ThreatIndicator] = field(default_factory=list)
timestamp:        str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
scan_duration_ms: float = 0.0
content_hash:     str   = “”
blocked:          bool  = False
summary:          str   = “”

```
def to_dict(self) -> Dict[str, Any]:
    d = asdict(self)
    d["threat_level"] = self.threat_level.name
    d["badge"]        = self.threat_level.badge
    return d

def to_report_line(self) -> str:
    """Linea compatta per report/console."""
    return (
        f"{self.threat_level.badge} │ Score: {self.threat_score:3d}/100 │ "
        f"Indicators: {len(self.indicators)} │ {self.url[:80]}"
    )
```

# ── Security Pattern Database ────────────────────────────────────────────────

class _SecurityPatternDB:
“””
Database centralizzato di pattern malevoli per il SecurityAgent.
Ogni pattern è una tupla: (regex_compilato, categoria, descrizione, severità, cwe)
“””

```
# ── URL / Phishing Patterns ──────────────────────────
PHISHING_URL: List[Tuple[re.Pattern, str, str, int, str]] = [
    (re.compile(r"(?:login|signin|verify|secure|account|update|confirm|auth)"
                 r"[._-]", re.I),
     "phishing", "Keyword di phishing nel dominio/path", 25, "CWE-451"),

    (re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
     "phishing", "URL basato su IP diretto (no DNS)", 30, "CWE-451"),

    (re.compile(r"(?:bit\.ly|tinyurl|t\.co|goo\.gl|is\.gd|rb\.gy|shorturl|"
                 r"cutt\.ly|ow\.ly)", re.I),
     "phishing", "URL shortener (potenziale redirect malevolo)", 15, ""),

    (re.compile(r"@[^/]+/", re.I),
     "phishing", "URL con @ (credential pre-fill / redirect trick)", 35, "CWE-601"),

    (re.compile(r"(?:\.tk|\.ml|\.ga|\.cf|\.gq|\.buzz|\.top|\.xyz|\.pw|"
                 r"\.cc|\.ws)(?:/|$)", re.I),
     "phishing", "TLD ad alto rischio phishing", 20, ""),

    (re.compile(r"(?:data:text/html|javascript:)", re.I),
     "phishing", "Data URI / JavaScript URI scheme", 45, "CWE-79"),

    (re.compile(r"[a-z0-9]{20,}\.(?:com|net|org)", re.I),
     "phishing", "Dominio generato algoritmicamente (DGA suspect)", 25, ""),

    (re.compile(r"(?:paypal|apple|google|microsoft|amazon|facebook|instagram|"
                 r"netflix|banking|wells.?fargo|chase|citibank)"
                 r"[^a-z]", re.I),
     "phishing", "Brand impersonation nel dominio", 35, "CWE-451"),
]

# ── Content / Malware Patterns ───────────────────────
MALWARE_CONTENT: List[Tuple[re.Pattern, str, str, int, str]] = [
    (re.compile(r"eval\s*\(\s*(?:atob|unescape|decodeURI|String\.fromCharCode)",
                 re.I),
     "malware", "eval() con decodifica — esecuzione codice offuscato", 50, "CWE-94"),

    (re.compile(r"document\.write\s*\(\s*(?:unescape|atob|decodeURI)", re.I),
     "malware", "document.write con decodifica — injection DOM", 45, "CWE-79"),

    (re.compile(r"(?:window|document)\s*\[\s*['\"](?:loc|loca|locat)", re.I),
     "malware", "Accesso offuscato a location (redirect malevolo)", 40, "CWE-601"),

    (re.compile(r"new\s+Function\s*\(\s*['\"]", re.I),
     "malware", "Costruttore Function() — code execution dinamica", 45, "CWE-94"),

    (re.compile(r"(?:createElement|appendChild)\s*\(.*?script", re.I | re.S),
     "malware", "Creazione dinamica tag <script>", 35, "CWE-79"),

    (re.compile(r"\.src\s*=\s*['\"](?:https?:)?//[^'\"]*?(?:\.php|\.asp|"
                 r"cmd=|shell|exec)", re.I),
     "malware", "Caricamento script esterno sospetto", 50, "CWE-829"),

    # Obfuscation patterns
    (re.compile(r"\\x[0-9a-f]{2}(?:\\x[0-9a-f]{2}){10,}", re.I),
     "obfuscation", "Stringa hex-escaped lunga (payload offuscato)", 35, "CWE-506"),

    (re.compile(r"\\u[0-9a-f]{4}(?:\\u[0-9a-f]{4}){10,}", re.I),
     "obfuscation", "Stringa unicode-escaped lunga (payload offuscato)", 35, "CWE-506"),

    (re.compile(r"String\.fromCharCode\s*\(\s*(?:\d+\s*,\s*){5,}", re.I),
     "obfuscation", "fromCharCode con molti argomenti (deoffuscamento)", 40, "CWE-506"),

    (re.compile(r"(?:btoa|atob)\s*\(\s*(?:btoa|atob)\s*\(", re.I),
     "obfuscation", "Doppia codifica base64 (evasion layer)", 45, "CWE-506"),

    (re.compile(r"[a-zA-Z_$][a-zA-Z0-9_$]*\s*=\s*[a-zA-Z_$][a-zA-Z0-9_$]*"
                 r"\s*\(\s*['\"][A-Za-z0-9+/=]{50,}['\"]\s*\)", re.I),
     "obfuscation", "Decodifica di blob base64 lungo (probabile payload)", 40, "CWE-506"),

    # Form credential harvesting
    (re.compile(r"<form[^>]*action\s*=\s*['\"]https?://(?!(?:www\.)?google\."
                 r"|(?:www\.)?facebook\.|(?:www\.)?github\.)", re.I),
     "phishing", "Form con action verso dominio esterno sospetto", 30, "CWE-352"),

    (re.compile(r"<input[^>]*type\s*=\s*['\"]password['\"][^>]*>", re.I),
     "phishing", "Campo password in pagina sospetta", 20, "CWE-522"),

    (re.compile(r"(?:password|passwd|creditcard|cc_num|ssn|social.?security)",
                 re.I),
     "phishing", "Riferimento a dati sensibili nel contenuto", 15, "CWE-312"),
]

# ── Backend Exploit Patterns ─────────────────────────
BACKEND_EXPLOIT: List[Tuple[re.Pattern, str, str, int, str]] = [
    # Reverse shells
    (re.compile(r"(?:bash\s+-i|/dev/tcp/|nc\s+-[elp]|ncat\s|"
                 r"mkfifo\s|socat\s.*exec)", re.I),
     "exploit", "Pattern reverse shell rilevato", 70, "CWE-78"),

    (re.compile(r"(?:python|perl|ruby|php)\s+-[ec]\s+['\"].*?(?:socket|"
                 r"connect|exec|system)", re.I | re.S),
     "exploit", "One-liner reverse shell (Python/Perl/Ruby/PHP)", 70, "CWE-78"),

    # Command injection
    (re.compile(r"(?:;|\||&&|\$\(|`)\s*(?:cat|ls|id|whoami|uname|"
                 r"wget|curl|chmod|chown)\s", re.I),
     "exploit", "Potenziale command injection", 55, "CWE-78"),

    # PHP-specific
    (re.compile(r"<\?php\s.*?(?:eval|exec|system|passthru|shell_exec|"
                 r"popen|proc_open)\s*\(", re.I | re.S),
     "exploit", "PHP con funzioni di esecuzione comandi", 60, "CWE-78"),

    (re.compile(r"(?:base64_decode|gzinflate|gzuncompress|str_rot13)\s*\(\s*"
                 r"(?:base64_decode|gzinflate|\$)", re.I),
     "exploit", "PHP multi-layer deoffuscamento (webshell pattern)", 65, "CWE-506"),

    # SQL Injection in content
    (re.compile(r"(?:UNION\s+ALL\s+SELECT|INTO\s+OUTFILE|INTO\s+DUMPFILE|"
                 r"LOAD_FILE\s*\(|benchmark\s*\(|sleep\s*\(\s*\d)", re.I),
     "exploit", "Payload SQLi rilevato nel contenuto", 50, "CWE-89"),

    # XXE
    (re.compile(r"<!ENTITY\s+\S+\s+SYSTEM\s+['\"](?:file://|https?://|"
                 r"php://|expect://)", re.I),
     "exploit", "XXE Entity injection", 60, "CWE-611"),

    # SSTI / Template injection
    (re.compile(r"\{\{\s*(?:config|self\.__class__|request\.application|"
                 r"cycler\.__init__|lipsum\.__globals__)", re.I),
     "exploit", "Server-Side Template Injection (SSTI)", 55, "CWE-1336"),

    # Deserialization
    (re.compile(r"(?:O:\d+:\"[A-Z]|a:\d+:\{|rO0ABX|aced0005)", re.I),
     "exploit", "Serialized object (PHP/Java deserialization attack)", 50, "CWE-502"),
]

# ── File / Document Patterns ─────────────────────────
FILE_PAYLOAD: List[Tuple[re.Pattern, str, str, int, str]] = [
    (re.compile(r"(?:macro|vba|auto_?open|document_?open|workbook_?open)",
                 re.I),
     "malware", "Riferimento a macro VBA (potenziale dropper)", 40, "CWE-506"),

    (re.compile(r"(?:powershell|cmd\.exe|wscript|cscript|mshta|regsvr32|"
                 r"rundll32|certutil)\s", re.I),
     "malware", "Invocazione utility Windows (potenziale dropper)", 50, "CWE-78"),

    (re.compile(r"(?:Invoke-Expression|IEX|Invoke-WebRequest|"
                 r"DownloadString|DownloadFile|Start-Process|"
                 r"New-Object\s+Net\.WebClient)", re.I),
     "malware", "PowerShell download/exec cradle", 60, "CWE-78"),

    (re.compile(r"<script[^>]*>\s*(?:var|let|const|function|\()", re.I),
     "suspicious_pattern", "Tag <script> con codice inline nel documento", 20, "CWE-79"),

    (re.compile(r"(?:\.exe|\.bat|\.cmd|\.ps1|\.vbs|\.scr|\.pif|\.com|"
                 r"\.msi|\.dll)\b", re.I),
     "suspicious_pattern", "Riferimento a eseguibile nel contenuto", 15, ""),

    (re.compile(r"(?:MZ|TVqQ|AAAA)(?:[A-Za-z0-9+/]{20,})", re.I),
     "malware", "Possibile PE/ELF binary encoded in base64", 55, "CWE-506"),
]

# ── Suspicious Header Patterns ───────────────────────
SUSPICIOUS_HEADERS: Dict[str, List[Tuple[re.Pattern, str, int]]] = {
    "content-type": [
        (re.compile(r"application/(?:x-msdownload|x-msdos-program|"
                     r"x-executable|octet-stream)", re.I),
         "Content-Type indica file eseguibile/binario", 25),
    ],
    "content-disposition": [
        (re.compile(r"filename\s*=\s*['\"]?.*?\.(?:exe|bat|cmd|ps1|vbs|"
                     r"scr|msi|dll|hta)", re.I),
         "Download forzato di file eseguibile", 40),
    ],
    "x-powered-by": [
        (re.compile(r"(?:PHP/[45]\.|ASP\.NET)", re.I),
         "Stack server-side obsoleto/vulnerabile", 10),
    ],
}
```

# ── Security Analyzer Modules ────────────────────────────────────────────────

class _URLSecurityAnalyzer:
“”“Analizza URL per indicatori di phishing e redirect malevoli.”””

```
_KNOWN_SAFE_DOMAINS: Set[str] = {
    "google.com", "github.com", "stackoverflow.com",
    "wikipedia.org", "microsoft.com", "apple.com",
    "mozilla.org", "w3.org", "python.org",
}

# Homoglyph / typosquatting confusables
_CONFUSABLES: Dict[str, str] = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',
    'с': 'c', 'х': 'x', 'у': 'y', '0': 'o',
    '1': 'l', 'і': 'i', 'ɡ': 'g',
}

_REDIRECT_PARAMS: Set[str] = {
    "url", "redirect", "next", "return", "goto",
    "redir", "destination", "continue", "target",
}

def analyze(self, url: str) -> List[ThreatIndicator]:
    indicators: List[ThreatIndicator] = []

    try:
        parsed = urlparse(url)
    except Exception:
        indicators.append(ThreatIndicator(
            category="phishing", description="URL malformato — non parseable",
            severity=30, evidence=url[:200],
        ))
        return indicators

    # Scheme check
    if parsed.scheme not in ("http", "https", ""):
        indicators.append(ThreatIndicator(
            category="phishing", description=f"Schema URL insolito: {parsed.scheme}",
            severity=25, evidence=parsed.scheme,
        ))
    if parsed.scheme == "http":
        indicators.append(ThreatIndicator(
            category="suspicious_pattern", description="Connessione HTTP non cifrata",
            severity=10, evidence=url[:100],
        ))

    # Abnormal URL length
    if len(url) > 250:
        indicators.append(ThreatIndicator(
            category="phishing", description=f"URL insolitamente lungo ({len(url)} chars)",
            severity=15, evidence=url[:100] + "...",
        ))

    hostname = parsed.hostname or ""

    # Subdomain stacking
    subdomain_parts = hostname.split(".")
    if len(subdomain_parts) > 4:
        indicators.append(ThreatIndicator(
            category="phishing",
            description=f"Subdomain stacking ({len(subdomain_parts)} livelli)",
            severity=25, evidence=hostname, cwe_id="CWE-451",
        ))

    # Homoglyph / typosquatting
    for char in hostname:
        if char in self._CONFUSABLES:
            indicators.append(ThreatIndicator(
                category="phishing",
                description="Carattere homoglyph nel dominio (typosquatting)",
                severity=45,
                evidence=f"'{char}' → '{self._CONFUSABLES[char]}' in {hostname}",
                cwe_id="CWE-451",
            ))
            break

    # Open redirect params
    params = parse_qs(parsed.query)
    for param_name in params:
        if param_name.lower() in self._REDIRECT_PARAMS:
            val = params[param_name][0]
            if val.startswith(("http://", "https://", "//")):
                indicators.append(ThreatIndicator(
                    category="phishing",
                    description=f"Open redirect via parametro '{param_name}'",
                    severity=30, evidence=f"{param_name}={val[:80]}",
                    cwe_id="CWE-601",
                ))

    # Pattern database (skip brand impersonation on known-safe domains)
    base_domain = ".".join(hostname.rsplit(".", 2)[-2:]) if hostname else ""
    is_safe = base_domain in self._KNOWN_SAFE_DOMAINS

    for pattern, cat, desc, sev, cwe in _SecurityPatternDB.PHISHING_URL:
        if is_safe and "impersonation" in desc.lower():
            continue
        if pattern.search(url):
            indicators.append(ThreatIndicator(
                category=cat, description=desc, severity=sev,
                evidence=pattern.pattern[:80], cwe_id=cwe,
            ))

    return indicators
```

class _ContentSecurityAnalyzer:
“”“Analizza il contenuto HTTP (HTML/JS/testo) per script malevoli.”””

```
def __init__(self, max_content_length: int = 5 * 1024 * 1024):
    self.max_content_length = max_content_length

def analyze(self, content: str, content_type: str = "") -> List[ThreatIndicator]:
    indicators: List[ThreatIndicator] = []
    if not content:
        return indicators

    analysis_content = content[:self.max_content_length]

    # Scan all pattern groups
    for pattern_group in (
        _SecurityPatternDB.MALWARE_CONTENT,
        _SecurityPatternDB.BACKEND_EXPLOIT,
        _SecurityPatternDB.FILE_PAYLOAD,
    ):
        for pattern, cat, desc, sev, cwe in pattern_group:
            matches = pattern.findall(analysis_content)
            if matches:
                adjusted_sev = min(100, sev + (len(matches) - 1) * 5)
                evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])
                indicators.append(ThreatIndicator(
                    category=cat,
                    description=f"{desc} (×{len(matches)})" if len(matches) > 1 else desc,
                    severity=adjusted_sev,
                    evidence=evidence[:120],
                    cwe_id=cwe,
                ))

    # Entropy analysis (detects encoded payloads)
    high_entropy_blocks = self._find_high_entropy_blocks(analysis_content)
    if high_entropy_blocks:
        indicators.append(ThreatIndicator(
            category="obfuscation",
            description=f"Rilevati {len(high_entropy_blocks)} blocchi ad alta "
                        f"entropia (possibile payload codificato)",
            severity=min(30 + len(high_entropy_blocks) * 5, 60),
            evidence=f"Blocchi: {len(high_entropy_blocks)}, "
                     f"max entropy: {max(e for _, e in high_entropy_blocks):.2f}",
        ))

    # Hidden iframe detection
    iframe_re = re.compile(
        r"<iframe[^>]*(?:style\s*=\s*['\"][^'\"]*"
        r"(?:display\s*:\s*none|visibility\s*:\s*hidden|"
        r"width\s*:\s*[01]|height\s*:\s*[01])|"
        r"width\s*=\s*['\"]?[01]['\"]?|height\s*=\s*['\"]?[01]['\"]?)",
        re.I | re.S,
    )
    if iframe_re.search(analysis_content):
        indicators.append(ThreatIndicator(
            category="malware",
            description="Iframe nascosto (hidden/zero-size) — possibile injection",
            severity=45, evidence="Hidden iframe detected", cwe_id="CWE-829",
        ))

    return indicators

@staticmethod
def _find_high_entropy_blocks(
    content: str, block_size: int = 256, threshold: float = 4.5,
) -> List[Tuple[int, float]]:
    """Trova blocchi di testo con entropia di Shannon alta."""
    high_blocks: List[Tuple[int, float]] = []
    for i in range(0, min(len(content), 100_000), block_size):
        block = content[i:i + block_size]
        if len(block) < block_size // 2:
            continue
        freq: Dict[str, int] = {}
        for ch in block:
            freq[ch] = freq.get(ch, 0) + 1
        entropy = 0.0
        for count in freq.values():
            p = count / len(block)
            if p > 0:
                entropy -= p * math.log2(p)
        if entropy > threshold:
            high_blocks.append((i, entropy))
    return high_blocks
```

class _HeaderSecurityAnalyzer:
“”“Analizza HTTP response headers per anomalie di sicurezza.”””

```
def analyze(self, headers: Dict[str, str]) -> List[ThreatIndicator]:
    indicators: List[ThreatIndicator] = []
    if not headers:
        return indicators

    normalized = {k.lower(): v for k, v in headers.items()}

    # Suspicious patterns
    for header_name, patterns in _SecurityPatternDB.SUSPICIOUS_HEADERS.items():
        value = normalized.get(header_name, "")
        if value:
            for pattern, desc, sev in patterns:
                if pattern.search(value):
                    indicators.append(ThreatIndicator(
                        category="suspicious_pattern", description=desc,
                        severity=sev, evidence=f"{header_name}: {value[:100]}",
                    ))

    # Missing security headers (aggregated)
    sec_hdrs = {
        "x-frame-options": 5, "content-security-policy": 5,
        "x-content-type-options": 5, "strict-transport-security": 5,
    }
    missing = [h for h in sec_hdrs if h not in normalized]
    if len(missing) >= 3:
        indicators.append(ThreatIndicator(
            category="suspicious_pattern",
            description=f"Mancano {len(missing)}/4 security headers standard",
            severity=10 + len(missing) * 3,
            evidence="Missing: " + ", ".join(missing),
        ))

    return indicators
```

class SecurityAgent(BaseAgent):
“””
Agente di sicurezza per DorkEye — rileva phishing, malware, exploit
e payload offuscati nei risultati di scansione.

```
Due modalità:
  - active:  analizza, tagga E blocca risultati DANGEROUS/CRITICAL
  - passive: analizza e tagga soltanto (default nel pipeline --analyze)

Integrazione nel pipeline --analyze:
  Aggiunge 'security_verdict' (dict) a ogni risultato processato.

Integrazione nello scanning (standalone hook):
  from dorkeye_agents import security_scan_hook
  verdict = security_scan_hook(url, content, headers)
  if verdict.blocked:
      continue  # skip risultato
"""

def __init__(
    self,
    plugin=None,
    mode:              str  = "passive",
    quarantine_dir:    Optional[str] = None,
    on_threat_callback: Optional[Callable[[SecurityVerdict], None]] = None,
):
    super().__init__(plugin, name="SecurityAgent")
    self.mode               = mode.lower()
    self.quarantine_dir     = quarantine_dir
    self.on_threat_callback = on_threat_callback

    self._url_analyzer     = _URLSecurityAnalyzer()
    self._content_analyzer = _ContentSecurityAnalyzer()
    self._header_analyzer  = _HeaderSecurityAnalyzer()

    # Stats
    self._stats: Dict[str, int] = {
        "total_scanned": 0, "clean": 0, "low": 0,
        "suspicious": 0, "dangerous": 0, "critical": 0, "blocked": 0,
    }
    self._verdicts: List[SecurityVerdict] = []

    if quarantine_dir:
        os.makedirs(quarantine_dir, exist_ok=True)

# ── Pipeline entry point (--analyze flow) ─────────────────────────────────

def run(self, results: List[dict]) -> List[dict]:
    """
    Scansiona tutti i risultati nel pipeline --analyze.
    Aggiunge 'security_verdict' (dict) a ogni risultato.
    In mode='active', imposta result['security_blocked']=True per DANGEROUS/CRITICAL.
    """
    candidates = [
        r for r in results
        if r.get("url") and r.get("triage_label", "SKIP") != "SKIP"
    ]
    if not candidates:
        _log(f"[{self.name}] No results to scan.", style="dim")
        return results

    _log(
        f"[{self.name}] Security scan on {len(candidates)} results "
        f"(mode={'🛡️ ACTIVE' if self.mode == 'active' else '👁️ PASSIVE'})...",
        style="bold cyan"
    )

    threats_found = 0
    blocked_count = 0

    for r in candidates:
        url     = r.get("url", "")
        content = r.get("page_content", "") or r.get("snippet", "") or ""
        headers = r.get("response_headers", {}) or {}

        verdict = self.scan_single(url, content, headers)
        r["security_verdict"] = verdict.to_dict()

        if verdict.blocked:
            r["security_blocked"] = True
            blocked_count += 1

        if verdict.threat_level not in (ThreatLevel.CLEAN, ThreatLevel.LOW):
            threats_found += 1
            _log(
                f"[{self.name}] {verdict.to_report_line()}",
                style="red" if verdict.threat_level.should_block else "yellow"
            )

    _log(
        f"[{self.name}] Completed: {self._stats['total_scanned']} scanned, "
        f"{threats_found} threats, {blocked_count} blocked.",
        style="bold green" if threats_found == 0 else "bold red"
    )
    return results

# ── Single-result scan (usable from both flows) ───────────────────────────

def scan_single(
    self,
    url:          str,
    content:      str = "",
    headers:      Optional[Dict[str, str]] = None,
    content_type: str = "",
) -> SecurityVerdict:
    """
    Analizza un singolo risultato.

    Chiamabile sia dal pipeline --analyze (via self.run)
    che dallo scanning flow (via security_scan_hook).
    """
    start_time = time.monotonic()
    all_indicators: List[ThreatIndicator] = []

    # Phase 1: URL analysis
    all_indicators.extend(self._url_analyzer.analyze(url))

    # Phase 2: Content analysis
    if content:
        all_indicators.extend(
            self._content_analyzer.analyze(content, content_type)
        )

    # Phase 3: Header analysis
    if headers:
        all_indicators.extend(self._header_analyzer.analyze(headers))

    # Phase 4: Threat score
    threat_score = self._calculate_threat_score(all_indicators)
    threat_level = ThreatLevel.from_score(threat_score)

    # Phase 5: Block decision
    blocked = (self.mode == "active" and threat_level.should_block)

    # Phase 6: Content hash
    content_hash = ""
    if content:
        content_hash = hashlib.sha256(
            content.encode("utf-8", errors="replace")
        ).hexdigest()[:16]

    scan_ms = (time.monotonic() - start_time) * 1000
    verdict = SecurityVerdict(
        url=url, threat_level=threat_level, threat_score=threat_score,
        indicators=all_indicators, scan_duration_ms=round(scan_ms, 2),
        content_hash=content_hash, blocked=blocked,
        summary=self._generate_summary(all_indicators, threat_level),
    )

    # Update stats
    self._stats["total_scanned"] += 1
    self._stats[threat_level.name.lower()] = (
        self._stats.get(threat_level.name.lower(), 0) + 1
    )
    if blocked:
        self._stats["blocked"] += 1
    self._verdicts.append(verdict)

    # Callback
    if self.on_threat_callback and threat_score > _THRESHOLD_SAFE:
        self.on_threat_callback(verdict)

    # Quarantine
    if blocked and self.quarantine_dir and content:
        self._quarantine(verdict, content)

    return verdict

# ── Stats and reporting ───────────────────────────────────────────────────

@property
def stats(self) -> Dict[str, int]:
    return dict(self._stats)

@property
def verdicts(self) -> List[SecurityVerdict]:
    return list(self._verdicts)

def get_threats_above(self, level: ThreatLevel) -> List[SecurityVerdict]:
    """Returns all verdicts above a given threat level."""
    order = list(ThreatLevel)
    threshold_idx = order.index(level)
    return [v for v in self._verdicts if order.index(v.threat_level) >= threshold_idx]

def generate_console_report(self) -> str:
    """Text report for Rich console output."""
    lines = [
        f"  Total scanned:  {self._stats['total_scanned']:>6}",
        f"  🟢 Clean:       {self._stats.get('clean', 0):>6}",
        f"  🟡 Low:         {self._stats.get('low', 0):>6}",
        f"  🟠 Suspicious:  {self._stats.get('suspicious', 0):>6}",
        f"  🔴 Dangerous:   {self._stats.get('dangerous', 0):>6}",
        f"  💀 Critical:    {self._stats.get('critical', 0):>6}",
        f"  🚫 Blocked:     {self._stats['blocked']:>6}",
    ]
    threats = [v for v in self._verdicts if v.threat_level != ThreatLevel.CLEAN]
    if threats:
        lines.append("  ─────────────────────────────────────")
        for v in sorted(threats, key=lambda x: -x.threat_score)[:15]:
            lines.append(f"  {v.to_report_line()}")
            for ind in v.indicators[:3]:
                lines.append(f"    ├─ [{ind.category.upper()}] {ind.description}")
                if ind.cwe_id:
                    lines.append(f"    │  └─ {ind.cwe_id}")
    return "\n".join(lines)

def generate_html_section(self) -> str:
    """HTML snippet for integration in ReportAgent's HTML output."""
    threat_colors = {
        "CLEAN": "#00c853", "LOW": "#ffd600", "SUSPICIOUS": "#ff9100",
        "DANGEROUS": "#ff1744", "CRITICAL": "#d50000",
    }
    rows = []
    for v in self._verdicts:
        if v.threat_level == ThreatLevel.CLEAN:
            continue
        color = threat_colors.get(v.threat_level.name, "#9e9e9e")
        pills = " ".join(
            f'<span style="background:{color}20;color:{color};'
            f'border:1px solid {color}40;padding:1px 6px;border-radius:3px;'
            f'font-size:10px;margin-right:3px">{ind.category}</span>'
            for ind in v.indicators[:4]
        )
        rows.append(
            f"<tr style='border-left:3px solid {color}'>"
            f"<td><span style='background:{color};color:#fff;padding:2px 8px;"
            f"border-radius:4px;font-size:10px;font-weight:700'>"
            f"{v.threat_level.name}</span></td>"
            f"<td style='font-weight:700;text-align:center'>{v.threat_score}/100</td>"
            f"<td title='{v.url}'><a href='{v.url}' target='_blank'>"
            f"{v.url[:65]}{'...' if len(v.url) > 65 else ''}</a></td>"
            f"<td>{pills}</td>"
            f"<td>{'🚫' if v.blocked else '✓'}</td></tr>"
        )
    if not rows:
        return ""
    return (
        '<table><tr><th>Level</th><th>Score</th>'
        '<th>URL</th><th>Indicators</th><th>Status</th></tr>'
        + "".join(rows) + '</table>'
    )

def reset(self):
    """Reset stats and verdicts for a new session."""
    self._stats = {k: 0 for k in self._stats}
    self._verdicts.clear()

# ── Private methods ───────────────────────────────────────────────────────

@staticmethod
def _calculate_threat_score(indicators: List[ThreatIndicator]) -> int:
    """
    Weighted threat score:
      50% from worst single indicator
      30% from average of remaining
      20% accumulation bonus (capped at +30)
    """
    if not indicators:
        return 0
    severities = sorted([i.severity for i in indicators], reverse=True)
    max_sev = severities[0]
    avg_rest = (
        sum(severities[1:]) / len(severities[1:])
        if len(severities) > 1 else 0
    )
    accum_bonus = min(len(indicators) * 3, 30)
    score = int(max_sev * 0.50 + avg_rest * 0.30 + accum_bonus * 0.20)
    return min(100, max(0, score))

@staticmethod
def _generate_summary(
    indicators: List[ThreatIndicator], threat_level: ThreatLevel,
) -> str:
    if not indicators:
        return "Nessun indicatore di minaccia rilevato."
    categories: Dict[str, int] = {}
    for ind in indicators:
        categories[ind.category] = categories.get(ind.category, 0) + 1
    parts = [f"{cat}: {n}" for cat, n in sorted(categories.items(), key=lambda x: -x[1])]
    return (
        f"{threat_level.badge} — "
        f"{len(indicators)} indicatori ({', '.join(parts)})"
    )

def _quarantine(self, verdict: SecurityVerdict, content: str) -> None:
    if not self.quarantine_dir:
        return
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", verdict.url)[:80]
    filename  = f"{verdict.content_hash}_{safe_name}.quarantine"
    filepath  = os.path.join(self.quarantine_dir, filename)
    data = {
        "verdict":        verdict.to_dict(),
        "content_preview": content[:2000],
        "content_hash_full": hashlib.sha256(
            content.encode("utf-8", errors="replace")
        ).hexdigest(),
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _log(f"[{self.name}] Quarantinato: {filepath}", style="dim")
    except OSError as e:
        _log(f"[{self.name}] Quarantine failed: {e}", style="yellow")
```

# ── Security Agent integration hooks (scanning flow) ─────────────────────────

_global_security_agent: Optional[SecurityAgent] = None

def get_security_agent(**kwargs) -> SecurityAgent:
“””
Returns the global SecurityAgent singleton.
Callable from any DorkEye module.

```
Usage:
    from dorkeye_agents import get_security_agent
    agent = get_security_agent(mode="active")
    verdict = agent.scan_single(url, content)
"""
global _global_security_agent
if _global_security_agent is None:
    _global_security_agent = SecurityAgent(**kwargs)
return _global_security_agent
```

def reset_security_agent() -> None:
“”“Resets the global singleton (for new scan sessions).”””
global _global_security_agent
if _global_security_agent:
_global_security_agent.reset()

def security_scan_hook(
url: str, content: str = “”, headers: Optional[Dict[str, str]] = None,
) -> SecurityVerdict:
“””
Quick hook for inline integration in the scanning flow.

```
Usage in dorkeye.py (scanning loop):
    from dorkeye_agents import security_scan_hook
    verdict = security_scan_hook(result_url, response_text, resp_headers)
    if verdict.blocked:
        continue  # skip malicious result

Usage in --analyze flow:
    verdict = security_scan_hook(url, fetched_content)
    report_data["security"] = verdict.to_dict()
"""
agent = get_security_agent()
return agent.scan_single(url, content, headers)
```

# ══════════════════════════════════════════════════════════════════════════════

# SECRETS AGENT

# ══════════════════════════════════════════════════════════════════════════════

# _censor imported as _censor_shared from dorkeye_patterns — local alias

def _censor(value: str, visible: int = 4) -> str:
return _censor_shared(value, show=visible)

class SecretsAgent(BaseAgent):
“””
Analyses the real page content (page_content) looking for
credentials, API keys, DB connections, and other sensitive data.

```
Works in two phases:
  1. Regex scan (fast, no LLM) — finds known patterns with high confidence
  2. LLM scan (optional) — contextual analysis for ambiguous or hidden patterns

Content analysis priority:
  page_content (real downloaded content) > snippet (DDG snippet)

Adds 'secrets' (list) to each result with findings.
"""

def __init__(self, plugin=None, use_llm: bool = True, max_content: int = 6000):
    super().__init__(plugin, name="SecretsAgent")
    self.use_llm     = use_llm and plugin is not None
    self.max_content = max_content

def run(self, results: List[dict]) -> List[dict]:
    """
    Scans all results that have available content.
    Returns the list with 'secrets' populated.
    """
    # Work only on results with content (non-empty page_content or snippet)
    candidates = [
        r for r in results
        if (r.get("page_content") or r.get("snippet"))
        and r.get("triage_label", "SKIP") != "SKIP"
    ]

    if not candidates:
        _log(f"[{self.name}] No content available to scan.", style="dim")
        return results

    _log(
        f"[{self.name}] Secrets scan on {len(candidates)} results "
        f"(LLM: {'on' if self.use_llm else 'off'})...",
        style="bold cyan"
    )

    total_found = 0
    for r in candidates:
        # Prefer the real page content
        content = r.get("page_content") or r.get("snippet") or ""
        content = content[:self.max_content]
        url     = r.get("url", "")

        findings: List[dict] = []

        # Phase 1: regex scan
        regex_hits = self._regex_scan(content, url)
        findings.extend(regex_hits)

        # Phase 2: LLM scan (only if LLM active and content rich enough)
        if self.use_llm and len(content) > 100:
            llm_hits = self._llm_scan(content, url)
            # Add only new findings not already found by regex
            existing_values = {f.get("value", "") for f in findings}
            for hit in llm_hits:
                if hit.get("value", "") not in existing_values:
                    findings.append(hit)

        if findings:
            r["secrets"] = findings
            total_found += len(findings)
            _log(
                f"[{self.name}] {len(findings)} secret(s) → [{r.get('triage_label','?')}] {url[:65]}",
                style="bold red"
            )

    _log(
        f"[{self.name}] Scan complete: {total_found} total secrets found.",
        style="bold green" if total_found == 0 else "bold red"
    )
    return results

def _regex_scan(self, content: str, url: str) -> List[dict]:
    findings = []
    # Dedup by normalised value (avoids duplicates for the same repeated key)
    seen_values: set = set()

    for category, pattern, description, has_group in _SECRET_PATTERNS:
        for match in pattern.finditer(content):
            if has_group and match.lastindex:
                raw_value = match.group(1).strip()
            else:
                raw_value = match.group(0).strip()
            if not raw_value or len(raw_value) < 4:
                continue

            # Dedup normalizzato: lowercase + strip whitespace
            norm = raw_value.lower().replace(" ", "").replace("-", "")
            if norm in seen_values:
                continue
            seen_values.add(norm)

            # Context: 70 characters before and after the match
            start   = max(0, match.start() - 70)
            end     = min(len(content), match.end() + 70)
            context = content[start:end].replace("\n", " ").strip()

            # Severity dal mapping centralizzato
            severity = _SECRET_SEVERITY.get(category, "MEDIUM")

            findings.append({
                "type":       category,
                "detection":  "REGEX",
                "value":      _censor(raw_value),
                "confidence": "HIGH",
                "severity":   severity,
                "context":    context[:160],
                "source":     url,
                "desc":       description,
            })
    return findings

def _llm_scan(self, content: str, url: str) -> List[dict]:
    prompt = (
        "You are a security expert. Analyse this text and find ALL secrets or sensitive data.\n\n"
        f"SORGENTE: {url}\n"
        f"CONTENUTO:\n{content[:3000]}\n\n"
        "Look for: API keys, tokens, passwords, hashes, JWT, DB connections, cloud credentials, SSH keys.\n"
        "Reply ONLY with a JSON array (empty [] if nothing found):\n"
        '[{"type":"API_KEY","value":"sk-abc...xyz0","confidence":"HIGH","context":"riga di contesto"}]\n###'
    )
    try:
        raw  = self._call_llm(prompt, max_tokens=500)
        data = self._safe_json(raw, expected_type=list)
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            if isinstance(item, dict) and item.get("value"):
                item["detection"] = "LLM"
                item["source"]    = url
                # Add severity if not present
                if "severity" not in item:
                    item["severity"] = _SECRET_SEVERITY.get(
                        item.get("type", ""), "MEDIUM"
                    )
                results.append(item)
        return results
    except Exception as e:
        _log(f"[{self.name}] LLM scan error ({url[:50]}): {e}", style="yellow")
        return []
```

# ══════════════════════════════════════════════════════════════════════════════

# REPORT AGENT

# ══════════════════════════════════════════════════════════════════════════════

class ReportAgent(BaseAgent):
“””
Generates the final report for the analysis session.

```
Input: triaged results with secrets, optional LLM analysis
Output: HTML file (dark theme), Markdown, or JSON
"""

def __init__(self, plugin=None):
    super().__init__(plugin, name="ReportAgent")

def run(
    self,
    results:     List[dict],
    analysis:    Optional[dict]  = None,
    target:      str             = "",
    output_path: Optional[str]   = None,
    fmt:         str             = "html",
    extra:       Optional[dict]  = None,
) -> str:
    """
    Generates the report in the requested format.

    Args:
        results:     triaged results (with secrets, pii, email, security, etc.)
        analysis:    dict da llm_plugin.analyze_results() (opzionale)
        target:      descrizione del target originale
        output_path: save path (None = do not save)
        fmt:         "html" | "md" | "json"
        extra:       dict with emails, pii, subdomains, cve_dorks, security (v3.1)

    Returns:
        Report string in the requested format.
    """
    _log(f"[{self.name}] Generating report (fmt={fmt})...", style="bold cyan")

    analysis  = analysis or {}
    extra     = extra    or {}
    all_secrets = [s for r in results for s in r.get("secrets", [])]

    counts = {l: 0 for l in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "SKIP")}
    for r in results:
        lbl = r.get("triage_label", "LOW")
        counts[lbl] = counts.get(lbl, 0) + 1

    if   fmt == "json": content = self._json(results, analysis, all_secrets, counts, target, extra)
    elif fmt == "md":   content = self._markdown(results, analysis, all_secrets, counts, target, extra)
    else:               content = self._html(results, analysis, all_secrets, counts, target, extra)

    if output_path:
        output_path = self._fix_ext(output_path, fmt)
        try:
            Path(output_path).write_text(content, encoding="utf-8")
            _log(f"[{self.name}] Report saved: {output_path}", style="bold green")
        except IOError as e:
            _log(f"[{self.name}] Save error: {e}", style="red")

    return content

# ── Build helpers ─────────────────────────────────────────────────────────

def _markdown(self, results, analysis, secrets, counts, target, extra=None) -> str:
    extra   = extra or {}
    now     = datetime.now().strftime("%Y-%m-%d %H:%M")
    top     = [r for r in results if r.get("triage_label") in ("CRITICAL","HIGH")]
    recs    = analysis.get("recommendations", [])
    pats    = analysis.get("patterns", [])
    emails  = extra.get("emails", [])
    pii     = extra.get("pii", [])
    subs    = extra.get("subdomains", {})
    sec_stats = extra.get("security_stats", {})
    sec_threats = extra.get("security_threats", [])

    lines = [
        "# DorkEye Analysis Report",
        f"\n> {now}  |  Target: `{target or 'N/A'}`  |  DorkEye v4.8 + Agents v3.1\n",
        "---\n",
        "## Summary\n",
        analysis.get("summary", "_No LLM analysis available._"),
        "\n---\n",
        "## Metrics\n",
        "| Label | Count |",
        "|-------|-------|",
        f"| 🔴 CRITICAL | {counts['CRITICAL']} |",
        f"| 🟠 HIGH     | {counts['HIGH']} |",
        f"| 🟡 MEDIUM   | {counts['MEDIUM']} |",
        f"| 🟢 LOW      | {counts['LOW']} |",
        f"| **TOTAL**   | **{len(results)}** |",
        f"| **SECRETS** | **{len(secrets)}** |",
        f"| **PII**     | **{len(pii)}** |",
        f"| **EMAILS**  | **{len(emails)}** |",
        "",
    ]

    # ── Security Agent section ────────────────────────────────────────────
    if sec_stats:
        lines += [
            "\n---\n",
            "## 🛡️ Security Agent Report\n",
            f"Scanned: {sec_stats.get('total_scanned', 0)} | "
            f"Blocked: {sec_stats.get('blocked', 0)} | "
            f"Mode: {sec_stats.get('mode', 'passive').upper()}\n",
            "| Level | Count |",
            "|-------|-------|",
            f"| 🟢 Clean      | {sec_stats.get('clean', 0)} |",
            f"| 🟡 Low        | {sec_stats.get('low', 0)} |",
            f"| 🟠 Suspicious | {sec_stats.get('suspicious', 0)} |",
            f"| 🔴 Dangerous  | {sec_stats.get('dangerous', 0)} |",
            f"| 💀 Critical   | {sec_stats.get('critical', 0)} |",
            "",
        ]
    if sec_threats:
        lines += [
            "\n### Threats Detected\n",
            "| Score | Level | URL | Categories |",
            "|-------|-------|-----|------------|",
        ]
        for t in sec_threats[:30]:
            cats = ", ".join(
                i.get("category", "?") for i in t.get("indicators", [])[:3]
            )
            lines.append(
                f"| {t.get('threat_score', 0)} | **{t.get('threat_level', '?')}** "
                f"| `{t.get('url', '')[:65]}` | {cats} |"
            )

    if top:
        lines += ["\n---\n", "## Top Findings — CRITICAL & HIGH\n",
                  "| Score | Label | URL | Reason |", "|-------|-------|-----|--------|"]
        for r in top[:25]:
            lines.append(
                f"| {r.get('triage_score',0)} | **{r.get('triage_label','')}** "
                f"| `{r.get('url','')[:75]}` | {r.get('triage_reason','')[:60]} |"
            )
    if secrets:
        lines += ["\n---\n", f"## Secrets Found ({len(secrets)})\n",
                  "| Type | Severity | Detection | Value | Source |",
                  "|------|----------|-----------|-------|--------|"]
        for s in secrets:
            lines.append(
                f"| {s.get('type','?')} | {s.get('severity','?')} | {s.get('detection','?')} "
                f"| `{s.get('value','?')}` | {s.get('source','?')[:60]} |"
            )
    if pii:
        lines += ["\n---\n", f"## PII Detected ({len(pii)})\n",
                  "| Type | Value | Source |", "|------|-------|--------|"]
        for p in pii[:50]:
            lines.append(f"| {p.get('type','?')} | `{p.get('value','?')}` | {p.get('source','?')[:60]} |")
    if emails:
        lines += ["\n---\n", f"## Emails Harvested ({len(emails)})\n",
                  "| Category | Email | Source |", "|----------|-------|--------|"]
        for e in emails[:50]:
            lines.append(f"| {e.get('category','?')} | `{e.get('email','?')}` | {e.get('source','?')[:60]} |")
    if subs:
        lines += ["\n---\n", "## Subdomains Found\n"]
        for bd, sub_list in subs.items():
            lines.append(f"**{bd}**: {', '.join(sub_list[:20])}")
    if pats:
        lines += ["\n---\n", "## Detected Patterns\n"] + [f"- {p}" for p in pats]
    if recs:
        lines += ["\n---\n", "## Recommendations\n"] + [f"- {r}" for r in recs]

    lines += [
        "\n---\n",
        f"## All Results ({len(results)})\n",
        "| Score | Label | URL | Title |",
        "|-------|-------|-----|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r.get('triage_score',0)} | {r.get('triage_label','?')} "
            f"| `{r.get('url','')[:70]}` | {r.get('title','N/A')[:50]} |"
        )
    lines.append(f"\n\n---\n*DorkEye v4.8 + Agents v3.1 — {now}*")
    return "\n".join(lines)

def _html(self, results, analysis, secrets, counts, target, extra=None) -> str:
    extra   = extra or {}
    now     = datetime.now().strftime("%Y-%m-%d %H:%M")
    top     = [r for r in results if r.get("triage_label") in ("CRITICAL","HIGH")]
    recs    = analysis.get("recommendations", [])
    pats    = analysis.get("patterns", [])
    summary = analysis.get("summary", "")
    emails  = extra.get("emails", [])
    pii     = extra.get("pii", [])
    subs    = extra.get("subdomains", {})
    cve_d   = extra.get("cve_dorks", [])
    sec_html = extra.get("security_html", "")
    sec_stats = extra.get("security_stats", {})

    _sc = {"CRITICAL":"#ff4444","HIGH":"#ff8800","MEDIUM":"#ffcc00","LOW":"#44cc44","SKIP":"#888"}
    _sv = {"CRITICAL":"#ff4444","HIGH":"#ff8800","MEDIUM":"#ffcc00","LOW":"#44cc44"}

    def badge(lbl, colors=_sc):
        c = colors.get(lbl,"#888")
        return f'<span style="background:{c};color:#000;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:bold">{lbl}</span>'

    rows_top = "".join(
        f"<tr><td>{r.get('triage_score',0)}</td><td>{badge(r.get('triage_label','?'))}</td>"
        f"<td><a href='{r.get('url','')}' target='_blank'>{r.get('url','')[:80]}</a></td>"
        f"<td>{r.get('triage_reason','')[:70]}</td></tr>"
        for r in top[:25]
    )
    rows_all = "".join(
        f"<tr><td>{r.get('triage_score',0)}</td><td>{badge(r.get('triage_label','?'))}</td>"
        f"<td><a href='{r.get('url','')}' target='_blank'>{r.get('url','')[:80]}</a></td>"
        f"<td>{r.get('title','N/A')[:55]}</td></tr>"
        for r in results
    )
    rows_sec = "".join(
        f"<tr><td><code>{s.get('type','?')}</code></td>"
        f"<td>{badge(s.get('severity','?'), _sv)}</td>"
        f"<td><span style='color:{'#4af' if s.get('detection')=='LLM' else '#fa4'}'>"
        f"{s.get('detection','?')}</span></td>"
        f"<td><code>{s.get('value','?')}</code></td>"
        f"<td>{s.get('source','?')[:60]}</td></tr>"
        for s in secrets
    )
    rows_pii = "".join(
        f"<tr><td><code>{p.get('type','?')}</code></td>"
        f"<td><code>{p.get('value','?')}</code></td>"
        f"<td>{p.get('desc','')[:50]}</td>"
        f"<td>{p.get('source','?')[:60]}</td></tr>"
        for p in pii[:100]
    )
    rows_email = "".join(
        f"<tr><td>{e.get('category','?')}</td>"
        f"<td><code>{e.get('email','?')}</code></td>"
        f"<td>{e.get('source','?')[:60]}</td></tr>"
        for e in emails[:100]
    )
    rows_subs = "".join(
        f"<tr><td><b>{bd}</b></td><td>{', '.join(sl[:15])}</td></tr>"
        for bd, sl in subs.items()
    )
    rows_cve = "".join(
        f"<tr><td><code>{d}</code></td></tr>"
        for d in cve_d[:30]
    )
    pats_html = "".join(f"<li>{p}</li>" for p in pats)
    recs_html = "".join(f"<li>{r}</li>" for r in recs)

    # ── Security Agent metrics for HTML ───────────────────────────────────
    sec_metrics_html = ""
    if sec_stats:
        sec_metrics_html = (
            '<div class="metrics" style="margin-bottom:10px">'
            f'<div class="metric"><div class="num" style="color:#00c853">{sec_stats.get("clean",0)}</div><div class="lbl">CLEAN</div></div>'
            f'<div class="metric"><div class="num" style="color:#ffd600">{sec_stats.get("low",0)}</div><div class="lbl">LOW</div></div>'
            f'<div class="metric"><div class="num" style="color:#ff9100">{sec_stats.get("suspicious",0)}</div><div class="lbl">SUSPICIOUS</div></div>'
            f'<div class="metric"><div class="num" style="color:#ff1744">{sec_stats.get("dangerous",0)}</div><div class="lbl">DANGEROUS</div></div>'
            f'<div class="metric"><div class="num" style="color:#d50000">{sec_stats.get("critical",0)}</div><div class="lbl">CRITICAL</div></div>'
            f'<div class="metric"><div class="num" style="color:#ff4444">{sec_stats.get("blocked",0)}</div><div class="lbl">BLOCKED</div></div>'
            '</div>'
        )

    def section(title, content, show=True):
        if not show:
            return ""
        return f"<h2>{title}</h2><div class='card'>{content}</div>"

    return f"""<!DOCTYPE html>
```

<html lang="it"><head><meta charset="UTF-8">
<title>DorkEye Report — {target or 'Session'}</title>
<style>
:root{{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--text:#c9d1d9;--acc:#58a6ff;--brd:#30363d}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;font-size:14px;line-height:1.6;padding:28px}}
h1{{color:var(--acc);font-size:26px;margin-bottom:4px}}
h2{{color:var(--acc);font-size:17px;margin:28px 0 10px;border-bottom:1px solid var(--brd);padding-bottom:5px}}
.meta{{color:#8b949e;font-size:12px;margin-bottom:20px}}
.card{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:16px;margin-bottom:12px}}
.metrics{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}}
.metric{{background:var(--bg3);border-radius:6px;padding:10px 18px;text-align:center;min-width:85px}}
.metric .num{{font-size:26px;font-weight:bold}}
.metric .lbl{{font-size:11px;color:#8b949e}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--bg3);padding:8px 10px;text-align:left;border-bottom:2px solid var(--brd);color:var(--acc)}}
td{{padding:6px 10px;border-bottom:1px solid var(--brd);vertical-align:top;word-break:break-word}}
tr:hover{{background:var(--bg3)}}
a{{color:var(--acc);text-decoration:none;word-break:break-all}}
a:hover{{text-decoration:underline}}
code{{background:var(--bg3);padding:1px 5px;border-radius:3px;font-size:12px}}
ul{{padding-left:18px}}li{{margin:3px 0}}
footer{{margin-top:36px;font-size:11px;color:#8b949e;text-align:center}}
</style></head><body>
<h1>&#128065; DorkEye Report</h1>
<div class="meta">Generated: {now} &nbsp;|&nbsp; Target: <code>{target or 'N/A'}</code> &nbsp;|&nbsp; DorkEye v4.8 + Agents v3.1</div>
{'<h2>Summary</h2><div class="card">'+summary+'</div>' if summary else ''}
<h2>Metrics</h2>
<div class="metrics">
  <div class="metric"><div class="num" style="color:#ff4444">{counts['CRITICAL']}</div><div class="lbl">CRITICAL</div></div>
  <div class="metric"><div class="num" style="color:#ff8800">{counts['HIGH']}</div><div class="lbl">HIGH</div></div>
  <div class="metric"><div class="num" style="color:#ffcc00">{counts['MEDIUM']}</div><div class="lbl">MEDIUM</div></div>
  <div class="metric"><div class="num" style="color:#44cc44">{counts['LOW']}</div><div class="lbl">LOW</div></div>
  <div class="metric"><div class="num">{len(results)}</div><div class="lbl">TOTAL</div></div>
  <div class="metric"><div class="num" style="color:#ff4444">{len(secrets)}</div><div class="lbl">SECRETS</div></div>
  <div class="metric"><div class="num" style="color:#ff8800">{len(pii)}</div><div class="lbl">PII</div></div>
  <div class="metric"><div class="num" style="color:#58a6ff">{len(emails)}</div><div class="lbl">EMAILS</div></div>
</div>
{section('🛡️ Security Agent', sec_metrics_html + sec_html, bool(sec_html or sec_stats))}
{section('Top Findings — CRITICAL &amp; HIGH', '<table><tr><th>Score</th><th>Label</th><th>URL</th><th>Reason</th></tr>'+rows_top+'</table>', bool(top))}
{section(f'Secrets Found ({len(secrets)})', '<table><tr><th>Type</th><th>Severity</th><th>Detection</th><th>Value</th><th>Source</th></tr>'+rows_sec+'</table>', bool(secrets))}
{section(f'PII Detected ({len(pii)})', '<table><tr><th>Type</th><th>Value</th><th>Description</th><th>Source</th></tr>'+rows_pii+'</table>', bool(pii))}
{section(f'Emails Harvested ({len(emails)})', '<table><tr><th>Category</th><th>Email</th><th>Source</th></tr>'+rows_email+'</table>', bool(emails))}
{section('Subdomains Found', '<table><tr><th>Base Domain</th><th>Subdomains</th></tr>'+rows_subs+'</table>', bool(subs))}
{section(f'CVE / Follow-up Dorks ({len(cve_d)})', '<table><tr><th>Dork</th></tr>'+rows_cve+'</table>', bool(cve_d))}
{'<h2>Patterns</h2><div class="card"><ul>'+pats_html+'</ul></div>' if pats else ''}
{'<h2>Recommendations</h2><div class="card"><ul>'+recs_html+'</ul></div>' if recs else ''}
<h2>All Results ({len(results)})</h2>
<div class="card"><table><tr><th>Score</th><th>Label</th><th>URL</th><th>Title</th></tr>{rows_all}</table></div>
<footer>DorkEye v4.8 + Agents v3.1 &mdash; {now}</footer>
</body></html>"""

```
def _json(self, results, analysis, secrets, counts, target, extra=None) -> str:
    extra = extra or {}
    return json.dumps({
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "target":       target or "",
            "engine":       "DorkEye v4.8 + Agents v3.1",
        },
        "metrics": {
            "total":     len(results),
            "by_label":  counts,
            "secrets":   len(secrets),
            "pii":       len(extra.get("pii", [])),
            "emails":    len(extra.get("emails", [])),
            "subdomains": sum(len(v) for v in extra.get("subdomains", {}).values()),
        },
        "security": {
            "stats":   extra.get("security_stats", {}),
            "threats": extra.get("security_threats", []),
        },
        "analysis":   analysis,
        "secrets":    secrets,
        "pii":        extra.get("pii", []),
        "emails":     extra.get("emails", []),
        "subdomains": extra.get("subdomains", {}),
        "cve_dorks":  extra.get("cve_dorks", []),
        "results":    results,
    }, indent=2, ensure_ascii=False)

@staticmethod
def _fix_ext(path: str, fmt: str) -> str:
    ext_map = {"md": ".md", "html": ".html", "json": ".json"}
    p, wanted = Path(path), ext_map.get(fmt, ".html")
    return str(p) if p.suffix.lower() == wanted else str(p.with_suffix(wanted))
```

# ══════════════════════════════════════════════════════════════════════════════

# HEADER INTEL AGENT (v4.8)

# ══════════════════════════════════════════════════════════════════════════════

# Security headers che dovrebbero essere presenti

_SECURITY_HEADERS_REQUIRED = {
“strict-transport-security”: “HSTS absent — MITM risk”,
“content-security-policy”:   “CSP absent — XSS risk”,
“x-frame-options”:           “Clickjacking protection absent”,
“x-content-type-options”:    “MIME sniffing protection absent”,
“referrer-policy”:           “Referrer-Policy absent”,
“permissions-policy”:        “Permissions-Policy absent”,
}

# Header che rivelano informazioni sul server/tecnologia

_INFO_LEAK_HEADERS = [
“server”, “x-powered-by”, “x-aspnet-version”, “x-aspnetmvc-version”,
“x-generator”, “x-drupal-cache”, “x-wordpress-cache”,
“x-runtime”, “x-rack-cache”, “via”,
]

# Pattern per versioni obsolete nei header

_OUTDATED_VERSION_RE = re.compile(
r”(?:apache|nginx|php|openssl|iis|tomcat|jetty|lighttpd)[/\s]”
r”(\d+.\d+(?:.\d+)?)”,
re.I,
)

class HeaderIntelAgent(BaseAgent):
“””
Analyses HTTP response headers saved by PageFetchAgent.

```
For each result with 'response_headers' detects:
  - Info leaks: Server, X-Powered-By, software versions
  - Missing security headers: HSTS, CSP, X-Frame-Options, etc.
  - Outdated versions in header values

Adds 'header_intel' (dict) to each processed result.
Does not perform HTTP requests — works on already present data.
"""

def __init__(self, plugin=None):
    super().__init__(plugin, name="HeaderIntelAgent")

def run(self, results: List[dict]) -> List[dict]:
    candidates = [r for r in results if r.get("response_headers")]
    if not candidates:
        _log(f"[{self.name}] No headers available — run with --analyze-fetch.", style="dim")
        return results

    _log(f"[{self.name}] Analysing headers for {len(candidates)} results...", style="bold cyan")

    total_findings = 0
    for r in candidates:
        intel = self._analyze(r["response_headers"], r.get("url", ""))
        r["header_intel"] = intel
        n = len(intel.get("info_leaks", [])) + len(intel.get("missing_security", []))
        if n:
            total_findings += n
            _log(
                f"[{self.name}] [{r.get('triage_label','?')}] "
                f"{n} finding(s) → {r.get('url','')[:65]}",
                style="yellow"
            )

    _log(f"[{self.name}] Completed: {total_findings} total header finding(s).", style="bold green")
    return results

def _analyze(self, headers: dict, url: str) -> dict:
    intel = {
        "url":              url,
        "info_leaks":       [],
        "missing_security": [],
        "outdated":         [],
    }
    headers_lc = {k.lower(): v for k, v in headers.items()}

    # Info leak
    for h in _INFO_LEAK_HEADERS:
        val = headers_lc.get(h, "")
        if val:
            entry = {"header": h, "value": val[:120]}
            # Controlla versioni obsolete
            m = _OUTDATED_VERSION_RE.search(val)
            if m:
                entry["version"] = m.group(0)
                intel["outdated"].append(entry)
            intel["info_leaks"].append(entry)

    # Security headers mancanti
    for h, reason in _SECURITY_HEADERS_REQUIRED.items():
        if h not in headers_lc:
            intel["missing_security"].append({"header": h, "reason": reason})

    # Cache / debug header sospetti
    if headers_lc.get("x-debug") or headers_lc.get("x-debug-token"):
        intel["info_leaks"].append({"header": "x-debug", "value": "debug headers exposed"})
    if headers_lc.get("x-cache-debug"):
        intel["info_leaks"].append({"header": "x-cache-debug", "value": headers_lc["x-cache-debug"][:80]})

    return intel
```

# ══════════════════════════════════════════════════════════════════════════════

# TECH FINGERPRINT AGENT (v4.8)

# ══════════════════════════════════════════════════════════════════════════════

# Signatures tecnologie: (pattern, tech_name, category)

*TECH_SIGNATURES: List[Tuple[re.Pattern, str, str]] = [
# CMS
(re.compile(r”wp-content|wp-json|wordpress”,               re.I), “WordPress”,    “cms”),
(re.compile(r”joomla|option=com*”,                         re.I), “Joomla”,       “cms”),
(re.compile(r”drupal|sites/default”,                       re.I), “Drupal”,       “cms”),
(re.compile(r”magento|mage/|varien/”,                      re.I), “Magento”,      “cms”),
(re.compile(r”prestashop|modules/paypal”,                  re.I), “PrestaShop”,   “cms”),
(re.compile(r”typo3|fileadmin/”,                           re.I), “TYPO3”,        “cms”),
(re.compile(r”shopify”,                                    re.I), “Shopify”,      “cms”),
(re.compile(r”wix.com|wixstatic”,                         re.I), “Wix”,          “cms”),
# Framework
(re.compile(r”laravel|artisan|eloquent”,                   re.I), “Laravel”,      “framework”),
(re.compile(r”django|wsgi.py|manage.py”,                 re.I), “Django”,       “framework”),
(re.compile(r”rails|ruby on rails|action_controller”,      re.I), “Rails”,        “framework”),
(re.compile(r”flask|werkzeug”,                             re.I), “Flask”,        “framework”),
(re.compile(r”express.js|expressjs”,                      re.I), “Express.js”,   “framework”),
(re.compile(r”next.js|*next/static”,                      re.I), “Next.js”,      “framework”),
(re.compile(r”nuxt|nuxtjs”,                                re.I), “Nuxt.js”,      “framework”),
# JS Libraries (con versione)
(re.compile(r”jquery[/-](\d+.\d+.\d+)”,                  re.I), “jQuery”,       “js_lib”),
(re.compile(r”react(?:.min)?.js|react-dom”,              re.I), “React”,        “js_lib”),
(re.compile(r”vue(?:.min)?.js|vue@\d”,                   re.I), “Vue.js”,       “js_lib”),
(re.compile(r”angular(?:.min)?.js|angular/core”,         re.I), “Angular”,      “js_lib”),
(re.compile(r”bootstrap[/-](\d+.\d+.\d+)”,               re.I), “Bootstrap”,    “js_lib”),
# Server / infra
(re.compile(r”apache[/ ](\d+.\d+)”,                       re.I), “Apache”,       “server”),
(re.compile(r”nginx[/ ](\d+.\d+)”,                        re.I), “Nginx”,        “server”),
(re.compile(r”microsoft-iis[/ ](\d+.\d+)”,                re.I), “IIS”,          “server”),
(re.compile(r”openssl[/ ](\d+.\d+)”,                      re.I), “OpenSSL”,      “server”),
(re.compile(r”php[/ ](\d+.\d+)”,                          re.I), “PHP”,          “lang”),
(re.compile(r”python[/ ](\d+.\d+)”,                       re.I), “Python”,       “lang”),
(re.compile(r”node.js[/ ](\d+.\d+)”,                     re.I), “Node.js”,      “lang”),
# DevOps / infra
(re.compile(r”jenkins|hudson”,                             re.I), “Jenkins”,      “devops”),
(re.compile(r”gitlab”,                                     re.I), “GitLab”,       “devops”),
(re.compile(r”kibana”,                                     re.I), “Kibana”,       “devops”),
(re.compile(r”grafana”,                                    re.I), “Grafana”,      “devops”),
(re.compile(r”docker|dockerfile”,                          re.I), “Docker”,       “devops”),
(re.compile(r”kubernetes|k8s”,                             re.I), “Kubernetes”,   “devops”),
(re.compile(r”elasticsearch”,                              re.I), “Elasticsearch”,“devops”),
# DB panels
(re.compile(r”phpmyadmin|pma*”,                            re.I), “phpMyAdmin”,   “db_panel”),
(re.compile(r”adminer.php|adminer/”,                      re.I), “Adminer”,      “db_panel”),
(re.compile(r”pgadmin”,                                    re.I), “pgAdmin”,      “db_panel”),
]

# Dork CVE mirati per tecnologia (alimenta DorkCrawlerAgent)

_TECH_CVE_DORK_TEMPLATES: Dict[str, List[str]] = {
“WordPress”:  [
‘site:{domain} inurl:wp-login.php’,
‘site:{domain} inurl:xmlrpc.php’,
‘site:{domain} inurl:wp-config.php.bak’,
],
“Joomla”:     [‘site:{domain} inurl:configuration.php’, ‘site:{domain} inurl:/administrator/’],
“Drupal”:     [‘site:{domain} inurl:CHANGELOG.txt’, ‘site:{domain} inurl:sites/default/files’],
“Laravel”:    [‘site:{domain} inurl:.env’, ‘site:{domain} filetype:log storage/logs’],
“Django”:     [‘site:{domain} “DisallowedHost”’, ‘site:{domain} “DEBUG = True”’],
“phpMyAdmin”: [‘site:{domain} intitle:“phpMyAdmin” inurl:index.php’],
“Jenkins”:    [‘site:{domain} intitle:“Dashboard [Jenkins]”’, ‘site:{domain} inurl:/jenkins/api/’],
“Kibana”:     [‘site:{domain} inurl:app/kibana’, ‘site:{domain} intitle:“Kibana”’],
“Grafana”:    [‘site:{domain} inurl:3000/login intitle:Grafana’],
“jQuery”:     [‘site:{domain} inurl:jquery-1’, ‘site:{domain} inurl:jquery-2’],
}

class TechFingerprintAgent(BaseAgent):
“””
Rileva tecnologie usate dal target da page_content + response_headers.

```
For each result with available content:
  - Identifies CMS, frameworks, JS libraries, servers, languages
  - Attempts to extract specific versions
  - Produces 'tech_fingerprint' (dict) and adds targeted CVE dorks
    to feed DorkCrawlerAgent in the next round

Adds 'tech_fingerprint' to each processed result.
Also returns 'cve_dorks' (List[str]) in the return value.
"""

def __init__(self, plugin=None):
    super().__init__(plugin, name="TechFingerprintAgent")

def run(self, results: List[dict]) -> List[dict]:
    candidates = [
        r for r in results
        if r.get("page_content") or r.get("response_headers") or r.get("snippet")
    ]
    if not candidates:
        _log(f"[{self.name}] No content available.", style="dim")
        return results

    _log(f"[{self.name}] Fingerprinting {len(candidates)} results...", style="bold cyan")

    total_techs = 0
    for r in candidates:
        # Merge all available text
        text = " ".join(filter(None, [
            r.get("page_content", ""),
            r.get("snippet", ""),
            r.get("url", ""),
            r.get("title", ""),
            " ".join(str(v) for v in (r.get("response_headers") or {}).values()),
        ]))
        fp = self._fingerprint(text, r.get("url", ""))
        if fp["techs"]:
            r["tech_fingerprint"] = fp
            total_techs += len(fp["techs"])
            _log(
                f"[{self.name}] [{r.get('triage_label','?')}] "
                f"{', '.join(t['name'] for t in fp['techs'][:5])} — {r.get('url','')[:55]}",
                style="cyan"
            )

    _log(f"[{self.name}] Completed: {total_techs} technologies detected.", style="bold green")
    return results

def _fingerprint(self, text: str, url: str) -> dict:
    fp: dict = {"url": url, "techs": [], "cve_dorks": []}
    seen: set = set()

    domain = ""
    try:
        domain = urlparse(url).netloc
    except Exception:
        pass

    for pattern, name, category in _TECH_SIGNATURES:
        m = pattern.search(text)
        if m and name not in seen:
            seen.add(name)
            entry: dict = {"name": name, "category": category}
            # Prova a estrarre la versione dal gruppo di cattura
            if m.lastindex:
                entry["version"] = m.group(1)
            fp["techs"].append(entry)

            # Generate CVE dorks if available
            if name in _TECH_CVE_DORK_TEMPLATES and domain:
                for tmpl in _TECH_CVE_DORK_TEMPLATES[name]:
                    fp["cve_dorks"].append(tmpl.replace("{domain}", domain))

    return fp

def get_all_cve_dorks(self, results: List[dict]) -> List[str]:
    """Collects all generated CVE dorks — to be passed to DorkCrawlerAgent."""
    dorks: List[str] = []
    seen: set = set()
    for r in results:
        for d in r.get("tech_fingerprint", {}).get("cve_dorks", []):
            if d not in seen:
                seen.add(d)
                dorks.append(d)
    return dorks
```

# ══════════════════════════════════════════════════════════════════════════════

# EMAIL HARVESTER AGENT (v4.8)

# ══════════════════════════════════════════════════════════════════════════════

*EMAIL_RE = re.compile(r”\b[A-Za-z0-9.*%+-]+@[A-Za-z0-9.-]+.[A-Za-z]{2,}\b”)

# Categorie email per prefisso

_EMAIL_CATEGORIES = {
“admin”:    re.compile(r”^(?:admin|administrator|root|sysadmin|webmaster|hostmaster|postmaster)@”, re.I),
“security”: re.compile(r”^(?:security|abuse|vuln|pentest|csirt|cert|soc|noc|infosec)@”,          re.I),
“info”:     re.compile(r”^(?:info|contact|hello|support|help|service|sales|marketing)@”,          re.I),
“noreply”:  re.compile(r”^(?:no.?reply|noreply|donotreply|mailer.?daemon|bounce)@”,               re.I),
}

class EmailHarvesterAgent(BaseAgent):
“””
Collects and categorises email addresses from snippet + page_content.

```
Categories: admin, security, info, noreply, personal (everything else).
Produces 'emails_found' (List[dict]) for the result and a global list
accessible via get_all_emails().

Does not perform HTTP requests — works on already present data.
"""

def __init__(self, plugin=None):
    super().__init__(plugin, name="EmailHarvesterAgent")
    self._global_emails: Dict[str, dict] = {}  # email → entry, global dedup

def run(self, results: List[dict]) -> List[dict]:
    candidates = [
        r for r in results
        if r.get("page_content") or r.get("snippet")
    ]
    if not candidates:
        _log(f"[{self.name}] No content available.", style="dim")
        return results

    _log(f"[{self.name}] Email harvesting on {len(candidates)} results...", style="bold cyan")

    for r in candidates:
        text = (r.get("page_content", "") or "") + " " + (r.get("snippet", "") or "")
        found = self._harvest(text, r.get("url", ""))
        if found:
            r["emails_found"] = found
            _log(
                f"[{self.name}] {len(found)} email → {r.get('url','')[:65]}",
                style="yellow"
            )

    total = len(self._global_emails)
    _log(f"[{self.name}] Completed: {total} unique emails found.", style="bold green")
    return results

def _harvest(self, text: str, source_url: str) -> List[dict]:
    found = []
    for m in _EMAIL_RE.finditer(text):
        email = m.group(0).lower().strip()
        if email in self._global_emails:
            continue  # global dedup
        category = self._categorize(email)
        entry = {
            "email":    email,
            "category": category,
            "source":   source_url,
        }
        self._global_emails[email] = entry
        found.append(entry)
    return found

@staticmethod
def _categorize(email: str) -> str:
    for cat, pat in _EMAIL_CATEGORIES.items():
        if pat.match(email):
            return cat
    return "personal"

def get_all_emails(self) -> List[dict]:
    """Returns all collected emails, sorted by category."""
    order = {"admin": 0, "security": 1, "info": 2, "personal": 3, "noreply": 4}
    return sorted(self._global_emails.values(), key=lambda e: order.get(e["category"], 9))
```

# ══════════════════════════════════════════════════════════════════════════════

# PII DETECTOR AGENT (v4.8)

# ══════════════════════════════════════════════════════════════════════════════

class PiiDetectorAgent(BaseAgent):
“””
Detects personal data (PII) in snippet + page_content.

```
Types detected: email, phone (IT/EU/US), IBAN, Italian fiscal code,
credit card (Luhn validation), US SSN, date of birth, passport,
public IPs.

Adds 'pii_found' (List[dict]) to each result with findings.
Separate from SecretsAgent — PII ≠ technical credentials.
"""

def __init__(self, plugin=None, max_content: int = 8000):
    super().__init__(plugin, name="PiiDetectorAgent")
    self.max_content = max_content

def run(self, results: List[dict]) -> List[dict]:
    candidates = [
        r for r in results
        if r.get("page_content") or r.get("snippet")
    ]
    if not candidates:
        _log(f"[{self.name}] No content available.", style="dim")
        return results

    _log(f"[{self.name}] PII scan on {len(candidates)} results...", style="bold cyan")

    total_found = 0
    for r in candidates:
        content = ((r.get("page_content", "") or "") + " " + (r.get("snippet", "") or ""))
        content = content[:self.max_content]
        findings = self._scan(content, r.get("url", ""))
        if findings:
            r["pii_found"] = findings
            total_found += len(findings)
            _log(
                f"[{self.name}] {len(findings)} PII → "
                f"[{r.get('triage_label','?')}] {r.get('url','')[:60]}",
                style="bold red"
            )

    _log(
        f"[{self.name}] Completed: {total_found} total PII found.",
        style="bold green" if total_found == 0 else "bold red"
    )
    return results

def _scan(self, content: str, url: str) -> List[dict]:
    findings = []
    seen: set = set()

    for category, pattern, description, has_group in _PII_PATTERNS:
        for match in pattern.finditer(content):
            if has_group and match.lastindex:
                raw_value = match.group(1).strip()
            else:
                raw_value = match.group(0).strip()

            if not raw_value or len(raw_value) < 4:
                continue

            # Validazione speciale Luhn per carte di credito
            if category == "CREDIT_CARD" and not _luhn_check(raw_value):
                continue

            norm = re.sub(r"\s", "", raw_value.lower())
            if norm in seen:
                continue
            seen.add(norm)

            start   = max(0, match.start() - 50)
            end     = min(len(content), match.end() + 50)
            context = content[start:end].replace("\n", " ").strip()

            findings.append({
                "type":    category,
                "value":   _censor(raw_value, visible=3),
                "desc":    description,
                "context": context[:140],
                "source":  url,
            })

    return findings
```

# ══════════════════════════════════════════════════════════════════════════════

# SUBDOMAIN HARVESTER AGENT (v4.8)

# ══════════════════════════════════════════════════════════════════════════════

class SubdomainHarvesterAgent(BaseAgent):
“””
Extracts subdomains from URL + snippet + page_content of all results.

```
For each detected base domain collects unique subdomains, deduplicates them
and generates 'site:sub.domain.*' dorks ready to be injected into the
DorkCrawlerAgent in the next round.

Adds 'subdomains' (List[str]) to each result and produces a global list
accessible via get_all_subdomains() and get_followup_dorks().
"""

def __init__(self, plugin=None):
    super().__init__(plugin, name="SubdomainHarvesterAgent")
    self._global_subdomains: Dict[str, set] = {}  # base_domain → {subdomains}

def run(self, results: List[dict]) -> List[dict]:
    if not results:
        return results

    _log(f"[{self.name}] Subdomain harvesting on {len(results)} results...", style="bold cyan")

    # Extract base domain from the majority of URLs
    base_domains: set = set()
    for r in results:
        bd = self._base_domain(r.get("url", ""))
        if bd:
            base_domains.add(bd)
    if not base_domains:
        _log(f"[{self.name}] No base domain found.", style="dim")
        return results

    _log(f"[{self.name}] Domini base: {', '.join(list(base_domains)[:5])}", style="dim")

    # Build regex to search for subdomains of each base domain
    for r in results:
        text = " ".join(filter(None, [
            r.get("url", ""),
            r.get("snippet", ""),
            r.get("page_content", ""),
            r.get("title", ""),
        ]))
        found_subs = []
        for bd in base_domains:
            subs = self._extract_subdomains(text, bd)
            for s in subs:
                if bd not in self._global_subdomains:
                    self._global_subdomains[bd] = set()
                self._global_subdomains[bd].add(s)
                found_subs.append(s)
        if found_subs:
            r["subdomains"] = sorted(set(found_subs))

    total = sum(len(v) for v in self._global_subdomains.values())
    _log(f"[{self.name}] Completed: {total} unique subdomains found.", style="bold green")
    for bd, subs in self._global_subdomains.items():
        _log(f"[{self.name}]   {bd}: {', '.join(sorted(subs)[:8])}", style="dim")
    return results

@staticmethod
def _base_domain(url: str) -> str:
    """Extracts the base domain (e.g. example.com from sub.example.com)."""
    try:
        host = urlparse(url).netloc.lower()
        host = host.split(":")[0]  # rimuovi porta
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
    except Exception:
        pass
    return ""

@staticmethod
def _extract_subdomains(text: str, base_domain: str) -> List[str]:
    """Finds all occurrences of *.base_domain in the text."""
    escaped = re.escape(base_domain)
    pattern = re.compile(
        r"\b((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+?"
        + escaped + r")\b"
    )
    results = []
    for m in pattern.finditer(text):
        sub = m.group(1).lower()
        # Exclude the base domain itself and nonsensical patterns
        if sub != base_domain and len(sub) < 200:
            results.append(sub)
    return results

def get_all_subdomains(self) -> Dict[str, List[str]]:
    """Returns all subdomains found per base domain."""
    return {bd: sorted(subs) for bd, subs in self._global_subdomains.items()}

def get_followup_dorks(self) -> List[str]:
    """Generates site:subdomain dorks to feed DorkCrawlerAgent."""
    dorks = []
    for bd, subs in self._global_subdomains.items():
        for sub in sorted(subs):
            dorks.append(f'site:{sub}')
            dorks.append(f'site:{sub} inurl:admin')
            dorks.append(f'site:{sub} inurl:.env OR inurl:.git')
    return dorks
```

# ══════════════════════════════════════════════════════════════════════════════

# DORK CRAWLER AGENT — recursive adaptive dorking

# ══════════════════════════════════════════════════════════════════════════════

# Template di dork per CMS/tecnologie rilevate

*CMS_DORK_TEMPLATES: Dict[str, List[str]] = {
“wordpress”: [
‘site:{domain} inurl:wp-config.php’,
‘site:{domain} inurl:wp-content/uploads filetype:php’,
‘site:{domain} inurl:wp-json/wp/v2/users’,
‘site:{domain} inurl:xmlrpc.php’,
‘site:{domain} inurl:wp-admin/install.php’,
‘site:{domain} filetype:log inurl:wp-content’,
],
“joomla”: [
‘site:{domain} inurl:configuration.php’,
‘site:{domain} inurl:administrator/index.php’,
’site:{domain} inurl:components/com*’,
‘site:{domain} filetype:xml inurl:joomla’,
],
“drupal”: [
‘site:{domain} inurl:sites/default/settings.php’,
‘site:{domain} inurl:/user/login’,
‘site:{domain} inurl:node?destination=’,
‘site:{domain} filetype:php inurl:modules’,
],
“laravel”: [
‘site:{domain} inurl:.env’,
‘site:{domain} filetype:log inurl:storage/logs’,
‘site:{domain} inurl:public/index.php’,
‘site:{domain} inurl:api/v1’,
],
“django”: [
‘site:{domain} inurl:admin/’,
‘site:{domain} “debug” “traceback” “request”’,
‘site:{domain} inurl:static/ filetype:py’,
‘site:{domain} filetype:sqlite3’,
],
“phpmyadmin”: [
‘site:{domain} inurl:phpmyadmin/index.php’,
‘site:{domain} inurl:pma/ intitle:phpMyAdmin’,
‘site:{domain} inurl:phpmyadmin setup’,
],
“adminer”: [
‘site:{domain} inurl:adminer.php’,
‘site:{domain} inurl:adminer/ intitle:Adminer’,
],
“magento”: [
‘site:{domain} inurl:/admin/ intitle:Magento’,
‘site:{domain} inurl:app/etc/local.xml’,
‘site:{domain} inurl:downloader/index.php’,
],
“prestashop”: [
‘site:{domain} inurl:admin123’,
‘site:{domain} inurl:/config/settings.inc.php’,
‘site:{domain} inurl:modules/paypal’,
],
}

# Templates for interesting paths found

_PATH_DORK_TEMPLATES: List[str] = [
‘site:{domain} inurl:{path}’,
‘site:{domain} inurl:{path} filetype:php’,
‘site:{domain} inurl:{path} filetype:env’,
‘site:{domain} inurl:{path} filetype:log’,
‘site:{domain} inurl:{path} filetype:sql’,
‘site:{domain} inurl:{path} filetype:bak’,
‘site:{domain} inurl:{path} intitle:“index of”’,
]

# Template per estensioni file sensibili trovate

_EXT_DORK_TEMPLATES: Dict[str, List[str]] = {
“.env”:    [‘site:{domain} filetype:env’, ‘site:{domain} inurl:.env.backup’, ‘site:{domain} inurl:.env.old’],
“.sql”:    [‘site:{domain} filetype:sql’, ‘site:{domain} inurl:backup filetype:sql’, ‘site:{domain} inurl:dump filetype:sql’],
“.bak”:    [‘site:{domain} filetype:bak’, ‘site:{domain} inurl:backup filetype:bak’, ‘site:{domain} ext:bak’],
“.log”:    [‘site:{domain} filetype:log’, ‘site:{domain} inurl:logs filetype:log’, ‘site:{domain} ext:log inurl:error’],
“.php”:    [‘site:{domain} filetype:php inurl:config’, ‘site:{domain} filetype:php inurl:install’, ‘site:{domain} filetype:php inurl:setup’],
“.xml”:    [‘site:{domain} filetype:xml inurl:config’, ‘site:{domain} filetype:xml inurl:api’, ‘site:{domain} ext:xml inurl:sitemap’],
“.json”:   [‘site:{domain} filetype:json inurl:api’, ‘site:{domain} filetype:json inurl:config’, ‘site:{domain} ext:json inurl:secret’],
“.yaml”:   [‘site:{domain} filetype:yaml’, ‘site:{domain} ext:yml inurl:config’, ‘site:{domain} filetype:yml inurl:docker’],
“.conf”:   [‘site:{domain} filetype:conf’, ‘site:{domain} ext:conf inurl:nginx’, ‘site:{domain} ext:conf inurl:apache’],
“.sqlite”: [‘site:{domain} filetype:sqlite’, ‘site:{domain} ext:db’, ‘site:{domain} filetype:sqlite3’],
“.git”:    [‘site:{domain} inurl:.git/config’, ‘site:{domain} inurl:.git/HEAD’, ‘site:{domain} inurl:.git/COMMIT_EDITMSG’],
}

# Pattern per riconoscere tecnologie dagli snippet/titoli/URL

*TECH_DETECTION: List[Tuple[re.Pattern, str]] = [
(re.compile(r”wp-content|wp-admin|wordpress”,            re.I), “wordpress”),
(re.compile(r”joomla|com_content|option=com*”,           re.I), “joomla”),
(re.compile(r”drupal|sites/default|node/\d+”,            re.I), “drupal”),
(re.compile(r”laravel|artisan|eloquent|blade.php”,      re.I), “laravel”),
(re.compile(r”django|wsgi|settings.py|manage.py”,      re.I), “django”),
(re.compile(r”phpmyadmin|pma_|phpMyAdmin”,               re.I), “phpmyadmin”),
(re.compile(r”adminer.php|adminer/”,                    re.I), “adminer”),
(re.compile(r”magento|mage/|varien/”,                    re.I), “magento”),
(re.compile(r”prestashop|/modules/|/themes/community”,   re.I), “prestashop”),
]

# Path considerati “interessanti” per il follow-up

_INTERESTING_PATHS = re.compile(
r”/(admin|administrator|backup|backups|config|configs|api|v1|v2|v3|”
r”debug|test|tests|dev|staging|old|archive|logs|log|uploads|files|”
r”db|database|sql|data|export|dump|install|setup|portal|panel|”
r”private|secret|hidden|internal|manage|management|dashboard)/”,
re.I
)

# Parametri GET sospetti

_SUSPICIOUS_PARAMS = re.compile(
r”[?&](id|file|path|page|url|redirect|include|require|src|doc|”
r”template|view|module|action|query|search|q|load|read|show|”
r”download|open|image|img|lang|locale)=”,
re.I
)

class DorkCrawlerAgent(BaseAgent):
“””
Agente di crawling ricorsivo adattivo tramite DDGS.

```
Runs multiple rounds of dorking, automatically refining the dorks
each round based on patterns found in previous results.
Zero LLM — entirely based on regex, templates and pattern matching.

Round pipeline:
  1. Search with current dorks via DDGS
  2. TriageAgent classifies new results
  3. _extract_intelligence() extracts patterns: domains, paths, CMS, ext
  4. _generate_followup_dorks() produces new targeted dorks
  5. Controlla stop conditions
  6. Riparte dal passo 1 con i nuovi dork

Stop conditions (all evaluated before triggering):
  - Raggiunto max_rounds
  - Raggiunto max_results totali
  - No new HIGH/CRITICAL results in the last round
  - No new dorks can be generated (all already used)

Args:
    plugin:         LLMProvider opzionale (arricchisce il triage se presente)
    max_rounds:     numero massimo di round (default: 4)
    max_results:    total aggregated results limit (default: 300)
    results_per_dork: DDGS results per dork per round (default: 20)
    min_new_high:   min. nuovi HIGH/CRITICAL per continuare (default: 1)
    delay_between:  pause in seconds between searches (default: 3.0)
    stealth:        rallenta ulteriormente per evitare rate limit (default: False)
"""

def __init__(
    self,
    plugin          = None,
    max_rounds:     int   = 4,
    max_results:    int   = 300,
    results_per_dork: int = 20,
    min_new_high:   int   = 1,
    delay_between:  float = 3.0,
    stealth:        bool  = False,
):
    super().__init__(plugin, name="DorkCrawlerAgent")
    self.max_rounds       = max_rounds
    self.max_results      = max_results
    self.results_per_dork = results_per_dork
    self.min_new_high     = min_new_high
    self.delay_between    = delay_between * (2.0 if stealth else 1.0)
    self.stealth          = stealth

    # Stato interno del crawl
    self._all_results:   List[dict] = []
    self._seen_urls:     set        = set()
    self._used_dorks:    set        = set()
    self._round_log:     List[dict] = []

# ── Entry point ───────────────────────────────────────────────────────────

def run(
    self,
    seed_dorks: List[str],
    target:     str = "",
) -> dict:
    """
    Runs the adaptive recursive crawl.

    Args:
        seed_dorks: lista dork di partenza (round 1)
        target:     descrizione del target (per il log)

    Returns:
        dict con:
            results       — all aggregated and triaged results
            rounds        — number of completed rounds
            dorks_used    — all dorks used
            round_log     — detail per round
            stop_reason   — reason for stopping
    """
    if not seed_dorks:
        _log(f"[{self.name}] No seed dorks provided.", style="yellow")
        return self._build_output("no_seed_dorks")

    _log(
        f"[{self.name}] Starting recursive crawl — "
        f"seed:{len(seed_dorks)} dork | "
        f"max_rounds:{self.max_rounds} | "
        f"max_results:{self.max_results} | "
        f"stealth:{'on' if self.stealth else 'off'}",
        style="bold cyan"
    )
    if target:
        _log(f"[{self.name}] Target: {target}", style="cyan")

    current_dorks = list(seed_dorks)
    stop_reason   = "completed"

    try:
        from ddgs import DDGS
    except ImportError:
        _log(f"[{self.name}] ddgs non installato. Installa con: pip install ddgs", style="red")
        return self._build_output("ddgs_missing")

    triage_agent = TriageAgent(plugin=self.plugin)

    for round_n in range(1, self.max_rounds + 1):
        if not current_dorks:
            stop_reason = "no_new_dorks"
            break
        if len(self._all_results) >= self.max_results:
            stop_reason = "max_results_reached"
            break

        _log(
            f"\n[{self.name}] ── Round {round_n}/{self.max_rounds} "
            f"({len(current_dorks)} dork, "
            f"{len(self._all_results)} results so far) ──",
            style="bold cyan"
        )

        # ── Search with current dorks ─────────────────────────────────
        round_results = self._search_dorks(current_dorks, DDGS)

        # Dedup globale
        new_results = []
        for r in round_results:
            url = r.get("url", "")
            if url and url not in self._seen_urls:
                self._seen_urls.add(url)
                new_results.append(r)

        _log(
            f"[{self.name}] Round {round_n}: "
            f"{len(round_results)} found, {len(new_results)} new unique",
            style="cyan"
        )

        if not new_results:
            _log(f"[{self.name}] No new results — stopping.", style="yellow")
            stop_reason = "no_new_results"
            break

        # ── Triage new results ────────────────────────────────────────
        new_triaged = triage_agent.run(new_results, use_llm=self.has_llm)
        self._all_results.extend(new_triaged)

        # Conta HIGH/CRITICAL in questo round
        n_high = sum(
            1 for r in new_triaged
            if r.get("triage_label") in ("CRITICAL", "HIGH")
        )
        _log(
            f"[{self.name}] Triage round {round_n}: "
            f"CRITICAL+HIGH={n_high} | "
            f"TOTAL={len(self._all_results)}",
            style="green" if n_high > 0 else "dim"
        )

        # Log del round
        self._round_log.append({
            "round":       round_n,
            "dorks_used":  list(current_dorks),
            "found":       len(round_results),
            "new_unique":  len(new_results),
            "high_crit":   n_high,
            "total_so_far": len(self._all_results),
        })

        # ── Stop condition: no nuovi HIGH/CRITICAL dopo round 1 ────────
        if round_n > 1 and n_high < self.min_new_high:
            _log(
                f"[{self.name}] Only {n_high} new HIGH/CRITICAL "
                f"(min={self.min_new_high}) — stop.",
                style="yellow"
            )
            stop_reason = "no_new_findings"
            break

        # ── Ultimo round: non generare altri dork ──────────────────────
        if round_n == self.max_rounds:
            stop_reason = "max_rounds_reached"
            break

        # ── Extract intelligence and generate follow-up dorks ─────────
        intelligence = self._extract_intelligence(new_triaged)
        self._log_intelligence(intelligence, round_n)

        next_dorks = self._generate_followup_dorks(intelligence)
        if not next_dorks:
            _log(f"[{self.name}] No new dorks can be generated — stopping.", style="yellow")
            stop_reason = "no_new_dorks"
            break

        current_dorks = next_dorks
        _log(
            f"[{self.name}] {len(current_dorks)} dork follow-up generati per round {round_n+1}",
            style="bold cyan"
        )
        for d in current_dorks[:8]:
            _log(f"  → {d}", style="dim")
        if len(current_dorks) > 8:
            _log(f"  ... e altri {len(current_dorks)-8}", style="dim")

        # Pausa anti rate-limit
        if round_n < self.max_rounds:
            _log(
                f"[{self.name}] Pausa {self.delay_between:.1f}s "
                f"(stealth: {'on' if self.stealth else 'off'})...",
                style="dim"
            )
            time.sleep(self.delay_between)

    # ── Ordinamento finale per score ───────────────────────────────────
    self._all_results.sort(
        key=lambda x: x.get("triage_score", 0), reverse=True
    )

    output = self._build_output(stop_reason)
    self._print_summary(output)
    return output

# ── DDGS search ───────────────────────────────────────────────────────────

def _search_dorks(self, dorks: List[str], DDGS) -> List[dict]:
    """Executes DDGS searches for all dorks in the current round."""
    results = []
    for dork in dorks:
        if dork in self._used_dorks:
            continue
        self._used_dorks.add(dork)
        _log(f"[{self.name}] Cerco: {dork[:80]}", style="dim")
        try:
            for item in DDGS().text(dork, max_results=self.results_per_dork):
                url = item.get("href") or item.get("url", "")
                if not url:
                    continue
                results.append({
                    "url":       url,
                    "title":     item.get("title", ""),
                    "snippet":   item.get("body", ""),
                    "dork":      dork,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "extension": Path(urlparse(url).path).suffix.lower(),
                    "category":  "webpage",
                })
        except Exception as e:
            _log(f"[{self.name}] Errore DDGS '{dork[:50]}': {e}", style="yellow")

        # Small pause between dorks in the same round
        time.sleep(max(1.0, self.delay_between / 3))

    return results

# ── Intelligence extraction ───────────────────────────────────────────────

def _extract_intelligence(self, results: List[dict]) -> dict:
    intelligence: dict = {
        "domains": set(), "paths": set(), "technologies": set(),
        "extensions": set(), "params": set(),
    }
    prioritized = sorted(results, key=lambda r: r.get("triage_score", 0), reverse=True)

    for r in prioritized:
        url      = r.get("url", "")
        title    = r.get("title", "")
        snippet  = r.get("snippet", "") or ""
        combined = f"{url} {title} {snippet}"

        parsed = urlparse(url)
        if parsed.netloc:
            domain = parsed.netloc.lstrip("www.")
            intelligence["domains"].add(domain)

        path = parsed.path
        for m in _INTERESTING_PATHS.finditer(path):
            intelligence["paths"].add(m.group(1).lower())

        for pattern, tech in _TECH_DETECTION:
            if pattern.search(combined):
                intelligence["technologies"].add(tech)

        ext = Path(path).suffix.lower()
        if ext and ext in _EXT_DORK_TEMPLATES:
            intelligence["extensions"].add(ext)

        for m in _SUSPICIOUS_PARAMS.finditer(url):
            intelligence["params"].add(m.group(1).lower())

    return {k: sorted(v) for k, v in intelligence.items()}

# ── Dork generation ───────────────────────────────────────────────────────

def _generate_followup_dorks(self, intelligence: dict) -> List[str]:
    generated: set = set()
    domains      = intelligence.get("domains", [])[:8]
    paths        = intelligence.get("paths", [])[:5]
    technologies = intelligence.get("technologies", [])
    extensions   = intelligence.get("extensions", [])
    params       = intelligence.get("params", [])[:4]

    for tech in technologies:
        templates = _CMS_DORK_TEMPLATES.get(tech, [])
        for tmpl in templates:
            for domain in domains:
                dork = tmpl.format(domain=domain)
                if dork not in self._used_dorks:
                    generated.add(dork)

    for path in paths:
        for domain in domains[:4]:
            for tmpl in _PATH_DORK_TEMPLATES[:3]:
                dork = tmpl.format(domain=domain, path=path)
                if dork not in self._used_dorks:
                    generated.add(dork)

    for ext in extensions:
        templates = _EXT_DORK_TEMPLATES.get(ext, [])
        for tmpl in templates[:2]:
            for domain in domains[:4]:
                dork = tmpl.format(domain=domain)
                if dork not in self._used_dorks:
                    generated.add(dork)

    for param in params:
        for domain in domains[:3]:
            for d in [
                f'site:{domain} inurl:"?{param}="',
                f'site:{domain} inurl:"{param}=" filetype:php',
            ]:
                if d not in self._used_dorks:
                    generated.add(d)

    for domain in domains[:5]:
        for d in [
            f'site:{domain} intitle:"index of"',
            f'site:{domain} inurl:backup',
            f'site:{domain} inurl:.git',
            f'site:{domain} inurl:api',
            f'site:{domain} filetype:env',
        ]:
            if d not in self._used_dorks:
                generated.add(d)

    return list(generated)

# ── Helpers ───────────────────────────────────────────────────────────────

def _log_intelligence(self, intel: dict, round_n: int) -> None:
    parts = []
    if intel.get("domains"):      parts.append(f"domini:{len(intel['domains'])}")
    if intel.get("technologies"): parts.append(f"tech:{','.join(intel['technologies'])}")
    if intel.get("paths"):        parts.append(f"path:{len(intel['paths'])}")
    if intel.get("extensions"):   parts.append(f"ext:{','.join(intel['extensions'])}")
    if intel.get("params"):       parts.append(f"params:{','.join(intel['params'])}")
    _log(
        f"[{self.name}] Intelligence round {round_n}: "
        + (" | ".join(parts) if parts else "nulla di nuovo"),
        style="cyan"
    )

def _build_output(self, stop_reason: str) -> dict:
    return {
        "results":     self._all_results,
        "rounds":      len(self._round_log),
        "dorks_used":  sorted(self._used_dorks),
        "round_log":   self._round_log,
        "stop_reason": stop_reason,
        "total":       len(self._all_results),
        "critical":    sum(1 for r in self._all_results if r.get("triage_label") == "CRITICAL"),
        "high":        sum(1 for r in self._all_results if r.get("triage_label") == "HIGH"),
        "medium":      sum(1 for r in self._all_results if r.get("triage_label") == "MEDIUM"),
    }

def _print_summary(self, output: dict) -> None:
    _panel(
        f"  Rounds completed  : {output['rounds']}/{self.max_rounds}\n"
        f"  Stop reason       : {output['stop_reason']}\n"
        f"  Dork usati        : {len(output['dorks_used'])}\n"
        f"  Total results     : {output['total']}\n"
        f"  CRITICAL          : {output['critical']}\n"
        f"  HIGH              : {output['high']}\n"
        f"  MEDIUM            : {output['medium']}",
        title="[bold cyan][ DorkCrawlerAgent — Crawl Summary ][/bold cyan]",
        border="cyan",
    )
```

# ══════════════════════════════════════════════════════════════════════════════

# CLI INTEGRATION

# ══════════════════════════════════════════════════════════════════════════════

def add_crawler_args(parser) -> object:
“”“Adds –crawl-* flags to the DorkEye CLI parser.”””
g = parser.add_argument_group(
“Recursive Crawl — adaptive multi-round dorking (no AI)”
)
g.add_argument(”–crawl”, action=“store_true”,
help=“Activate the adaptive recursive crawl after the initial search”)
g.add_argument(”–crawl-rounds”, type=int, default=4,
help=“Numero massimo di round di raffinamento (default: 4)”)
g.add_argument(”–crawl-max”, type=int, default=300,
help=“Total aggregated results limit (default: 300)”)
g.add_argument(”–crawl-per-dork”, type=int, default=20,
help=“DDGS results per dork per round (default: 20)”)
g.add_argument(”–crawl-stealth”, action=“store_true”,
help=“Stealth mode: longer delays between searches”)
g.add_argument(”–crawl-report”, action=“store_true”,
help=“Generate HTML report at the end of the crawl”)
g.add_argument(”–crawl-out”, type=str, default=None,
help=“Path report crawl (default: dorkeye_crawl_<timestamp>.html)”)
return parser

def add_security_args(parser) -> object:
“”“Adds –security-* flags to the DorkEye CLI parser.”””
g = parser.add_argument_group(
“Security Agent — threat detection for phishing, malware, exploits”
)
g.add_argument(”–no-security”, action=“store_true”,
help=“Disable the SecurityAgent in the pipeline”)
g.add_argument(”–security-mode”, type=str, default=“passive”,
choices=[“active”, “passive”],
help=“active: block DANGEROUS/CRITICAL | passive: report only (default: passive)”)
g.add_argument(”–security-quarantine”, action=“store_true”,
help=“Save quarantined content to dorkeye_quarantine/”)
return parser

def run_crawl(
seed_dorks: List[str],
args,
target:  str = “”,
plugin       = None,
) -> dict:
“””
Entry point for dorkeye.py — starts the DorkCrawlerAgent.
“””
crawler = DorkCrawlerAgent(
plugin           = plugin,
max_rounds       = getattr(args, “crawl_rounds”,   4),
max_results      = getattr(args, “crawl_max”,      300),
results_per_dork = getattr(args, “crawl_per_dork”, 20),
stealth          = getattr(args, “crawl_stealth”,  False),
)

```
output = crawler.run(seed_dorks=seed_dorks, target=target)

# Report opzionale
if getattr(args, "crawl_report", False) and output.get("results"):
    fmt = "html"
    out = getattr(args, "crawl_out", None)
    if not out:
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"dorkeye_crawl_{ts}.{fmt}"

    reporter = ReportAgent()
    reporter.run(
        results     = output["results"],
        analysis    = {},
        target      = target,
        output_path = out,
        fmt         = fmt,
    )
    output["report_path"] = out
    _log(f"[Crawl] Report saved: {out}", style="bold green")

return output
```

def run_analysis_pipeline(
results:    List[dict],
llm_plugin = None,
args       = None,
target:    str = “”,
) -> dict:
“””
Runs the post-search analysis pipeline v3.1.

```
Works WITHOUT LLM (llm_plugin=None):
    1.  TriageAgent             — classifies with regex + runtime bonus
    2.  PageFetchAgent          — downloads HIGH/CRITICAL pages (if --analyze-fetch)
    3.  SecurityAgent  [NEW]    — phishing/malware/exploit/obfuscation detection
    4.  HeaderIntelAgent        — analyses response headers
    5.  TechFingerprintAgent    — detects CMS/frameworks/versions
    6.  SecretsAgent            — secrets scan + hash + severity
    7.  PiiDetectorAgent        — detects PII (CC, IBAN, CF, SSN, etc.)
    8.  EmailHarvesterAgent     — collects and categorises emails
    9.  SubdomainHarvesterAgent — extracts subdomains, generates follow-up dorks
    10. ReportAgent             — generates complete HTML/MD/JSON report (incl. security)

Args:
    results:    DorkEye results list
    llm_plugin: DorkEyeLLMPlugin (optional — None = regex only)
    args:       argparse.Namespace con i flag --analyze-* e --security-*
    target:     descrizione target (per il report)

Returns:
    dict con: triaged, secrets_total, pii_total, emails_total,
              subdomains, cve_dorks, report_path, analysis,
              security_stats, security_threats
"""
if args is None:
    args = type("A", (), {
        "analyze_fetch":         False,
        "analyze_fetch_max":     20,
        "analyze_no_llm_triage": False,
        "analyze_report":        True,
        "analyze_fmt":           "html",
        "analyze_out":           None,
        "no_security":           False,
        "security_mode":         "passive",
        "security_quarantine":   False,
    })()

output = {
    "triaged":          None,
    "secrets_total":    0,
    "pii_total":        0,
    "emails_total":     0,
    "subdomains":       {},
    "cve_dorks":        [],
    "report_path":      None,
    "analysis":         {},
    "security_stats":   {},
    "security_threats": [],
}

if not results:
    _log("[Agents] No results to analyse.", style="yellow")
    return output

mode_label = "LLM + regex" if llm_plugin else "autonomous regex"
_log(f"[Agents] Pipeline v3.1 — mode: {mode_label}", style="bold cyan")

# ── 1. Triage ─────────────────────────────────────────────────────────────
use_llm_triage = (
    llm_plugin is not None
    and not getattr(args, "analyze_no_llm_triage", False)
)
triage  = TriageAgent(plugin=llm_plugin)
triaged = triage.run(results, use_llm=use_llm_triage)
output["triaged"] = triaged

counts = {l: 0 for l in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "SKIP")}
for r in triaged:
    counts[r.get("triage_label", "LOW")] = counts.get(r.get("triage_label", "LOW"), 0) + 1

_panel(
    "\n".join(
        f"  [{counts[l]:>3}]  {l}"
        for l in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "SKIP")
    ) + f"\n\n  TOTAL: {len(triaged)}",
    title="[bold cyan][ Triage Results ][/bold cyan]",
    border="cyan",
)

# ── 2. Page Fetch (opzionale) ──────────────────────────────────────────────
if getattr(args, "analyze_fetch", False):
    fetch_max = getattr(args, "analyze_fetch_max", 20)
    fetcher   = PageFetchAgent(max_pages=fetch_max)
    triaged   = fetcher.run(triaged)

# ── 3. Security Agent [NEW in v3.1] ───────────────────────────────────────
sec_agent = None
if not getattr(args, "no_security", False):
    sec_mode       = getattr(args, "security_mode", "passive")
    sec_quarantine = "dorkeye_quarantine" if getattr(args, "security_quarantine", False) else None

    sec_agent = SecurityAgent(mode=sec_mode, quarantine_dir=sec_quarantine)
    triaged   = sec_agent.run(triaged)

    # Collect security data for report
    output["security_stats"] = {
        **sec_agent.stats,
        "mode": sec_mode,
    }

    # Collect non-clean threats for report
    threat_verdicts = sec_agent.get_threats_above(ThreatLevel.LOW)
    output["security_threats"] = [v.to_dict() for v in threat_verdicts]

    # Show Rich panel with security summary
    if sec_agent.stats["total_scanned"] > 0:
        n_threats = sum(
            sec_agent.stats.get(k, 0)
            for k in ("suspicious", "dangerous", "critical")
        )
        panel_style = "red" if n_threats > 0 else "green"
        _panel(
            sec_agent.generate_console_report(),
            title=f"[bold {panel_style}][ 🛡️ Security Agent — "
                  f"{'ACTIVE' if sec_mode == 'active' else 'PASSIVE'} ][/bold {panel_style}]",
            border=panel_style,
        )

# ── 4. Header Intel ───────────────────────────────────────────────────────
header_agent = HeaderIntelAgent()
triaged      = header_agent.run(triaged)

# ── 5. Tech Fingerprint ───────────────────────────────────────────────────
tech_agent = TechFingerprintAgent()
triaged    = tech_agent.run(triaged)
cve_dorks  = tech_agent.get_all_cve_dorks(triaged)
output["cve_dorks"] = cve_dorks
if cve_dorks:
    _log(f"[Agents] TechFP: {len(cve_dorks)} CVE dork generati.", style="cyan")

# ── 6. Secrets scan ───────────────────────────────────────────────────────
use_llm_secrets = llm_plugin is not None
secrets_agent   = SecretsAgent(plugin=llm_plugin, use_llm=use_llm_secrets)
triaged         = secrets_agent.run(triaged)

all_secrets = [s for r in triaged for s in r.get("secrets", [])]
output["secrets_total"] = len(all_secrets)

if all_secrets:
    _sev_ord = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_secrets_sorted = sorted(
        all_secrets, key=lambda s: _sev_ord.get(s.get("severity", "LOW"), 9)
    )
    _panel(
        "\n".join(
            f"  [{s.get('severity','?'):8}] [{s.get('detection','?'):5}] "
            f"{s.get('type','?'):14} — {s.get('value','?')} "
            f"({s.get('source','?')[:45]})"
            for s in all_secrets_sorted[:30]
        ),
        title=f"[bold red][ {len(all_secrets)} Secret(s) Found ][/bold red]",
        border="red",
    )

# ── 7. PII Detection ──────────────────────────────────────────────────────
pii_agent = PiiDetectorAgent()
triaged   = pii_agent.run(triaged)
all_pii   = [p for r in triaged for p in r.get("pii_found", [])]
output["pii_total"] = len(all_pii)
if all_pii:
    _log(f"[Agents] PII: {len(all_pii)} dato/i personale/i rilevato/i.", style="bold red")

# ── 8. Email Harvesting ───────────────────────────────────────────────────
email_agent   = EmailHarvesterAgent()
triaged       = email_agent.run(triaged)
all_emails    = email_agent.get_all_emails()
output["emails_total"] = len(all_emails)
if all_emails:
    _log(f"[Agents] Email: {len(all_emails)} unique emails collected.", style="cyan")

# ── 9. Subdomain Harvesting ───────────────────────────────────────────────
subdomain_agent = SubdomainHarvesterAgent()
triaged         = subdomain_agent.run(triaged)
all_subdomains  = subdomain_agent.get_all_subdomains()
followup_dorks  = subdomain_agent.get_followup_dorks()
output["subdomains"] = all_subdomains
output["cve_dorks"]  = list(dict.fromkeys(cve_dorks + followup_dorks))  # dedup preserving order
if all_subdomains:
    total_subs = sum(len(v) for v in all_subdomains.values())
    _log(f"[Agents] Subdomain: {total_subs} subdomains found.", style="cyan")

# ── LLM analysis (only if llm_plugin available) ────────────────────────────
analysis: dict = {}
if llm_plugin:
    try:
        analysis = llm_plugin.analyze_results(triaged, target=target)
        output["analysis"] = analysis
        _sev   = analysis.get("severity", "LOW")
        _sc    = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "bold red"}
        _style = _sc.get(_sev, "white")
        _panel(
            f"[bold white]Summary:[/bold white] {analysis.get('summary','N/A')}\n\n"
            f"[bold yellow]High-value:[/bold yellow] "
            f"{', '.join(analysis.get('high_value',[])[:5]) or 'none'}\n"
            f"[bold cyan]Patterns:[/bold cyan] "
            f"{', '.join(analysis.get('patterns',[])[:5]) or 'none'}\n"
            f"[bold green]Recommendations:[/bold green] "
            f"{chr(10).join(analysis.get('recommendations',[])[:3]) or 'none'}\n"
            f"[bold white]Severity:[/bold white] [{_style}]{_sev}[/{_style}]",
            title="[bold magenta][ LLM Analysis ][/bold magenta]",
            border="magenta",
        )
    except Exception as e:
        _log(f"[Agents] LLM analysis error: {e}", style="yellow")

# ── 10. Report ────────────────────────────────────────────────────────────
if getattr(args, "analyze_report", False):
    fmt = getattr(args, "analyze_fmt", "html")
    out = getattr(args, "analyze_out", None)
    if not out:
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"dorkeye_analysis_{ts}.{fmt}"

    # Build security HTML section for report
    sec_html = ""
    if sec_agent:
        sec_html = sec_agent.generate_html_section()

    reporter = ReportAgent(plugin=llm_plugin)
    reporter.run(
        results     = triaged,
        analysis    = analysis,
        target      = target,
        output_path = out,
        fmt         = fmt,
        extra       = {
            "emails":           all_emails,
            "pii":              all_pii,
            "subdomains":       all_subdomains,
            "cve_dorks":        output["cve_dorks"],
            "security_html":    sec_html,
            "security_stats":   output.get("security_stats", {}),
            "security_threats": output.get("security_threats", []),
        },
    )
    output["report_path"] = out

# LLM stats
if llm_plugin:
    try:
        s = llm_plugin.stats()
        _log(
            f"[Agents] LLM — provider:{s['provider']} | "
            f"cache:{s['cache']} | mem:{s['memory_entries']}",
            style="dim"
        )
    except Exception:
        pass

return output
```

# ══════════════════════════════════════════════════════════════════════════════

# STANDALONE — analyses a DorkEye JSON results file

# ══════════════════════════════════════════════════════════════════════════════

if **name** == “**main**”:
import argparse as _ap
import sys

```
parser = _ap.ArgumentParser(
    description="DorkEye Agents v3.1 — Standalone analysis on results file",
    formatter_class=_ap.RawDescriptionHelpFormatter,
    epilog=(
        "Esempi:\n"
        "  # Standalone analysis (no LLM required)\n"
        "  python dorkeye_agents.py results.json\n"
        "  python dorkeye_agents.py results.json --analyze-fetch --analyze-fmt=html\n\n"
        "  # With security agent in active mode + quarantine\n"
        "  python dorkeye_agents.py results.json --security-mode=active --security-quarantine\n\n"
        "  # Disable security agent\n"
        "  python dorkeye_agents.py results.json --no-security\n\n"
        "  # With Ollama LLM (optional — adds summary and contextual analysis)\n"
        "  python dorkeye_agents.py results.json --llm --analyze-fetch\n"
    ),
)
parser.add_argument(
    "results_file",
    help="DorkEye JSON results file (produced with -o results.json)",
)
parser.add_argument("--target", default="", help="Descrizione target (opzionale)")
parser.add_argument("--analyze-fetch",     action="store_true",
                    help="Download HIGH/CRITICAL pages for more accurate analysis")
parser.add_argument("--analyze-fetch-max", type=int, default=20,
                    help="Max pages to download (default: 20)")
parser.add_argument("--analyze-no-llm-triage", action="store_true",
                    help="Regex-only triage (ignores LLM even if available)")
parser.add_argument("--analyze-report",    action="store_true", default=True,
                    help="Generate report file (default: True)")
parser.add_argument("--analyze-fmt",       choices=["html","md","json","txt"],
                    default="html", help="Formato report (default: html)")
parser.add_argument("--analyze-out",       default=None,
                    help="Path output report")

# Security Agent arguments
add_security_args(parser)

# Optional LLM arguments — imported only if available
_llm_available = False
try:
    from dorkeye_llm_plugin import add_llm_args, init_llm_plugin
    add_llm_args(parser)
    _llm_available = True
except ImportError:
    parser.add_argument("--llm", action="store_true",
                        help="(unavailable: dorkeye_llm_plugin.py not found)")

args     = parser.parse_args()
args.llm = getattr(args, "llm", False)

# Load results
from pathlib import Path as _Path
p = _Path(args.results_file)
if not p.exists():
    print(f"[!] File non trovato: {p}", file=sys.stderr)
    sys.exit(1)

try:
    raw_data = json.loads(p.read_text(encoding="utf-8"))
    results  = raw_data if isinstance(raw_data, list) else raw_data.get("results", [])
except Exception as e:
    print(f"[!] Errore lettura: {e}", file=sys.stderr)
    sys.exit(1)

if not results:
    print(f"[!] No results found in '{p}'.", file=sys.stderr)
    sys.exit(1)

# Init LLM (opzionale)
llm = None
if args.llm and _llm_available:
    llm = init_llm_plugin(args)
    if not llm:
        print("[!] LLM not initialised — continuing in autonomous mode.", file=sys.stderr)
elif args.llm and not _llm_available:
    print("[!] dorkeye_llm_plugin.py not found — autonomous mode.", file=sys.stderr)

print(f"\n[*] Analysing {len(results)} results from '{p.name}'")
print(f"[*] Mode: {'LLM + regex' if llm else 'autonomous (regex)'}")
sec_mode = getattr(args, "security_mode", "passive")
no_sec   = getattr(args, "no_security", False)
print(f"[*] Security: {'DISABLED' if no_sec else sec_mode.upper()}")

out = run_analysis_pipeline(
    results    = results,
    llm_plugin = llm,
    args       = args,
    target     = args.target,
)

print()
if out.get("report_path"):
    print(f"[✓] Report: {out['report_path']}")
print(f"[✓] Secrets found:     {out['secrets_total']}")
print(f"[✓] PII found:         {out.get('pii_total', 0)}")
print(f"[✓] Emails collected:  {out.get('emails_total', 0)}")
n_subs = sum(len(v) for v in out.get('subdomains', {}).values())
print(f"[✓] Subdomini:         {n_subs}")
print(f"[✓] CVE dorks:         {len(out.get('cve_dorks', []))}")

# Security summary
sec_stats = out.get("security_stats", {})
if sec_stats:
    print(f"[✓] Security scanned:  {sec_stats.get('total_scanned', 0)}")
    print(f"[✓] Security threats:  {len(out.get('security_threats', []))}")
    print(f"[✓] Security blocked:  {sec_stats.get('blocked', 0)}")

if out.get("triaged"):
    from collections import Counter
    dist = Counter(r.get("triage_label", "?") for r in out["triaged"])
    print(f"[✓] Triage: CRITICAL={dist.get('CRITICAL',0)} HIGH={dist.get('HIGH',0)} "
          f"MEDIUM={dist.get('MEDIUM',0)} LOW={dist.get('LOW',0)}")
```
