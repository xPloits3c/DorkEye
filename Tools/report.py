#!/usr/bin/env python3
"""
DorkEye Report Engine
Single home for DorkEye's HTML report rendering + the shared in-browser export
(TXT/JSON/CSV/SQLite). Extracted from dorkeye.py so the main module stays light
and every report (dork results now; OSINT, DBScan, crawl next) renders through
one engine with one look.

Lives in: DorkEye/Tools/report.py
Author: xPloits3c | DorkEye Project
"""
from __future__ import annotations

import os
import time
import json
import html
import base64
import sqlite3
import tempfile
from datetime import datetime


def _format_size(size):

        """Format byte count to human-readable string."""
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



def _safe_href(url) -> str:
    """Escaped href for http/https/ftp(s) URLs; anything else (javascript:,
    data:, ...) becomes '#' so a crafted result can't run script on click."""
    from urllib.parse import urlparse
    url = "" if url is None else str(url).strip()
    try:
        scheme = urlparse(url).scheme.lower()
    except ValueError:
        return "#"
    if scheme in ("http", "https", "ftp", "ftps"):
        return html.escape(url, quote=True)
    return "#"


def _json_scalar(v):
    """Flatten list/dict cells to a compact string for the SQLite snapshot."""
    if isinstance(v, (list, dict)):
        import json as _j
        return _j.dumps(v, ensure_ascii=False)
    return v


# Intensity levels → chains. 1 basic · 2 medium (IP enrichment) · 3 full (adds
# wayback + live http probe + email/phone harvesting).
_OSINT_LEVELS = {"1": "recon-basic", "2": "recon-ip", "3": "recon-passive"}


def build_results_sqlite_b64(results, max_bytes: int = 8 * 1024 * 1024) -> str:
    """
    Build an in-memory SQLite snapshot of DorkEye search results and return it
    base64-encoded, so the HTML report can offer a one-click .sqlite export that
    runs entirely in the browser. Returns "" on any error or if it exceeds the
    size cap (the SQLITE button then shows a friendly message).
    """
    try:
        import sqlite3 as _sq, base64 as _b64, tempfile as _tf
        fields = [
            "url", "title", "snippet", "dork", "timestamp", "extension",
            "category", "file_size", "content_type", "accessible", "status_code",
            "sqli_vulnerable", "sqli_confidence", "waf_detected",
            "xss_vulnerable", "xss_types", "xss_confidence",
        ]
        tmp = os.path.join(_tf.mkdtemp(), "results.sqlite")
        con = _sq.connect(tmp)
        con.execute("CREATE TABLE results (" +
                    ",".join(f'"{c}" TEXT' for c in fields) + ")")
        con.executemany(
            "INSERT INTO results VALUES (" + ",".join("?" * len(fields)) + ")",
            [[_json_scalar(r.get(c)) for c in fields] for r in (results or [])],
        )
        con.commit()
        con.close()
        size = os.path.getsize(tmp)
        if size > max_bytes:
            return ""
        with open(tmp, "rb") as fh:
            return _b64.b64encode(fh.read()).decode("ascii")
    except Exception:
        return ""


