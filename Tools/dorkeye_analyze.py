#!/usr/bin/env python3
"""
DorkEye Analyzer v1.0
======================
Fully autonomous post-search analysis — zero AI, zero Ollama.

Works with Python + requests + rich only (already in requirements.txt).
Reads results saved by DorkEye (-o results.json) and produces:

  1. Triage    — classifies each result with score 0-100 (pure regex)
  2. Fetch     — downloads the real content of priority pages
  3. Secrets   — credentials and sensitive data scan (40+ regex patterns)
  4. Report    — HTML with dark theme / Markdown / JSON / text

Uso diretto su file:
    python dorkeye_analyze.py Dump/results.json
    python dorkeye_analyze.py Dump/results.json --fetch --fmt=html --out=report.html
    python dorkeye_analyze.py Dump/results.json --fetch --fetch-max=30 --fmt=md

Integrated into dorkeye.py with --analyze-local:
    python dorkeye.py --dg=all -o results.html --analyze-local
    python dorkeye.py -d dorks.txt --analyze-local --analyze-local-fetch --analyze-local-fmt=html

Autore: DorkEye Project
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser as _HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import urllib3
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Rich (optional but already in requirements.txt) ─────────────────────────
try:
    from rich.console  import Console
    from rich.panel    import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table    import Table
    from rich.rule     import Rule
    _con = Console()

    def _log(msg: str, style: str = "cyan")         -> None: _con.print(f"[{style}]{msg}[/{style}]")
    def _rule(title: str = "", style: str = "cyan") -> None: _con.print(Rule(title=title, style=style))
    def _panel(body: str, title: str = "", border: str = "cyan") -> None:
        _con.print(Panel(body, title=title, border_style=border))
    def _progress():
        return Progress(SpinnerColumn(), TextColumn("{task.description}"),
                        BarColumn(), TextColumn("{task.completed}/{task.total}"),
                        console=_con, transient=True)
    HAS_RICH = True

except ImportError:
    HAS_RICH = False
    def _log(msg: str, style: str = "")            -> None: print(msg)
    def _rule(title: str = "", style: str = "")    -> None: print(f"\n{'─'*60}  {title}")
    def _panel(body: str, title: str = "", border: str = "") -> None:
        print(f"\n[{title}]\n{body}")
    def _progress(): return None  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
#  PATTERN LIBRARY — imported from dorkeye_patterns.py
# ══════════════════════════════════════════════════════════════════════════════
from dorkeye_patterns import (
    TRIAGE_RULES,
    SECRET_RULES,
    SecretRule,
    SCORE_TO_LABEL     as _SCORE_TO_LABEL,
    FETCH_UA           as _FETCH_UA,
    SKIP_EXTENSIONS    as _SKIP_EXT,
    label_from_score   as _label,
    censor             as _censor_base,
)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _censor(value: str, show: int = 4) -> str:
    return _censor_base(value, show=show)


class _ScriptStyleStripper(_HTMLParser):
    """HTMLParser che rimuove blocchi <script> e <style> in modo sicuro.

    Replaces the bypassable regex (CWE-20/116) with the built-in parser
    che gestisce correttamente tutte le varianti sintattiche valide del
    tag di chiusura (es. </script  >, </SCRIPT\\n>, ecc.).
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._skip_tags: set = {"script", "style"}
        self._in_skip: int = 0
        self._parts: list = []

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