def build_dork_html(results, stats, start_time, report_base="report"):
        """Build and write the full interactive dark-theme HTML report."""
        sqli_count = stats.get("sqli_vulnerable", 0)
        sqli_safe  = sum(
            1 for r in results
            if "sqli_test" in r and r["sqli_test"].get("tested") and not r["sqli_test"].get("vulnerable")
        )
        sqli_total = sqli_count + sqli_safe
        xss_count  = stats.get("xss_vulnerable", 0)
        xss_safe   = sum(
            1 for r in results
            if "xss_test" in r and r["xss_test"].get("tested") and not r["xss_test"].get("vulnerable")
        )
        xss_total  = xss_count + xss_safe
        waf_count  = stats.get("waf_detected", 0)
        cnt        = {"all": len(results), "doc": 0, "sqli": sqli_total, "xss": xss_total, "scripts": 0, "page": 0}
        for r in results:
            cat = r.get("category", "unknown")
            if cat in ("documents", "archives", "backups"):    cnt["doc"]     += 1
            elif cat in ("scripts", "configs", "credentials"): cnt["scripts"] += 1
            elif cat == "webpage":                             cnt["page"]    += 1

        import json as _json
        import html as _html_mod

        export_rows = []
        for r in results:
            sqli_t = r.get("sqli_test", {})
            if sqli_t.get("tested"):
                conf   = sqli_t.get("overall_confidence", "")
                sqli_s = ("critical" if conf == "critical" else "vuln") if sqli_t.get("vulnerable") else "safe"
            else:
                sqli_s = "untested"
            xss_t  = r.get("xss_test", {})
            if xss_t.get("tested"):
                xss_s = "vuln" if xss_t.get("vulnerable") else "safe"
            else:
                xss_s = "untested"
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
                "xss":       xss_s,
                "xss_types": ",".join(xss_t.get("xss_types_found", [])),
                "xss_conf":  xss_t.get("overall_confidence", ""),
            })

        file_rows = []
        for r in results:
            cat = r.get("category", "webpage")
            if cat == "webpage":
                continue
            file_rows.append({
                "url":         r.get("url", ""),
                "title":       r.get("title", ""),
                "category":    cat,
                "ext":         r.get("extension", ""),
                "size":        r.get("file_size"),
                "size_str":    _format_size(r.get("file_size")),
                "accessible":  r.get("accessible", False),
                "status_code": r.get("status_code"),
                "timestamp":   r.get("timestamp", ""),
            })

        export_data_js = _json.dumps(export_rows, ensure_ascii=False).replace("</", "<\\/")
        file_data_js   = _json.dumps(file_rows,   ensure_ascii=False).replace("</", "<\\/")
        # Embed a SQLite snapshot of the results so the report can also export
        # the data as a .sqlite file, entirely in the browser (same idea as the
        # OSINT report). Capped so a huge run doesn't bloat the HTML.
        sqlite_b64     = build_results_sqlite_b64(results)

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
        .header { background: rgba(0,10,0,0.85); border: 1px solid #00ff41; border-left: 4px solid #00ff41;
            padding: 22px 28px; margin-bottom: 24px; box-shadow: 0 0 24px rgba(0,255,65,0.15); }
        .header h1 { font-size: 22px; color: #00ff41; text-shadow: 0 0 10px #00ff41; letter-spacing: 2px; }
        .header .subtitle { margin-top: 6px; font-size: 12px; color: #009922; letter-spacing: 1px; }
        .header .blink { animation: blink 1.1s step-end infinite; }
        @keyframes blink { 50% { opacity: 0; } }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 24px; }
        .stat-card { background: rgba(0,10,0,0.82); border: 1px solid #00aa2a; padding: 16px 18px; }
        .stat-card h3 { font-size: 11px; color: #009922; letter-spacing: 1px; text-transform: uppercase; }
        .stat-card p { font-size: 26px; font-weight: bold; color: #00ff41; margin-top: 8px; text-shadow: 0 0 8px rgba(0,255,65,0.5); }
        .sqli-alert { background: rgba(40,0,0,0.88); border: 1px solid #ff2222; border-left: 4px solid #ff2222;
            padding: 14px 20px; margin-bottom: 20px; color: #ff4444; }
        .sqli-alert h2 { font-size: 15px; letter-spacing: 2px; margin-bottom: 6px; }
        .sqli-alert p  { font-size: 13px; color: #ff6666; }
        .waf-alert { background: rgba(30,20,0,0.88); border: 1px solid #ffaa00; border-left: 4px solid #ffaa00;
            padding: 12px 20px; margin-bottom: 14px; color: #ffcc44; font-size: 13px; }
        .toolbar { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
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
        .right-btns { display: flex; gap: 6px; flex-shrink: 0; align-items: flex-start; }
        .srch-wrap, .export-wrap, .files-wrap { position: relative; flex-shrink: 0; }
        .rbt { background: rgba(0,10,18,0.85); border: 1px solid #0077bb; color: #00aaff;
            padding: 5px 13px; font-family: 'Courier New', monospace; font-size: 11px; cursor: pointer;
            letter-spacing: 2px; text-transform: uppercase; display: inline-flex; align-items: center;
            gap: 5px; transition: all .15s; white-space: nowrap; }
        .rbt:hover, .rbt.open { background: rgba(0,100,180,0.2); border-color: #00aaff; color: #fff; }
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
        .table-wrap { background: rgba(0,8,0,0.82); border: 1px solid #00aa2a; overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 290px); min-height: 200px; }
        thead th { background: rgba(0,10,0,0.97); color: #00ff41; padding: 11px 10px; text-align: left;
            border-bottom: 1px solid #00aa2a; font-size: 11px; letter-spacing: 2px;
            text-transform: uppercase; white-space: nowrap; position: sticky; top: 0; z-index: 5; }
        table { width: 100%; border-collapse: collapse; table-layout: auto; }
        col.c-num   { width: 36px; }
        col.c-url   { min-width: 180px; }
        col.c-title { min-width: 120px; width: 14%; }
        col.c-cat   { min-width: 90px;  width: 9%; }
        col.c-sqli  { min-width: 110px; width: 10%; }
        col.c-xss   { min-width: 110px; width: 10%; }
        col.c-waf   { min-width: 70px;  width: 7%; }
        col.c-size  { min-width: 54px;  width: 6%; }
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
        .xss-vuln      { color: #ffaa00; font-weight: bold; }
        .xss-safe      { color: #00ff41; }
        .xss-untested  { color: #444; }
        .waf-label     { font-size: 10px; color: #ffaa00; border: 1px solid #ffaa00; padding: 1px 5px; letter-spacing: 1px; white-space: nowrap; }
        .url-cell { display: flex; align-items: center; gap: 6px; overflow: hidden; }
        .url-cell a { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
        .dl-btn { flex-shrink: 0; background: transparent; border: none; color: #005588;
            font-size: 15px; cursor: pointer; text-decoration: none; line-height: 1;
            padding: 0; transition: color .12s; }
        .dl-btn:hover { color: #00aaff; }
        .info-btn { flex-shrink: 0; background: transparent; border: none; color: #004455;
            font-size: 13px; cursor: pointer; line-height: 1; padding: 0 1px;
            transition: color .12s; font-family: 'Courier New', monospace; }
        .info-btn:hover { color: #00ccff; }
        .info-overlay { display: none; position: fixed; inset: 0; z-index: 8900;
            background: rgba(0,0,0,0.72); backdrop-filter: blur(2px); }
        .info-overlay.open { display: block; animation: fadeIn .15s ease; }
        .info-popup { display: none; position: fixed; z-index: 9000;
            top: 50%; left: 50%; transform: translate(-50%,-50%);
            background: rgba(0,4,12,0.98); border: 1px solid #007acc;
            border-top: 3px solid #00aaff;
            box-shadow: 0 0 60px rgba(0,120,200,0.45), 0 0 120px rgba(0,80,160,0.25);
            width: min(560px, 92vw); max-height: 80vh; overflow-y: auto;
            font-size: 11px; padding: 18px 20px; }
        .info-popup.open { display: block; animation: fadeIn .18s ease; }
        .info-popup-title { font-size: 10px; color: #005588; letter-spacing: 2px;
            text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid rgba(0,100,180,0.2);
            padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
        .info-close { background: transparent; border: none; color: #004466; cursor: pointer;
            font-size: 14px; font-family: 'Courier New', monospace; padding: 0 3px; transition: color .12s; }
        .info-close:hover { color: #00aaff; }
        .info-row { display: flex; gap: 8px; margin-bottom: 5px; align-items: flex-start; }
        .info-lbl { color: #005588; min-width: 90px; flex-shrink: 0; letter-spacing: 1px; }
        .info-val { color: #00aaff; word-break: break-all; }
        .footer { margin-top: 28px; padding: 14px 0; border-top: 1px solid #002200;
            text-align: center; font-size: 11px; color: #004400; letter-spacing: 2px; }
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
        <p>Review the results marked VULNERABLE below.</p>
    </div>
""")
        if xss_count > 0:
            parts.append(f"""    <div class="xss-alert" style="background:rgba(40,20,0,0.88);border:1px solid #ffaa00;border-left:4px solid #ffaa00;padding:14px 20px;margin-bottom:20px;color:#ffcc44;">
        <h2 style="font-size:15px;letter-spacing:2px;margin-bottom:6px;">&#9888; XSS ALERT &#9888;</h2>
        <p style="font-size:13px;color:#ffdd88;"><strong>{xss_count}</strong> potential Cross-Site Scripting vulnerabilities detected!</p>
    </div>
""")
        if waf_count > 0:
            parts.append(f"""    <div class="waf-alert">
        &#9888; <strong>{waf_count}</strong> WAF-protected target(s) detected.
    </div>
""")
        parts.append(f"""    <div class="stats">
        <div class="stat-card"><h3>&#9632; TOTAL RESULTS</h3><p>{len(results)}</p></div>
        <div class="stat-card"><h3>&#9632; DUPLICATES FILTERED</h3><p>{stats.get("duplicates", 0)}</p></div>
        <div class="stat-card"><h3>&#9632; SQLI VULNERABILITIES</h3><p style="color:#ff3333;">{sqli_count}</p></div>
        <div class="stat-card"><h3>&#9632; XSS VULNERABILITIES</h3><p style="color:#ffaa00;">{xss_count}</p></div>
        <div class="stat-card"><h3>&#9632; WAF DETECTED</h3><p style="color:#ffaa00;">{waf_count}</p></div>
        <div class="stat-card"><h3>&#9632; EXECUTION TIME</h3><p>{round(time.time() - start_time, 2)}s</p></div>
    </div>

    <div class="toolbar">
      <div class="filter-bar">
        <span class="filter-label">[ FILTER ]</span>
        <button class="filter-btn active" data-group="all" onclick="applyFilter(this)">ALL <span class="badge" id="badge-all">{cnt["all"]}</span></button>
        <div class="filter-group" id="fg-doc">
            <button class="filter-btn has-sub" data-group="doc" onclick="applyFilter(this)">DOC <span class="badge" id="badge-doc">{cnt["doc"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-doc">
                <button class="sub-btn active" data-sub="doc-all"  onclick="applySubFilter(this,'doc')">ALL      <span class="sub-badge" id="sbadge-doc-all">{cnt["doc"]}</span></button>
                <button class="sub-btn"        data-sub="doc-pdf"  onclick="applySubFilter(this,'doc')">PDF      <span class="sub-badge" id="sbadge-doc-pdf">-</span></button>
                <button class="sub-btn"        data-sub="doc-docx" onclick="applySubFilter(this,'doc')">DOCX     <span class="sub-badge" id="sbadge-doc-docx">-</span></button>
                <button class="sub-btn"        data-sub="doc-xlsx" onclick="applySubFilter(this,'doc')">XLSX     <span class="sub-badge" id="sbadge-doc-xlsx">-</span></button>
                <button class="sub-btn"        data-sub="doc-ppt"  onclick="applySubFilter(this,'doc')">PPT      <span class="sub-badge" id="sbadge-doc-ppt">-</span></button>
                <button class="sub-btn"        data-sub="doc-arc"  onclick="applySubFilter(this,'doc')">ARCHIVES <span class="sub-badge" id="sbadge-doc-arc">-</span></button>
            </div>
        </div>
        <div class="filter-group" id="fg-sqli">
            <button class="filter-btn has-sub" data-group="sqli" onclick="applyFilter(this)">SQLi <span class="badge" id="badge-sqli">{cnt["sqli"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-sqli">
                <button class="sub-btn active" data-sub="sqli-all"      onclick="applySubFilter(this,'sqli')">SQLi ALL      <span class="sub-badge" id="sbadge-sqli-all">{sqli_total}</span></button>
                <button class="sub-btn"        data-sub="sqli-critical" onclick="applySubFilter(this,'sqli')">SQLi CRITICAL <span class="sub-badge sqli-critical" id="sbadge-sqli-critical">-</span></button>
                <button class="sub-btn"        data-sub="sqli-vuln"     onclick="applySubFilter(this,'sqli')">SQLi VULN     <span class="sub-badge sqli-vuln" id="sbadge-sqli-vuln">{sqli_count}</span></button>
                <button class="sub-btn"        data-sub="sqli-safe"     onclick="applySubFilter(this,'sqli')">SQLi SAFE     <span class="sub-badge" id="sbadge-sqli-safe">{sqli_safe}</span></button>
            </div>
        </div>
        <div class="filter-group" id="fg-xss">
            <button class="filter-btn has-sub" data-group="xss" onclick="applyFilter(this)">XSS <span class="badge" id="badge-xss">{cnt["xss"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-xss">
                <button class="sub-btn active" data-sub="xss-all"  onclick="applySubFilter(this,'xss')">ALL  <span class="sub-badge" id="sbadge-xss-all">{xss_total}</span></button>
                <button class="sub-btn"        data-sub="xss-vuln" onclick="applySubFilter(this,'xss')">VULN <span class="sub-badge xss-vuln" id="sbadge-xss-vuln">{xss_count}</span></button>
                <button class="sub-btn"        data-sub="xss-safe" onclick="applySubFilter(this,'xss')">SAFE <span class="sub-badge" id="sbadge-xss-safe">{xss_safe}</span></button>
            </div>
        </div>
        <div class="filter-group" id="fg-scripts">
            <button class="filter-btn has-sub" data-group="scripts" onclick="applyFilter(this)">SCRIPTS <span class="badge" id="badge-scripts">{cnt["scripts"]}</span><span class="arrow">&#9660;</span></button>
            <div class="sub-menu" id="sub-scripts">
                <button class="sub-btn active" data-sub="scripts-all"    onclick="applySubFilter(this,'scripts')">ALL     <span class="sub-badge" id="sbadge-scripts-all">{cnt["scripts"]}</span></button>
                <button class="sub-btn"        data-sub="scripts-php"    onclick="applySubFilter(this,'scripts')">PHP     <span class="sub-badge" id="sbadge-scripts-php">-</span></button>
                <button class="sub-btn"        data-sub="scripts-asp"    onclick="applySubFilter(this,'scripts')">ASP     <span class="sub-badge" id="sbadge-scripts-asp">-</span></button>
                <button class="sub-btn"        data-sub="scripts-sh"     onclick="applySubFilter(this,'scripts')">SH/BAT  <span class="sub-badge" id="sbadge-scripts-sh">-</span></button>
                <button class="sub-btn"        data-sub="scripts-config" onclick="applySubFilter(this,'scripts')">CONFIGS <span class="sub-badge" id="sbadge-scripts-config">-</span></button>
                <button class="sub-btn"        data-sub="scripts-creds"  onclick="applySubFilter(this,'scripts')">CREDS   <span class="sub-badge" id="sbadge-scripts-creds">-</span></button>
            </div>
        </div>
        <button class="filter-btn" data-group="page" onclick="applyFilter(this)">PAGE <span class="badge" id="badge-page">{cnt["page"]}</span></button>
      </div>
      <div class="right-btns">
        <div class="srch-wrap" id="srchWrap">
          <button class="rbt" id="srchToggle" onclick="toggleSearch()">&#128269; SEARCH</button>
          <div class="rpanel srch-panel" id="srchPanel">
            <button class="panel-close" onclick="document.getElementById('srchPanel').classList.remove('open');document.getElementById('srchToggle').classList.remove('open')" title="Close">&#10005;</button>
            <div class="srch-inner">
              <div class="srch-title">&#9632; Search</div>
              <div class="srch-input-wrap">
                <input class="srch-input" id="srchInput" type="text" placeholder="Type to filter results..." oninput="doSearch()" autocomplete="off" spellcheck="false">
                <button class="srch-clear" onclick="clearSearch()">CLEAR</button>
              </div>
              <div class="srch-meta">Matching: <span id="srchCount">-</span> of {len(results)} results</div>
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
        <div class="export-wrap" id="exportWrap">
          <button class="rbt" id="exportToggle" onclick="toggleExportPanel()">&#11015; LINKS</button>
          <div class="rpanel" id="exportPanel">
            <button class="panel-close" onclick="document.getElementById('exportPanel').classList.remove('open');document.getElementById('exportToggle').classList.remove('open')" title="Close">&#10005;</button>
            <div class="ep-section">
              <div class="ep-title">&#9632; Export Links - All</div>
              <div class="ep-row">
                <span class="ep-label">All ({len(results)})</span>
                <button class="exp-btn txt" onclick="doExport('txt','all')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','all')">JSON</button>
                <button class="exp-btn csv" onclick="doExport('csv','all')">CSV</button>
                <button class="exp-btn" onclick="exportSqlite()">SQLITE</button>
              </div>
            </div>
            <div class="ep-section">
              <div class="ep-title">&#9632; Export Links - SQLi</div>
              <div class="ep-row">
                <span class="ep-label warn">All tested <span id="epCntSqliAll"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','sqli-all')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','sqli-all')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','sqli-all')">CSV</button>
              </div>
              <div class="ep-row">
                <span class="ep-label danger">VULN <span id="epCntSqliVuln"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','sqli-vuln')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','sqli-vuln')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','sqli-vuln')">CSV</button>
              </div>
              <div class="ep-row">
                <span class="ep-label safe-lbl">SAFE <span id="epCntSqliSafe"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','sqli-safe')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','sqli-safe')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','sqli-safe')">CSV</button>
              </div>
            </div>
            <div class="ep-section">
              <div class="ep-title">&#9632; Export Links - XSS</div>
              <div class="ep-row">
                <span class="ep-label warn">All tested <span id="epCntXssAll"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','xss-all')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','xss-all')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','xss-all')">CSV</button>
              </div>
              <div class="ep-row">
                <span class="ep-label" style="color:#ffaa00;">VULN <span id="epCntXssVuln"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','xss-vuln')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','xss-vuln')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','xss-vuln')">CSV</button>
              </div>
              <div class="ep-row">
                <span class="ep-label safe-lbl">SAFE <span id="epCntXssSafe"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','xss-safe')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','xss-safe')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','xss-safe')">CSV</button>
              </div>
            </div>
            <div class="ep-section">
              <div class="ep-title">&#9632; Current View</div>
              <div class="ep-row">
                <span class="ep-label view-lbl">Visible <span id="epCntView"></span></span>
                <button class="exp-btn txt"  onclick="doExport('txt','view')">TXT</button>
                <button class="exp-btn json" onclick="doExport('json','view')">JSON</button>
                <button class="exp-btn csv"  onclick="doExport('csv','view')">CSV</button>
              </div>
            </div>
          </div>
        </div>
        <div class="files-wrap" id="filesWrap">
          <button class="rbt" id="filesToggle" onclick="toggleFilesPanel()">&#128196; FILES</button>
          <div class="rpanel files-panel" id="filesPanel">
            <div class="files-hdr" style="position:relative">
              <div class="ep-title" style="margin-bottom:0">&#9632; Download Files</div>
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

        if file_rows:
            for idx_f, fr in enumerate(file_rows):
                size_str      = fr.get("size_str", "N/A")
                is_accessible = fr.get("accessible", False)
                opacity_style = "" if is_accessible else ' style="opacity:.45"'
                status_icon   = "✓" if is_accessible else "✗"
                status_color  = "#00aa44" if is_accessible else "#663333"
                status_code   = _html_mod.escape(str(fr.get("status_code", "?")), quote=True)
                url_raw       = str(fr.get("url", "") or "")
                url_esc       = _html_mod.escape(url_raw, quote=True)
                url_href      = _safe_href(url_raw)
                url_short     = _html_mod.escape(url_raw[:62] + ("..." if len(url_raw) > 62 else ""), quote=False)
                cat_str       = _html_mod.escape(str(fr.get("category", "") or "").upper())
                ext_str       = _html_mod.escape(str(fr.get("ext", "") or ""))
                parts.append(f"""              <div class="file-row"{opacity_style}>
                <input class="file-chk" type="checkbox" data-fidx="{idx_f}" onchange="updateSelCount()">
                <span style="font-size:9px;color:{status_color};flex-shrink:0" title="HTTP {status_code}">{status_icon}</span>
                <div class="file-info">
                  <a class="file-url" href="{url_href}" target="_blank" rel="noopener noreferrer" title="{url_esc}">{url_short}</a>
                  <div class="file-cat">{cat_str} &nbsp;{ext_str}</div>
                </div>
                <span class="file-size">{size_str}</span>
                <a class="file-dl" href="{url_href}" download>&#8681;</a>
              </div>
""")
        else:
            parts.append('              <div class="files-empty">No file results in this report.</div>\n')

        parts.append(f"""            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="active-sub-info" id="sub-info"></div>
    <div class="table-wrap">
    <table>
        <colgroup>
          <col class="c-num"><col class="c-url"><col class="c-title">
          <col class="c-cat"><col class="c-sqli"><col class="c-xss"><col class="c-waf"><col class="c-size">
        </colgroup>
        <thead><tr>
          <th>#</th><th>URL</th><th>Title</th>
          <th>Category</th><th>SQLi</th><th>XSS</th><th>WAF</th><th>Size</th>
        </tr></thead>
        <tbody id="results-tbody">
""")

        for idx, result in enumerate(results, 1):
            size        = _format_size(result.get('file_size'))
            category    = _html_mod.escape(str(result.get('category', 'unknown') or 'unknown'), quote=True)
            ext         = _html_mod.escape(str(result.get('extension', '') or '').lower(), quote=True)
            url         = str(result['url'])
            url_display = _html_mod.escape(url[:70] + ('...' if len(url) > 70 else ''), quote=False)
            title_disp  = (result.get('title', 'N/A') or 'N/A')[:40]
            dork_val    = _html_mod.escape(result.get('dork', '') or '', quote=True)
            url_esc_td  = _html_mod.escape(url, quote=True)
            url_href_td = _safe_href(url)
            title_esc   = _html_mod.escape(title_disp, quote=True)

            sqli_status = "N/A"
            sqli_class  = "sqli-untested"
            sqli_data   = "untested"
            sqli_conf   = ""
            waf_label   = ""
            xss_status  = "N/A"
            xss_class   = "xss-untested"
            xss_data    = "untested"

            _sqli_t      = result.get("sqli_test", {})
            _vuln_str    = ""
            _payload_str = ""
            if _sqli_t.get("tested"):
                _vuln_str = "VULNERABLE" if _sqli_t.get("vulnerable") else "SAFE"
                _conf_str = _sqli_t.get("overall_confidence", "")
                if _conf_str:
                    _vuln_str += f" ({_conf_str})"
                _details = []
                for _tt in _sqli_t.get("tests", []):
                    if _tt.get("vulnerable"):
                        _m   = _tt.get("method", "")
                        _evs = " | ".join(_tt.get("evidence", [])[:2])
                        _param = _tt.get("parameter", "")
                        _details.append(f"{_m}" + (f"[{_param}]" if _param else "") + (f": {_evs[:80]}" if _evs else ""))
                _payload_str = " ↳ ".join(_details[:3])
            _waf_info = _sqli_t.get("waf_detected", "") or ""

            _xss_t       = result.get("xss_test", {})
            _xss_str     = ""
            _xss_det_str = ""
            if _xss_t.get("tested"):
                _xss_str = "VULNERABLE" if _xss_t.get("vulnerable") else "SAFE"
                _xconf   = _xss_t.get("overall_confidence", "")
                _xtypes  = ",".join(_xss_t.get("xss_types_found", []))
                if _xconf:
                    _xss_str += f" ({_xconf})"
                if _xtypes:
                    _xss_str += f" [{_xtypes}]"
                _xdet = []
                for _xt in _xss_t.get("tests", []):
                    if _xt.get("vulnerable"):
                        _xdet.append(_xt.get("type", "") + ": " + " | ".join(_xt.get("evidence", [])[:1]))
                _xss_det_str = " ↳ ".join(_xdet[:3])

            import json as _json_local
            _info_obj = _json_local.dumps({
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
                "xss":       _xss_str,
                "xss_det":   _xss_det_str,
                "size":      size,
            }, ensure_ascii=False).replace("&", "&amp;").replace("'", "&#39;").replace("</", "<\\/")

            if "sqli_test" in result and result["sqli_test"].get("tested", False):
                conf      = _html_mod.escape(str(result["sqli_test"].get("overall_confidence", "none")), quote=True)
                sqli_conf = conf
                if result["sqli_test"].get("vulnerable", False):
                    # "critical" is SQLiConfidence.CRITICAL.value; inlined so the
                    # report engine stays decoupled from the sqli module.
                    if conf == "critical":
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

            if "xss_test" in result and result["xss_test"].get("tested", False):
                if result["xss_test"].get("vulnerable", False):
                    _xtypes_short = _html_mod.escape(",".join(map(str, result["xss_test"].get("xss_types_found", [])))[:30])
                    xss_status = f"VULN [{_xtypes_short}]"
                    xss_class  = "xss-vuln"
                    xss_data   = "vuln"
                else:
                    xss_status = "SAFE"
                    xss_class  = "xss-safe"
                    xss_data   = "safe"

            parts.append(f"""            <tr data-category="{category}" data-ext="{ext}" data-sqli="{sqli_data}" data-conf="{sqli_conf}" data-xss="{xss_data}"
                data-idx="{idx-1}" data-url="{url_esc_td}" data-title="{title_esc}" data-dork="{dork_val}">
                <td style="color:#444">{idx}</td>
                <td><div class="url-cell"><a href="{url_href_td}" target="_blank" rel="noopener noreferrer" title="{url_esc_td}">{url_display}</a><a class="dl-btn" href="{url_href_td}" download>&#8681;</a><button class="info-btn" onclick="showInfo(this)" data-info='{_info_obj}' title="Details">&#9432;</button></div></td>
                <td title="{title_esc}">{_html_mod.escape(title_disp)}</td>
                <td><span class="category category-{category}">{category}</span></td>
                <td class="{sqli_class}">{sqli_status}</td>
                <td class="{xss_class}">{xss_status}</td>
                <td>{waf_label}</td>
                <td>{size}</td>
            </tr>
""")

        parts.append(f"""        </tbody>
    </table>
    </div>
    <div class="footer">DorkEye v5.1 &nbsp;|&nbsp; xploits3c &nbsp;|&nbsp; For authorized security research only</div>
</div>

<div id="toast"></div>
<div class="info-overlay" id="infoOverlay" onclick="closeInfo()"></div>
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
const SQLITE_B64  = "{sqlite_b64}";
</script>

<script>
(function(){{
    const c=document.getElementById('matrix-canvas'),ctx=c.getContext('2d');
    const CH='アイウエオカキクケコ0123456789ABCDEF';
    const FS=14;let cols,drops;
    function resize(){{c.width=window.innerWidth;c.height=window.innerHeight;cols=Math.floor(c.width/FS);drops=Array.from({{length:cols}},()=>Math.random()*-100);}}
    function draw(){{ctx.fillStyle='rgba(0,0,0,0.05)';ctx.fillRect(0,0,c.width,c.height);for(let i=0;i<cols;i++){{const ch=CH[Math.floor(Math.random()*CH.length)];ctx.fillStyle=Math.random()>.95?'#fff':'#00ff41';ctx.font=FS+'px monospace';ctx.fillText(ch,i*FS,drops[i]*FS);if(drops[i]*FS>c.height&&Math.random()>.975)drops[i]=0;drops[i]+=.5+Math.random()*.5;}}}}
    resize();window.addEventListener('resize',resize);setInterval(draw,45);
}})();

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
  "xss-all":(r)=>["vuln","safe"].includes(r.dataset.xss),
  "xss-vuln":(r)=>r.dataset.xss==="vuln",
  "xss-safe":(r)=>r.dataset.xss==="safe",
  "scripts-all":()=>true,
  "scripts-php":(r)=>r.dataset.ext===".php",
  "scripts-asp":(r)=>[".asp",".aspx"].includes(r.dataset.ext),
  "scripts-sh":(r)=>[".sh",".bat",".ps1"].includes(r.dataset.ext),
  "scripts-config":(r)=>[".conf",".config",".ini",".yaml",".yml",".json",".xml"].includes(r.dataset.ext),
  "scripts-creds":(r)=>[".env",".git",".svn",".htpasswd"].includes(r.dataset.ext)
}};
let activeGroup="all",activeSub=null;
function closeAllSubMenus(){{document.querySelectorAll('.sub-menu.open').forEach(m=>m.classList.remove('open'));}}
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
      else if(activeGroup==='xss'){{hide=!pred(row);}}
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
  const xssR=rows.filter(r=>["vuln","safe"].includes(r.dataset.xss));
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
  s('sbadge-xss-all',xssR.length);
  s('sbadge-xss-vuln',xssR.filter(r=>r.dataset.xss==='vuln').length);
  s('sbadge-xss-safe',xssR.filter(r=>r.dataset.xss==='safe').length);
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
  const el=document.getElementById('srchCount');if(el)el.textContent=q?match:'-';
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
  const el=document.getElementById('srchCount');if(el)el.textContent='-';
  updateInfoBar();updateExportCounts();
}}
function toggleExportPanel(){{
  const p=document.getElementById('exportPanel'),t=document.getElementById('exportToggle');
  const open=p.classList.contains('open');closeAllPanels();
  if(!open){{p.classList.add('open');t.classList.add('open');updateExportCounts();}}
}}
function updateExportCounts(){{
  const sqliAll=EXPORT_DATA.filter(r=>["vuln","safe","critical"].includes(r.sqli));
  const sqliVuln=EXPORT_DATA.filter(r=>["vuln","critical"].includes(r.sqli));
  const sqliSafe=EXPORT_DATA.filter(r=>r.sqli==="safe");
  const xssAll=EXPORT_DATA.filter(r=>["vuln","safe"].includes(r.xss));
  const xssVuln=EXPORT_DATA.filter(r=>r.xss==="vuln");
  const xssSafe=EXPORT_DATA.filter(r=>r.xss==="safe");
  const viewIdxs=new Set(Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden):not(.srch-hidden)')).map(r=>parseInt(r.dataset.idx)));
  const s=(id,n)=>{{const el=document.getElementById(id);if(el)el.textContent='('+n+')';}}; 
  s('epCntSqliAll',sqliAll.length);s('epCntSqliVuln',sqliVuln.length);s('epCntSqliSafe',sqliSafe.length);
  s('epCntXssAll',xssAll.length);s('epCntXssVuln',xssVuln.length);s('epCntXssSafe',xssSafe.length);
  s('epCntView',EXPORT_DATA.filter((_,i)=>viewIdxs.has(i)).length);
}}
function _getRows(scope){{
  if(scope==='all')return EXPORT_DATA;
  if(scope==='sqli-all')return EXPORT_DATA.filter(r=>["vuln","safe","critical"].includes(r.sqli));
  if(scope==='sqli-vuln')return EXPORT_DATA.filter(r=>["vuln","critical"].includes(r.sqli));
  if(scope==='sqli-safe')return EXPORT_DATA.filter(r=>r.sqli==="safe");
  if(scope==='xss-all')return EXPORT_DATA.filter(r=>["vuln","safe"].includes(r.xss));
  if(scope==='xss-vuln')return EXPORT_DATA.filter(r=>r.xss==="vuln");
  if(scope==='xss-safe')return EXPORT_DATA.filter(r=>r.xss==="safe");
  if(scope==='view'){{const vis=new Set(Array.from(document.querySelectorAll('#results-tbody tr:not(.hidden):not(.srch-hidden)')).map(r=>parseInt(r.dataset.idx)));return EXPORT_DATA.filter((_,i)=>vis.has(i));}}
  return EXPORT_DATA;
}}
function _scopeLabel(scope){{return{{'all':'all','sqli-all':'sqli_tested','sqli-vuln':'sqli_vuln','sqli-safe':'sqli_safe','xss-all':'xss_tested','xss-vuln':'xss_vuln','xss-safe':'xss_safe','view':'view'}}[scope]||scope;}}
function _download(content,filename,mime){{const blob=new Blob([content],{{type:mime}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;document.body.appendChild(a);a.click();setTimeout(()=>{{URL.revokeObjectURL(a.href);document.body.removeChild(a);}},100);}}
function exportSqlite(){{
  if(!SQLITE_B64){{_showToast('SQLite not embedded (empty or too large).');return;}}
  const bin=atob(SQLITE_B64);const arr=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const blob=new Blob([arr],{{type:'application/x-sqlite3'}});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=REPORT_BASE+'_'+ts+'.sqlite';document.body.appendChild(a);a.click();
  setTimeout(()=>{{URL.revokeObjectURL(a.href);document.body.removeChild(a);}},100);
  _showToast('Exported SQLite database');
}}
function _showToast(msg){{const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200);}}
function doExport(fmt,scope){{
  const rows=_getRows(scope);
  if(!rows.length){{_showToast('No results to export.');return;}}
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const base=REPORT_BASE+'_links_'+_scopeLabel(scope)+'_'+ts;
  if(fmt==='txt'){{
    const lines=rows.map((r,i)=>{{let s=(i+1)+'. '+r.url+'\\n';if(r.title)s+='   Title: '+r.title+'\\n';if(r.sqli&&r.sqli!=='untested')s+='   SQLi: '+r.sqli.toUpperCase()+'\\n';if(r.xss&&r.xss!=='untested')s+='   XSS: '+r.xss.toUpperCase()+'\\n';s+='   Time: '+r.timestamp+'\\n';return s;}});
    _download('DorkEye Export\\nScope: '+scope+'\\nGenerated: '+ts+'\\nTotal: '+rows.length+'\\n\\n'+lines.join('\\n'),base+'.txt','text/plain');
    _showToast('Exported '+rows.length+' links');
  }}else if(fmt==='json'){{
    _download(JSON.stringify({{meta:{{generated:ts,scope:scope,total:rows.length}},results:rows}},null,2),base+'.json','application/json');
    _showToast('Exported '+rows.length+' links');
  }}else if(fmt==='csv'){{
    const headers=['url','title','dork','category','ext','sqli','conf','waf','xss','xss_conf','xss_types','timestamp'];
    const esc=v=>{{const s=String(v??'');return s.includes(',')||s.includes('"')||s.includes('\\n')?'"'+s.replace(/"/g,'""')+'"':s;}};
    _download([headers.join(','),...rows.map(r=>headers.map(h=>esc(r[h]||'')).join(','))].join('\\r\\n'),base+'.csv','text/csv');
    _showToast('Exported '+rows.length+' links');
  }}
}}
function toggleFilesPanel(){{
  const p=document.getElementById('filesPanel'),t=document.getElementById('filesToggle');
  const open=p.classList.contains('open');closeAllPanels();
  if(!open){{p.classList.add('open');t.classList.add('open');updateSelCount();}}
}}
function updateSelCount(){{const n=document.querySelectorAll('.file-chk:checked').length;const el=document.getElementById('selCount');if(el)el.textContent=n;}}
function selectAllFiles(val){{document.querySelectorAll('.file-chk').forEach(c=>c.checked=val);updateSelCount();}}
function exportSelectedFiles(fmt){{
  const checked=Array.from(document.querySelectorAll('.file-chk:checked'));
  if(!checked.length){{_showToast('No files selected.');return;}}
  const rows=checked.map(c=>FILE_DATA[parseInt(c.dataset.fidx)]).filter(Boolean);
  const ts=new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const base=REPORT_BASE+'_files_selected_'+ts;
  if(fmt==='list'){{
    const lines=rows.map((r,i)=>(i+1)+'. '+r.url+'\\n   Category: '+r.category+'\\n   Size: '+r.size_str+'\\n');
    _download('DorkEye File List\\nGenerated: '+ts+'\\n\\n'+lines.join('\\n'),base+'.txt','text/plain');
    _showToast('File list ('+rows.length+') exported');
  }}else if(fmt==='json'){{
    _download(JSON.stringify({{meta:{{generated:ts,total:rows.length}},files:rows}},null,2),base+'.json','application/json');
    _showToast('File list ('+rows.length+') exported');
  }}
}}
function closeAllPanels(){{
  ['srchPanel','exportPanel','filesPanel'].forEach(id=>document.getElementById(id).classList.remove('open'));
  ['srchToggle','exportToggle','filesToggle'].forEach(id=>document.getElementById(id).classList.remove('open'));
}}
document.addEventListener('click',(e)=>{{
  if(!e.target.closest('.filter-group')&&!e.target.closest('.filter-btn[data-group]'))closeAllSubMenus();
  if(!e.target.closest('.srch-wrap')&&!e.target.closest('.export-wrap')&&!e.target.closest('.files-wrap'))closeAllPanels();
}});
buildSubBadges();updateInfoBar();updateExportCounts();updateSelCount();
let _infoOpen=false;
function showInfo(btn){{
  const d=JSON.parse(btn.getAttribute('data-info'));
  const sqliColor=d.sqli&&d.sqli.startsWith('VULN')?'#ff3333':d.sqli==='SAFE'?'#00ff41':d.sqli.startsWith('VULNERABLE')?'#ff00ff':'#444';
  const xssColor=d.xss&&d.xss.startsWith('VULN')?'#ffaa00':d.xss==='SAFE'?'#00ff41':'#444';
  let rows='';
  const _h=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
  const row=(lbl,val,color)=>val?`<div class="info-row"><span class="info-lbl">${{lbl}}</span><span class="info-val" style="color:${{color||'#00aaff'}}">${{_h(val)}}</span></div>`:'';
  rows+=row('URL',d.url.length>80?d.url.slice(0,80)+'...':d.url);
  rows+=row('Title',d.title);rows+=row('Category',d.category,'#00cc88');rows+=row('Extension',d.ext,'#ffaa00');
  rows+=row('Size',d.size,'#009922');rows+=row('Timestamp',d.ts,'#666');rows+=row('Dork',d.dork&&d.dork.length>80?d.dork.slice(0,80)+'...':d.dork,'#cc88ff');
  rows+=row('Snippet',d.snippet&&d.snippet.length>120?d.snippet.slice(0,120)+'...':d.snippet,'#777');
  if(d.sqli)rows+=row('SQLi',d.sqli,sqliColor);if(d.payload)rows+=row('SQLi Method',d.payload.length>100?d.payload.slice(0,100)+'...':d.payload,'#ff6666');
  if(d.xss)rows+=row('XSS',d.xss,xssColor);if(d.xss_det)rows+=row('XSS Detail',d.xss_det.length>100?d.xss_det.slice(0,100)+'...':d.xss_det,'#ffcc66');
  if(d.waf)rows+=row('WAF','! '+d.waf,'#ffaa00');
  document.getElementById('infoBody').innerHTML=rows||'<span style="color:#444">No details.</span>';
  document.getElementById('infoPopup').classList.add('open');
  document.getElementById('infoOverlay').classList.add('open');
  _infoOpen=true;document.body.style.overflow='hidden';
}}
function closeInfo(){{document.getElementById('infoPopup').classList.remove('open');document.getElementById('infoOverlay').classList.remove('open');document.body.style.overflow='';_infoOpen=false;}}
document.addEventListener('keydown',(e)=>{{if(_infoOpen&&e.key==='Escape')closeInfo();}});
</script>
</body>
</html>""")

        html = "".join(parts)
        return html


def write_dork_report(filename, results, stats, start_time):
    """Write the standalone Dorks report (byte-identical to the previous output)."""
    report_base = os.path.splitext(os.path.basename(filename))[0]
    html = build_dork_html(results, stats, start_time, report_base)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename



# ══════════════════════════════════════════════════════════════════════════════
#  Unified tabbed report (Phase 2/3)
#  One HTML that hosts several reports as tabs. Each report is embedded in its own
#  sandbox-free <iframe srcdoc> so there are zero CSS/JS collisions between tabs
#  and each existing report keeps working exactly as it does standalone. New
#  report types (Dorks, OSINT, DBScan, Crawl, Analyze) are just extra tabs.
# ══════════════════════════════════════════════════════════════════════════════

_UNIFIED_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DorkEye | Report</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:'Courier New',monospace;background:#000;color:#00ff41;display:flex;flex-direction:column}
.tabbar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;
padding:10px 14px;background:rgba(0,12,0,0.95);border-bottom:1px solid #00aa2a;
box-shadow:0 0 18px rgba(0,255,65,0.12);z-index:2}
.tabbar .brand{color:#00ff41;font-weight:bold;letter-spacing:2px;margin-right:12px;text-shadow:0 0 8px #00ff41}
.tab{background:transparent;color:#009922;border:1px solid #00661a;border-radius:6px;
padding:7px 16px;cursor:pointer;font:inherit;letter-spacing:1px;text-transform:uppercase}
.tab:hover{color:#00ff41;border-color:#00aa2a}
.tab.active{color:#000;background:#00ff41;border-color:#00ff41;font-weight:bold;
box-shadow:0 0 12px rgba(0,255,65,0.5)}
.tab .cnt{opacity:.7;font-size:11px}
.frames{position:relative;flex:1;min-height:0}
.frames iframe{position:absolute;inset:0;width:100%;height:100%;border:0;display:none;background:#000}
.frames iframe.active{display:block}
</style></head><body>
<div class="tabbar"><span class="brand">&#9632; DorkEye</span>{tabs}</div>
<div class="frames">{frames}</div>
<script>
function showTab(i){
  document.querySelectorAll('.tabbar .tab').forEach((b,j)=>b.classList.toggle('active',i===j));
  document.querySelectorAll('.frames iframe').forEach((f,j)=>f.classList.toggle('active',i===j));
}
document.addEventListener('DOMContentLoaded',()=>showTab(0));
</script>
</body></html>"""


def write_report(filename, tabs):
    """
    Write one unified tabbed HTML. `tabs` is a list of (label, html_string).
    Each html_string is a complete, self-contained report page; it is embedded
    verbatim in an isolated iframe, so nothing clashes between tabs.
    Empty/None html entries are skipped. With a single tab the bar still shows
    but is harmless. Returns the path written.
    """
    tabs = [(lbl, h) for (lbl, h) in tabs if h]
    if not tabs:
        return filename
    btns, frames = [], []
    for i, (label, inner) in enumerate(tabs):
        active = " active" if i == 0 else ""
        btns.append(
            f'<button class="tab{active}" onclick="showTab({i})">{html.escape(str(label))}</button>'
        )
        frames.append(
            f'<iframe class="frame{active}" srcdoc="{html.escape(inner, quote=True)}"></iframe>'
        )
    page = _UNIFIED_TEMPLATE.replace("{tabs}", "".join(btns)).replace(
        "{frames}", "".join(frames))
    with open(filename, "w", encoding="utf-8") as f:
        f.write(page)
    return filename


# ══════════════════════════════════════════════════════════════════════════════
#  DBScan HTML report (Phase 3) — renders a DBScanReport as a matrix-themed page
#  so it can be embedded as a tab in the unified report.
# ══════════════════════════════════════════════════════════════════════════════

_SEV_COLOR = {"CRITICAL": "#ff3344", "HIGH": "#ffaa00", "MEDIUM": "#ffd93d", "INFO": "#009922"}


def render_dbscan_html(report, report_base="dbscan"):
    """Return an HTML string for a DBScanReport (db_portscan.DBScanReport)."""
    try:
        data = report.to_dict()
    except Exception:
        data = {"stats": {}, "hosts": []}
    stats = data.get("stats", {}) or {}
    hosts = data.get("hosts", []) or []

    def esc(x):
        return html.escape(str(x))

    stat_cells = "".join(
        f'<div class="sc"><h3>{esc(k.replace("_", " ").title())}</h3>'
        f'<p>{esc(v)}</p></div>'
        for k, v in stats.items()
    ) or '<div class="sc"><h3>Hosts</h3><p>0</p></div>'

    host_blocks = []
    for h in hosts:
        findings = h.get("findings", []) or []
        open_f = [f for f in findings if f.get("status") == "open"]
        if not open_f:
            continue
        rows = ""
        for f in sorted(open_f, key=lambda x: x.get("severity", "INFO")):
            sev = f.get("severity", "INFO")
            col = _SEV_COLOR.get(sev, "#009922")
            noauth = ' <span style="color:#ff3344">NO-AUTH</span>' if f.get("no_auth") else ""
            banner = esc((f.get("banner", "") or "")[:120])
            rows += (
                f'<tr><td>{esc(f.get("port",""))}</td>'
                f'<td>{esc(f.get("service",""))}</td>'
                f'<td style="color:{col};font-weight:bold">{esc(sev)}{noauth}</td>'
                f'<td>{esc(f.get("probe",""))}</td>'
                f'<td class="ban">{banner}</td></tr>'
            )
        host_blocks.append(
            f'<div class="host"><div class="hh">&#9632; {esc(h.get("host",""))} '
            f'<span class="dim">({len(open_f)} open · {h.get("critical",0)} crit · '
            f'{h.get("high",0)} high)</span></div>'
            f'<table><tr><th>Port</th><th>Service</th><th>Severity</th>'
            f'<th>Probe</th><th>Banner</th></tr>{rows}</table></div>'
        )
    body = "".join(host_blocks) or '<p class="dim">No open database ports found.</p>'

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DorkEye | DBScan</title><style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Courier New',monospace;background:#000;color:#00ff41;padding:24px}}
h1{{font-size:20px;color:#00ff41;text-shadow:0 0 8px #00ff41;letter-spacing:2px;margin-bottom:16px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:22px}}
.sc{{background:rgba(0,12,0,0.85);border:1px solid #00aa2a;padding:12px 14px}}
.sc h3{{font-size:10px;color:#009922;letter-spacing:1px;text-transform:uppercase}}
.sc p{{font-size:22px;font-weight:bold;color:#00ff41;margin-top:6px}}
.host{{background:rgba(0,12,0,0.6);border:1px solid #00661a;border-left:3px solid #00ff41;
padding:12px 16px;margin-bottom:14px}}
.hh{{color:#00ff41;font-weight:bold;margin-bottom:8px}}
.dim{{color:#009922;font-weight:normal}}
table{{width:100%;border-collapse:collapse;margin-top:4px}}
th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #00330f;font-size:13px;word-break:break-all}}
th{{color:#009922}} .ban{{color:#4aa;font-size:11px}}
</style></head><body>
<h1>&#9632; DorkEye | DB Port Scan</h1>
<div class="stats">{stat_cells}</div>
{body}
</body></html>"""