# Fallback regex — used ONLY if HTMLParser raises an exception on HTML
# that is severely malformed. This is NOT the primary path.
#
# FIX CWE-20/116/185/186 ("Bad HTML filtering regexp"):
#   - Opening : `(?:[^>]*)` unchanged (handles attributes without unquoted `>`)
#   - Closing : replaced `s*>` with `[^>]*>` to cover browser-accepted variants
#               come `</script anything>` o `</  script  foo>` (spazi dopo `</`
#               gestiti da `\s*` aggiunto prima del nome tag).
# This path is intentionally a last-resort: the primary path uses
# _ScriptStyleStripper (built-in HTMLParser) which is immune to these variants.
_SCRIPT_STYLE_RE_FALLBACK = re.compile(  # noqa: S608
    r"<(?:script|style)(?:[^>]*)>[\s\S]*?</\s*(?:script|style)[^>]*>",
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """Rimuove tag HTML e comprime gli spazi.

    Uses HTMLParser to strip <script>/<style> (safe against
    bypassable closing tag variants) and regex only for the
    remaining generic tags, comments and HTML entities.
    """
    stripper = _ScriptStyleStripper()
    try:
        stripper.feed(text)
        stripper.close()
        text = stripper.get_result()
    except Exception:
        text = _SCRIPT_STYLE_RE_FALLBACK.sub(" ", text)

    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>",   " ", text)
    text = re.sub(r"&[a-z]+;",  " ", text)
    text = re.sub(r"\s{3,}",   "\n", text)
    return text.strip()


def _dedup_secrets(secrets: List[dict]) -> List[dict]:
    """Deduplication by (type, value)."""
    seen, out = set(), []
    for s in secrets:
        key = (s.get("type",""), s.get("value",""))
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  TRIAGE
# ══════════════════════════════════════════════════════════════════════════════

def triage_results(results: List[dict]) -> List[dict]:
    """
    Classifies each result with score 0-100 using only regex.
    Adds: triage_score, triage_label, triage_reasons.
    Sorts by descending score.
    """
    _log("[Triage] Classifying results...", style="bold cyan")

    for r in results:
        text   = " ".join(filter(None, [r.get("url",""), r.get("title",""), r.get("snippet","")]))
        bonus  = 0
        reasons: List[str] = []

        for pattern, pts, hint in TRIAGE_RULES:
            if pattern.search(text):
                bonus += pts
                reasons.append(hint)

        score = min(bonus, 100)
        r["triage_score"]   = score
        r["triage_label"]   = _label(score)
        r["triage_reasons"] = list(dict.fromkeys(reasons))  # dedup preserving order

    results.sort(key=lambda x: x.get("triage_score", 0), reverse=True)

    counts = defaultdict(int)
    for r in results:
        counts[r["triage_label"]] += 1

    _panel(
        "\n".join(
            f"  [{counts[l]:>3}]  {l}"
            for l in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "SKIP")
        ) + f"\n\n  TOTAL: {len(results)}",
        title="[bold cyan][ Triage ][/bold cyan]" if HAS_RICH else "Triage",
        border="cyan",
    )
    return results


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE FETCH
# ══════════════════════════════════════════════════════════════════════════════

def fetch_pages(
    results:   List[dict],
    max_pages: int   = 20,
    min_label: str   = "HIGH",
    timeout:   int   = 10,
    max_chars: int   = 10000,
    delay_s:   float = 1.2,
) -> List[dict]:
    """
    Downloads the real HTML content of priority pages.
    Adds 'page_content' (str) to the processed results.
    """
    _label_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "SKIP": 0}
    min_rank    = _label_rank.get(min_label.upper(), 3)

    targets = [
        r for r in results
        if _label_rank.get(r.get("triage_label", "LOW"), 1) >= min_rank
        and "page_content" not in r
    ][:max_pages]

    if not targets:
        _log("[Fetch] No pages to download.", style="dim")
        return results

    _log(
        f"[Fetch] Downloading {len(targets)} pages "
        f"(min={min_label}, timeout={timeout}s, delay={delay_s}s)...",
        style="bold cyan"
    )

    fetched = 0
    for idx, r in enumerate(targets):
        url = r.get("url", "")
        if not url:
            continue

        # Salta estensioni binarie
        ext = Path(urlparse(url).path).suffix.lower()
        if ext in _SKIP_EXT:
            r["page_content"] = ""
            continue

        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent":      _FETCH_UA,
                    "Accept":          "text/html,application/xhtml+xml,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
                },
                allow_redirects=True,
                stream=True,
                verify=False,
            )
            if resp.status_code >= 400:
                r["page_content"] = ""
                r["fetch_status"] = resp.status_code
                _log(f"[Fetch] {resp.status_code} — {url[:70]}", style="dim")
                continue

            # Leggi al massimo max_chars*3 byte
            raw = b""
            for chunk in resp.iter_content(chunk_size=4096):
                raw += chunk
                if len(raw) > max_chars * 3:
                    break

            ct = resp.headers.get("Content-Type", "")
            if "text" not in ct and "json" not in ct and "xml" not in ct:
                r["page_content"] = ""
                continue

            text = raw.decode("utf-8", errors="replace")
            text = _strip_html(text)[:max_chars]

            r["page_content"] = text
            r["fetch_status"] = resp.status_code
            fetched += 1
            _log(
                f"[Fetch] [{r.get('triage_label','?')}] +{len(text)}c — {url[:70]}",
                style="dim"
            )

        except Exception as e:
            r["page_content"] = ""
            r["fetch_error"]  = str(e)[:80]
            _log(f"[Fetch] Error — {url[:60]}: {e}", style="yellow")

        if idx < len(targets) - 1:
            time.sleep(delay_s)

    _log(
        f"[Fetch] Completed: {fetched}/{len(targets)} pages downloaded.",
        style="green"
    )
    return results


# ══════════════════════════════════════════════════════════════════════════════
#  SECRETS SCAN
# ══════════════════════════════════════════════════════════════════════════════

def scan_secrets(results: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Regex scan on page_content (if available) or snippet.
    Adds 'secrets' (list) to each result with findings.

    Returns:
        (updated_results, global_secrets_list)
    """
    _log("[Secrets] Starting regex scan...", style="bold cyan")

    total_found   = 0
    all_secrets_g = []

    candidates = [
        r for r in results
        if (r.get("page_content") or r.get("snippet"))
        and r.get("triage_label", "SKIP") != "SKIP"
    ]

    if not candidates:
        _log("[Secrets] No content available.", style="dim")
        return results, []

    for r in candidates:
        content = r.get("page_content") or r.get("snippet") or ""
        url     = r.get("url", "")
        findings: List[dict] = []

        for category, pattern, description, has_group in SECRET_RULES:
            for match in pattern.finditer(content):
                if has_group and match.lastindex:
                    raw_val = match.group(1).strip()
                else:
                    raw_val = match.group(0).strip()

                if not raw_val or len(raw_val) < 4:
                    continue

                # Context: 70 characters around the match
                s_ctx   = max(0, match.start() - 70)
                e_ctx   = min(len(content), match.end() + 70)
                context = content[s_ctx:e_ctx].replace("\n", " ").strip()

                findings.append({
                    "type":       category,
                    "desc":       description,
                    "value":      _censor(raw_val),
                    "confidence": "HIGH",
                    "context":    context[:160],
                    "source":     url,
                })

        # Dedup by (type, value)
        findings = _dedup_secrets(findings)

        if findings:
            r["secrets"] = findings
            total_found += len(findings)
            all_secrets_g.extend(findings)
            _log(
                f"[Secrets] {len(findings):>2} found "
                f"[{r.get('triage_label','?')}] {url[:70]}",
                style="bold red"
            )

    _log(
        f"[Secrets] Scan complete: {total_found} secrets in {len(candidates)} results.",
        style="bold green" if total_found == 0 else "bold red"
    )

    if total_found > 0 and HAS_RICH:
        # Summary table by type
        by_type = defaultdict(int)
        for s in all_secrets_g:
            by_type[s["type"]] += 1
        table = Table(title="Secrets by type", style="red")
        table.add_column("Type",  style="bold red")
        table.add_column("Count", style="bold white")
        for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
            table.add_row(t, str(c))
        _con.print(table)

    return results, all_secrets_g


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════════════════════════

def build_report(
    results:    List[dict],
    all_secrets: List[dict],
    target:     str  = "",
    fmt:        str  = "html",
) -> str:
    """
    Generates the report in the chosen format.
    fmt: "html" | "md" | "json" | "txt"
    """
    now    = datetime.now().strftime("%Y-%m-%d %H:%M")
    counts = defaultdict(int)
    for r in results:
        counts[r.get("triage_label", "LOW")] += 1

    top = [r for r in results if r.get("triage_label") in ("CRITICAL", "HIGH")]

    if fmt == "json":
        return _report_json(results, all_secrets, counts, target, now)
    elif fmt == "md":
        return _report_md(results, all_secrets, counts, top, target, now)
    elif fmt == "txt":
        return _report_txt(results, all_secrets, counts, top, target, now)
    else:
        return _report_html(results, all_secrets, counts, top, target, now)


def _report_html(results, all_secrets, counts, top, target, now) -> str:
    _sc = {"CRITICAL":"#ff4444","HIGH":"#ff8800","MEDIUM":"#ffcc00","LOW":"#44cc44","SKIP":"#888"}

    def badge(lbl: str) -> str:
        c = _sc.get(lbl, "#888")
        return (f'<span style="background:{c};color:#000;padding:1px 8px;'
                f'border-radius:3px;font-size:11px;font-weight:bold">{lbl}</span>')

    rows_top = "".join(
        f"<tr>"
        f"<td>{r.get('triage_score',0)}</td>"
        f"<td>{badge(r.get('triage_label','?'))}</td>"
        f"<td><a href='{r.get('url','')}' target='_blank'>{r.get('url','')[:85]}</a></td>"
        f"<td>{', '.join(r.get('triage_reasons',[]))[:70]}</td>"
        f"</tr>"
        for r in top[:30]
    )
    rows_all = "".join(
        f"<tr>"
        f"<td>{r.get('triage_score',0)}</td>"
        f"<td>{badge(r.get('triage_label','?'))}</td>"
        f"<td><a href='{r.get('url','')}' target='_blank'>{r.get('url','')[:85]}</a></td>"
        f"<td>{r.get('title','')[:55]}</td>"
        f"<td>{'✓' if r.get('secrets') else ''}</td>"
        f"</tr>"
        for r in results
    )
    rows_sec = "".join(
        f"<tr>"
        f"<td><code>{s.get('type','?')}</code></td>"
        f"<td>{s.get('desc','')[:40]}</td>"
        f"<td><code>{s.get('value','?')}</code></td>"
        f"<td>{s.get('confidence','?')}</td>"
        f"<td><a href='{s.get('source','')}' target='_blank'>{s.get('source','')[:60]}</a></td>"
        f"</tr>"
        for s in all_secrets
    )

    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>DorkEye Analyzer — {target or 'Report'}</title>
<style>
:root{{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--text:#c9d1d9;--acc:#58a6ff;--brd:#30363d}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',Consolas,sans-serif;font-size:14px;line-height:1.6;padding:28px}}
h1{{color:var(--acc);font-size:24px;margin-bottom:4px}}
h2{{color:var(--acc);font-size:16px;margin:26px 0 10px;border-bottom:1px solid var(--brd);padding-bottom:5px}}
.meta{{color:#8b949e;font-size:12px;margin-bottom:18px}}
.card{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:14px;margin-bottom:12px}}
.metrics{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}}
.metric{{background:var(--bg3);border-radius:6px;padding:10px 18px;text-align:center;min-width:80px}}
.metric .num{{font-size:26px;font-weight:bold}}
.metric .lbl{{font-size:11px;color:#8b949e}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--bg3);padding:7px 10px;text-align:left;border-bottom:2px solid var(--brd);color:var(--acc)}}
td{{padding:5px 10px;border-bottom:1px solid var(--brd);vertical-align:top;word-break:break-word}}
tr:hover{{background:var(--bg3)}}
a{{color:var(--acc);text-decoration:none}}a:hover{{text-decoration:underline}}
code{{background:var(--bg3);padding:1px 5px;border-radius:3px;font-size:12px;font-family:Consolas,monospace}}
footer{{margin-top:32px;font-size:11px;color:#8b949e;text-align:center}}
.warn{{color:#ff8800;font-weight:bold}}
</style></head><body>
<h1>&#128065; DorkEye Analyzer Report</h1>
<div class="meta">
  Generated: {now} &nbsp;|&nbsp;
  Target: <code>{target or 'N/A'}</code> &nbsp;|&nbsp;
  DorkEye Analyzer v1.0 (no-AI)
</div>
<h2>Metrics</h2>
<div class="metrics">
  <div class="metric"><div class="num" style="color:#ff4444">{counts['CRITICAL']}</div><div class="lbl">CRITICAL</div></div>
  <div class="metric"><div class="num" style="color:#ff8800">{counts['HIGH']}</div><div class="lbl">HIGH</div></div>
  <div class="metric"><div class="num" style="color:#ffcc00">{counts['MEDIUM']}</div><div class="lbl">MEDIUM</div></div>
  <div class="metric"><div class="num" style="color:#44cc44">{counts['LOW']}</div><div class="lbl">LOW</div></div>
  <div class="metric"><div class="num">{len(results)}</div><div class="lbl">TOTAL</div></div>
  <div class="metric"><div class="num" style="color:#ff4444">{len(all_secrets)}</div><div class="lbl">SECRETS</div></div>
</div>
{'<h2 class="warn">&#9888; Top Findings — CRITICAL &amp; HIGH</h2><div class="card"><table><tr><th>Score</th><th>Label</th><th>URL</th><th>Reasons</th></tr>' + rows_top + '</table></div>' if top else ''}
{'<h2 class="warn">&#128274; Secrets Found (' + str(len(all_secrets)) + ')</h2><div class="card"><table><tr><th>Type</th><th>Description</th><th>Value</th><th>Confidence</th><th>Source</th></tr>' + rows_sec + '</table></div>' if all_secrets else ''}
<h2>All Results ({len(results)})</h2>
<div class="card"><table>
<tr><th>Score</th><th>Label</th><th>URL</th><th>Title</th><th>&#128274;</th></tr>
{rows_all}
</table></div>
<footer>DorkEye Analyzer v1.0 (no-AI, pure regex) &mdash; {now}</footer>
</body></html>"""


def _report_md(results, all_secrets, counts, top, target, now) -> str:
    lines = [
        "# DorkEye Analyzer Report",
        f"\n> {now}  |  Target: `{target or 'N/A'}`  |  DorkEye Analyzer v1.0 (no-AI)\n",
        "---\n",
        "## Metrics\n",
        "| Label | Count |", "|-------|-------|",
        f"| 🔴 CRITICAL | {counts['CRITICAL']} |",
        f"| 🟠 HIGH     | {counts['HIGH']} |",
        f"| 🟡 MEDIUM   | {counts['MEDIUM']} |",
        f"| 🟢 LOW      | {counts['LOW']} |",
        f"| **TOTAL**   | **{len(results)}** |",
        f"| **SECRETS** | **{len(all_secrets)}** |",
    ]
    if top:
        lines += ["\n---\n", "## Top Findings — CRITICAL & HIGH\n",
                  "| Score | Label | URL | Reasons |", "|-------|-------|-----|---------|"]
        for r in top[:30]:
            lines.append(
                f"| {r.get('triage_score',0)} | **{r.get('triage_label','')}** "
                f"| `{r.get('url','')[:80]}` | {', '.join(r.get('triage_reasons',[]))[:60]} |"
            )
    if all_secrets:
        lines += ["\n---\n", f"## Secrets Found ({len(all_secrets)})\n",
                  "| Type | Description | Value | Source |",
                  "|------|-------------|-------|--------|"]
        for s in all_secrets:
            lines.append(
                f"| **{s.get('type','?')}** | {s.get('desc','')[:35]} "
                f"| `{s.get('value','?')}` | {s.get('source','?')[:60]} |"
            )
    lines += [
        "\n---\n", f"## All Results ({len(results)})\n",
        "| Score | Label | URL | Secrets |", "|-------|-------|-----|---------|",
    ]
    for r in results:
        lines.append(
            f"| {r.get('triage_score',0)} | {r.get('triage_label','?')} "
            f"| `{r.get('url','')[:75]}` | {'🔴' if r.get('secrets') else ''} |"
        )
    lines.append(f"\n\n---\n*DorkEye Analyzer v1.0 (no-AI) — {now}*")
    return "\n".join(lines)


def _report_txt(results, all_secrets, counts, top, target, now) -> str:
    lines = [
        "=" * 70,
        "  DORKEYE ANALYZER REPORT",
        f"  {now}  |  Target: {target or 'N/A'}",
        "=" * 70,
        f"\nMETRICS:",
        f"  CRITICAL : {counts['CRITICAL']}",
        f"  HIGH     : {counts['HIGH']}",
        f"  MEDIUM   : {counts['MEDIUM']}",
        f"  LOW      : {counts['LOW']}",
        f"  TOTAL    : {len(results)}",
        f"  SECRETS  : {len(all_secrets)}",
    ]
    if top:
        lines += ["\n" + "─" * 70, "TOP FINDINGS (CRITICAL & HIGH):", "─" * 70]
        for r in top[:30]:
            lines.append(
                f"  [{r.get('triage_score',0):>3}] [{r.get('triage_label','?'):<8}] "
                f"{r.get('url','')[:75]}"
            )
            if r.get("triage_reasons"):
                lines.append(f"       Reasons: {', '.join(r['triage_reasons'])}")
    if all_secrets:
        lines += ["\n" + "─" * 70, f"SECRETS FOUND ({len(all_secrets)}):", "─" * 70]
        for s in all_secrets:
            lines.append(f"  [{s.get('type','?'):<12}] {s.get('value','?'):<30}  {s.get('source','?')[:60]}")
            lines.append(f"    Desc: {s.get('desc','')}  | Context: {s.get('context','')[:80]}")
    lines += ["\n" + "─" * 70, f"ALL RESULTS ({len(results)}):", "─" * 70]
    for r in results:
        sec_flag = " [SECRET]" if r.get("secrets") else ""
        lines.append(
            f"  [{r.get('triage_score',0):>3}] [{r.get('triage_label','?'):<8}]{sec_flag} "
            f"{r.get('url','')[:75]}"
        )
    lines.append(f"\nDorkEye Analyzer v1.0 (no-AI) — {now}")
    return "\n".join(lines)


def _report_json(results, all_secrets, counts, target, now) -> str:
    return json.dumps({
        "meta": {
            "generated_at": now,
            "target": target,
            "engine": "DorkEye Analyzer v1.0 (no-AI, pure regex)",
        },
        "metrics":  {"total": len(results), "by_label": dict(counts), "secrets": len(all_secrets)},
        "secrets":  all_secrets,
        "results":  results,
    }, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    results:    List[dict],
    do_fetch:   bool = False,
    fetch_max:  int  = 20,
    fetch_min_label: str = "HIGH",
    fmt:        str  = "html",
    out:        Optional[str] = None,
    target:     str  = "",
) -> dict:
    """
    Runs the full pipeline: triage → [fetch] → secrets → report.

    Args:
        results:         DorkEye results dict list
        do_fetch:        True = download real pages
        fetch_max:       max pages to download
        fetch_min_label: minimum label for download (HIGH / MEDIUM)
        fmt:             formato report ("html" | "md" | "json" | "txt")
        out:             output path (None = do not save)
        target:          target description for the report

    Returns:
        dict con: triaged, all_secrets, report_path, counts
    """
    _rule(" DorkEye Analyzer v1.0 — no AI required ", style="bold cyan")

    # 1. Triage
    results = triage_results(results)

    # 2. Fetch (opzionale)
    if do_fetch:
        results = fetch_pages(
            results,
            max_pages  = fetch_max,
            min_label  = fetch_min_label,
        )

    # 3. Secrets scan
    results, all_secrets = scan_secrets(results)

    # 4. Report
    _log(f"[Report] Generating report (fmt={fmt})...", style="bold cyan")
    content = build_report(results, all_secrets, target=target, fmt=fmt)

    report_path = None
    if out:
        # Aggiusta estensione
        ext_map = {"html": ".html", "md": ".md", "json": ".json", "txt": ".txt"}
        p = Path(out)
        if p.suffix.lower() not in ext_map.values():
            p = p.with_suffix(ext_map.get(fmt, ".html"))
        try:
            p.write_text(content, encoding="utf-8")
            report_path = str(p)
            _log(f"[Report] Saved: {report_path}", style="bold green")
        except IOError as e:
            _log(f"[Report] Save error: {e}", style="red")

    counts = defaultdict(int)
    for r in results:
        counts[r.get("triage_label", "LOW")] += 1

    # Riepilogo finale
    _rule(" Analysis Complete ", style="bold green")
    _log(
        f"CRITICAL:{counts['CRITICAL']}  HIGH:{counts['HIGH']}  "
        f"MEDIUM:{counts['MEDIUM']}  LOW:{counts['LOW']}  "
        f"TOTAL:{len(results)}  SECRETS:{len(all_secrets)}",
        style="bold white"
    )
    if report_path:
        _log(f"Report: {report_path}", style="bold green")

    return {
        "triaged":     results,
        "all_secrets": all_secrets,
        "report_path": report_path,
        "counts":      dict(counts),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  INTEGRAZIONE CLI dorkeye.py
#  Queste funzioni vengono importate da dorkeye.py
# ══════════════════════════════════════════════════════════════════════════════

def add_local_analyze_args(parser) -> object:
    """
    Adds --analyze-local-* flags to the dorkeye.py CLI parser.
    Does not require --llm.
    """
    g = parser.add_argument_group(
        "Local Analysis (no AI — pure regex, does not require --llm)"
    )
    g.add_argument(
        "--analyze-local",
        action="store_true",
        help="Analisi post-ricerca: triage + secrets scan (regex, no AI)",
    )
    g.add_argument(
        "--analyze-local-fetch",
        action="store_true",
        help="Downloads the real content of HIGH/CRITICAL pages",
    )
    g.add_argument(
        "--analyze-local-fetch-max",
        type=int, default=20,
        help="Max pages to download (default: 20)",
    )
    g.add_argument(
        "--analyze-local-fmt",
        choices=["html", "md", "json", "txt"],
        default="html",
        help="Formato report: html | md | json | txt (default: html)",
    )
    g.add_argument(
        "--analyze-local-out",
        type=str, default=None,
        help="Path output report (default: dorkeye_local_analysis_<ts>.<fmt>)",
    )
    return parser


def run_local_analysis(results: List[dict], args, target: str = "") -> dict:
    """
    Entry point for dorkeye.py — called when --analyze-local is active.
    Does not require llm_plugin.
    """
    fmt = getattr(args, "analyze_local_fmt", "html")
    out = getattr(args, "analyze_local_out", None)
    if not out:
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"dorkeye_local_analysis_{ts}.{fmt}"

    return run_pipeline(
        results   = results,
        do_fetch  = getattr(args, "analyze_local_fetch",     False),
        fetch_max = getattr(args, "analyze_local_fetch_max", 20),
        fmt       = fmt,
        out       = out,
        target    = target,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT CLI STANDALONE
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DorkEye Analyzer v1.0 — Post-search analysis without AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Esempi:

  # Basic analysis (triage + secrets regex)
    python dorkeye_analyze.py Dump/results.json

  # With page download + HTML report
    python dorkeye_analyze.py Dump/results.json --fetch --fmt=html --out=report.html

  # Markdown report with target context
    python dorkeye_analyze.py results.json --target "gov.it admin panels" --fmt=md

  # Download up to 40 pages (more accurate for secrets)
    python dorkeye_analyze.py results.json --fetch --fetch-max=40 --fmt=html

  # Output JSON machine-readable
    python dorkeye_analyze.py results.json --fmt=json --out=analisi.json
""",
    )

    parser.add_argument("results_file",    help="DorkEye JSON results file")
    parser.add_argument("--target",        default="", help="Descrizione target (opzionale)")
    parser.add_argument("--fetch",         action="store_true", help="Download HIGH/CRITICAL pages")
    parser.add_argument("--fetch-max",     type=int,  default=20,   help="Max pages to download (default: 20)")
    parser.add_argument("--fetch-label",   default="HIGH",          help="Minimum label for fetch (default: HIGH)")
    parser.add_argument("--fmt",           choices=["html","md","json","txt"], default="html", help="Formato report")
    parser.add_argument("--out",           default=None, help="Path output report")
    parser.add_argument("--no-report",     action="store_true", help="Do not generate a report file, output to console only")

    args = parser.parse_args()

    # Load results
    p = Path(args.results_file)
    if not p.exists():
        print(f"[!] File not found: {p}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[!] Errore lettura file: {e}", file=sys.stderr)
        sys.exit(1)

    if isinstance(raw, list):
        results = raw
    elif isinstance(raw, dict):
        results = raw.get("results", [])
    else:
        results = []

    if not results:
        print(f"[!] No results found in '{p}'.", file=sys.stderr)
        print("    Save DorkEye results with: -o results.json", file=sys.stderr)
        sys.exit(1)

    _log(f"[*] Loaded {len(results)} results from '{p.name}'", style="bold cyan")
    if args.target:
        _log(f"[*] Target: {args.target}", style="cyan")

    # Determina path output
    out = None
    if not args.no_report:
        out = args.out
        if not out:
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = f"dorkeye_analysis_{ts}.{args.fmt}"

    run_pipeline(
        results   = results,
        do_fetch  = args.fetch,
        fetch_max = args.fetch_max,
        fetch_min_label = args.fetch_label,
        fmt       = args.fmt,
        out       = out,
        target    = args.target,
    )


if __name__ == "__main__":
    main()
