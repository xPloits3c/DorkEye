#!/usr/bin/env python3
"""
DorkEye Web Dashboard
Matrix-style local web interface for all DorkEye operations.
Auto-selects a free port starting from 8080 and opens the browser.
Web GUI created for DorkEye Project.
Author: @xPloits3c

Usage (via dorkeye.py):
    python dorkeye.py --ui
    python dorkeye.py --ui --port 9090

Usage standalone:
    python dorkeye_web.py
"""

import os
import sys
import re
import json
import time
import uuid
import socket
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from collections import deque

# ── Flask check ───────────────────────────────────────────────────────────────
try:
    from flask import (
        Flask, Response, jsonify, request,
        render_template_string, send_from_directory,
        stream_with_context,
    )
    _FLASK = True
except ImportError:
    _FLASK = False

# ── Path roots ────────────────────────────────────────────────────────────────
# dorkeye_web.py sta in Tools/, dorkeye.py sta nella root del progetto.
# Risaliamo cercando dorkeye.py per trovare la root corretta.
def _find_project_root() -> Path:
    """
    Risale l'albero partendo da __file__ cercando dorkeye.py.
    Funziona sia se dorkeye_web.py e' in Tools/ che nella root.
      DorkEye/
          dorkeye.py          <- root cercata
          Tools/
              dorkeye_web.py  <- __file__
    """
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        if (candidate / "dorkeye.py").exists():
            return candidate
    return here  # fallback: stessa directory

ROOT          = _find_project_root()
DUMP_DIR      = ROOT / "Dump"
TEMPLATES_DIR = ROOT / "Templates"
DORKEYE_PY    = ROOT / "dorkeye.py"
PYTHON_EXE    = sys.executable

# strip ANSI/Rich markup from subprocess output
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mGKHFJA-Za-z]|\r|\x1b\].*?\x07')

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub('', s)

# ── Port finder ───────────────────────────────────────────────────────────────

def find_free_port(start: int = 8080) -> int:
    for p in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return start


# ══════════════════════════════════════════════════════════════════════════════
#  Job system
# ══════════════════════════════════════════════════════════════════════════════

class Job:
    __slots__ = ('jid', 'cmd', 'label', 'output_file',
                 'status', 'started', 'ended', 'lines', 'proc', '_lock')

    def __init__(self, jid: str, cmd: list, label: str, output_file: str = None):
        self.jid         = jid
        self.cmd         = cmd
        self.label       = label
        self.output_file = output_file
        self.status      = 'running'
        self.started     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ended       = None
        self.lines       = deque(maxlen=20000)
        self.proc        = None
        self._lock       = threading.Lock()

    def add(self, line: str) -> None:
        with self._lock:
            self.lines.append((time.monotonic(), line))

    def since(self, ts: float = 0.0) -> list:
        with self._lock:
            return [(t, l) for t, l in self.lines if t > ts]

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.status = 'killed'
        self.ended  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self) -> dict:
        return {
            'id':          self.jid,
            'label':       self.label,
            'cmd':         ' '.join(str(x) for x in self.cmd),
            'status':      self.status,
            'started':     self.started,
            'ended':       self.ended or '—',
            'output_file': self.output_file or '',
        }


class JobManager:
    def __init__(self):
        self._jobs: dict = {}
        self._lock       = threading.Lock()

    def spawn(self, cmd: list, label: str, output_file: str = None) -> str:
        jid = uuid.uuid4().hex[:8]
        job = Job(jid, cmd, label, output_file)

        with self._lock:
            self._jobs[jid] = job

        env = os.environ.copy()
        env.update({'PYTHONUNBUFFERED': '1', 'NO_COLOR': '1', 'FORCE_COLOR': '0'})

        def _run():
            try:
                proc = subprocess.Popen(
                    [str(c) for c in cmd],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                    cwd=str(ROOT),
                )
                job.proc = proc
                # Send 'n\n' to auto-answer any checkpoint resume prompt
                try:
                    proc.stdin.write('n\n')
                    proc.stdin.flush()
                    proc.stdin.close()
                except Exception:
                    pass

                for raw in proc.stdout:
                    job.add(strip_ansi(raw.rstrip('\n')))

                proc.wait()
                job.status = 'done' if proc.returncode == 0 else 'error'

            except Exception as e:
                job.add(f'[LAUNCHER ERROR] {e}')
                job.status = 'error'
            finally:
                job.ended = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        threading.Thread(target=_run, daemon=True, name=f'job-{jid}').start()
        return jid

    def get(self, jid: str):
        with self._lock:
            return self._jobs.get(jid)

    def all_jobs(self) -> list:
        with self._lock:
            return [j.to_dict() for j in reversed(list(self._jobs.values()))]

    def count_running(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == 'running')


# ── Global state ──────────────────────────────────────────────────────────────
JOBS = JobManager()


# ══════════════════════════════════════════════════════════════════════════════
#  Command builder
# ══════════════════════════════════════════════════════════════════════════════

def build_scan_cmd(d: dict) -> list:
    """Build dorkeye.py CLI command from web form payload dict."""
    cmd = [PYTHON_EXE, str(DORKEYE_PY)]

    if d.get('dork'):
        # Handle multiline dorks: if newline present, write to temp file
        dork_val = d['dork'].strip()
        if '\n' in dork_val:
            tmp_path = ROOT / 'Dump' / f'_web_dorks_{uuid.uuid4().hex[:6]}.txt'
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(dork_val, encoding='utf-8')
            cmd += ['-d', str(tmp_path)]
        else:
            cmd += ['-d', dork_val]

    if d.get('count'):
        cmd += ['-c', str(int(d['count']))]

    out = d.get('output', '').strip()
    if not out:
        ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = f'web_scan_{ts}.html'
    cmd += ['-o', out]

    mode = d.get('mode', 'soft')
    if mode != 'soft':
        cmd += ['--mode', mode]

    if d.get('stealth'):      cmd.append('--stealth')
    if d.get('sqli'):         cmd.append('--sqli')
    if d.get('xss'):
        cmd.append('--xss')
        xtype = d.get('xss_type', 'all')
        if xtype != 'all':
            cmd += ['--xss-type', xtype]
    if d.get('no_analyze'):   cmd.append('--no-analyze')
    if d.get('no_fingerprint'): cmd.append('--no-fingerprint')

    bl = d.get('blacklist', '').strip()
    if bl:
        cmd += ['--blacklist'] + bl.split()
    wl = d.get('whitelist', '').strip()
    if wl:
        cmd += ['--whitelist'] + wl.split()

    cfg = d.get('config', '').strip()
    if cfg:
        cmd += ['--config', cfg]

    tpl = d.get('templates', '').strip()
    if d.get('dg'):
        dg_cat = d.get('dg_cat', 'all') or 'all'
        cmd.append(f'--dg={dg_cat}')
        dg_max = d.get('dg_max', 800)
        cmd += ['--dg-max', str(int(dg_max))]
        if tpl:
            cmd.append(f'--templates={tpl}')

    if d.get('analyze'):
        cmd.append('--analyze')
        if d.get('analyze_fetch'):
            cmd.append('--analyze-fetch')
        afm = d.get('analyze_fetch_max')
        if afm:
            cmd += ['--analyze-fetch-max', str(int(afm))]
        afmt = d.get('analyze_fmt', 'html')
        if afmt:
            cmd += ['--analyze-fmt', afmt]
        aout = d.get('analyze_out', '').strip()
        if aout:
            cmd += ['--analyze-out', aout]

    if d.get('crawl'):
        cmd.append('--crawl')
        cr = d.get('crawl_rounds')
        cm = d.get('crawl_max')
        cp = d.get('crawl_per_dork')
        if cr: cmd += ['--crawl-rounds', str(int(cr))]
        if cm: cmd += ['--crawl-max',    str(int(cm))]
        if cp: cmd += ['--crawl-per-dork', str(int(cp))]
        if d.get('crawl_stealth'): cmd.append('--crawl-stealth')
        if d.get('crawl_report'):  cmd.append('--crawl-report')
        co = d.get('crawl_out', '').strip()
        if co: cmd += ['--crawl-out', co]

    if d.get('dbscan'):
        cmd.append('--dbscan')
        dbt  = d.get('dbscan_timeout')
        dbth = d.get('dbscan_threads')
        dbmh = d.get('dbscan_max_hosts')
        if dbt:  cmd += ['--dbscan-timeout',   str(float(dbt))]
        if dbth: cmd += ['--dbscan-threads',   str(int(dbth))]
        if dbmh: cmd += ['--dbscan-max-hosts', str(int(dbmh))]

    return cmd, out


def build_urltest_cmd(d: dict) -> list:
    cmd = [PYTHON_EXE, str(DORKEYE_PY), '-u', d['url']]
    if d.get('sqli'):  cmd.append('--sqli')
    if d.get('xss'):
        cmd.append('--xss')
        xtype = d.get('xss_type', 'all')
        if xtype != 'all':
            cmd += ['--xss-type', xtype]
    if d.get('stealth'): cmd.append('--stealth')
    out = d.get('output', '').strip()
    if not out:
        out = f'url_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    cmd += ['-o', out]
    return cmd, out


def build_file_cmd(d: dict) -> list:
    fpath = d.get('file', '')
    cmd   = [PYTHON_EXE, str(DORKEYE_PY), '-f', fpath]
    if d.get('sqli'):  cmd.append('--sqli')
    if d.get('xss'):   cmd.append('--xss')
    if d.get('dbscan'):
        cmd.append('--dbscan')
        dbt  = d.get('dbscan_timeout')
        dbth = d.get('dbscan_threads')
        dbmh = d.get('dbscan_max_hosts')
        if dbt:  cmd += ['--dbscan-timeout',   str(float(dbt))]
        if dbth: cmd += ['--dbscan-threads',   str(int(dbth))]
        if dbmh: cmd += ['--dbscan-max-hosts', str(int(dbmh))]
    out = d.get('output', '').strip()
    if not out:
        out = f'file_retest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    cmd += ['-o', out]
    return cmd, out


# ══════════════════════════════════════════════════════════════════════════════
#  Dump browser helpers
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_size(b: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if b < 1024:
            return f'{b:.1f} {unit}'
        b /= 1024
    return f'{b:.1f} TB'


def list_dump_files() -> dict:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    total = 0
    for p in sorted(DUMP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file() and not p.name.startswith('_') and p.suffix.lower() in ('.html', '.json', '.txt', '.csv', '.md'):
            sz = p.stat().st_size
            total += sz
            files.append({
                'name':     p.name,
                'size':     sz,
                'size_str': _fmt_size(sz),
                'mtime':    datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
            })
    return {'files': files, 'total_size': total, 'total_size_str': _fmt_size(total)}


# ══════════════════════════════════════════════════════════════════════════════
#  DorkGenerator helper (in-process)
# ══════════════════════════════════════════════════════════════════════════════

def _get_dork_generator():
    """Import DorkGenerator from the project root or Tools/."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    tools_dir = ROOT / 'Tools'
    if str(tools_dir) not in sys.path and tools_dir.exists():
        sys.path.insert(0, str(tools_dir))
    from dork_generator import DorkGenerator
    return DorkGenerator


def _resolve_template(tpl_str: str):
    """
    Risolve l'argomento --templates in una lista di Path.

    BUG FIX: il vecchio codice hardcodava 'dorks_templates.yaml' che
    spesso non esiste. Ora:
      - 'default' / ''  -> primo yaml disponibile in Templates/
                           (dorks_templates.yaml se presente, altrimenti
                            il primo in ordine alfabetico)
      - 'all'           -> tutti i *.yaml in Templates/
      - nome specifico  -> quel file; se non esiste, fallback a tutti
    """
    all_yaml = sorted(TEMPLATES_DIR.glob('*.yaml')) if TEMPLATES_DIR.exists() else []
    preferred = TEMPLATES_DIR / 'dorks_templates.yaml'

    if not tpl_str or tpl_str == 'default':
        if preferred.exists():
            return [preferred]
        return all_yaml if all_yaml else []

    if tpl_str == 'all':
        return all_yaml

    p = TEMPLATES_DIR / tpl_str
    if p.exists():
        return [p]
    # fallback se il nome specifico non esiste
    return [preferred] if preferred.exists() else all_yaml


# ══════════════════════════════════════════════════════════════════════════════
#  Flask app
# ══════════════════════════════════════════════════════════════════════════════

def create_app(port: int) -> 'Flask':
    app = Flask(__name__, static_folder=None)
    app.config['SECRET_KEY'] = uuid.uuid4().hex

    # ── Main page ─────────────────────────────────────────────────────────────
    @app.route('/')
    def index():
        return render_template_string(_HTML_TEMPLATE, port=port)

    # ── Serve Dump files ──────────────────────────────────────────────────────
    @app.route('/dump/<path:filename>')
    def dump_serve(filename):
        return send_from_directory(str(DUMP_DIR), filename)

    # ── Status ────────────────────────────────────────────────────────────────
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status':  'online',
            'version': '4.9',
            'port':    port,
            'running': JOBS.count_running(),
        })

    # ── Job list ──────────────────────────────────────────────────────────────
    @app.route('/api/jobs')
    def api_jobs():
        return jsonify(JOBS.all_jobs())

    # ── Job detail ────────────────────────────────────────────────────────────
    @app.route('/api/jobs/<jid>')
    def api_job_detail(jid):
        job = JOBS.get(jid)
        if not job:
            return jsonify({'error': 'not found'}), 404
        d = job.to_dict()
        d['lines'] = [{'t': t, 'l': l} for t, l in job.since()]
        return jsonify(d)

    # ── Kill job ──────────────────────────────────────────────────────────────
    @app.route('/api/jobs/<jid>', methods=['DELETE'])
    def api_job_kill(jid):
        job = JOBS.get(jid)
        if not job:
            return jsonify({'error': 'not found'}), 404
        job.kill()
        return jsonify({'ok': True, 'status': job.status})

    # ── SSE stream ───────────────────────────────────────────────────────────
    @app.route('/api/stream/<jid>')
    def api_stream(jid):
        job = JOBS.get(jid)
        if not job:
            return Response(
                f'data: {json.dumps({"error": "not found"})}\n\n',
                mimetype='text/event-stream',
            )

        def generate():
            last_ts = 0.0
            idle    = 0
            while True:
                lines = job.since(last_ts)
                if lines:
                    idle   = 0
                    last_ts = lines[-1][0]
                    payload = json.dumps({'lines': [{'t': t, 'l': l} for t, l in lines]})
                    yield f'data: {payload}\n\n'
                else:
                    idle += 1

                if job.status != 'running':
                    # Drain any last lines
                    lines = job.since(last_ts)
                    if lines:
                        payload = json.dumps({'lines': [{'t': t, 'l': l} for t, l in lines]})
                        yield f'data: {payload}\n\n'
                    yield f'data: {json.dumps({"done": True, "status": job.status})}\n\n'
                    return

                time.sleep(0.25)

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control':     'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection':        'keep-alive',
            },
        )

    # ── Run a job ─────────────────────────────────────────────────────────────
    @app.route('/api/run', methods=['POST'])
    def api_run():
        d = request.json or {}
        jtype = d.get('type', 'scan')

        try:
            if jtype == 'scan':
                cmd, out = build_scan_cmd(d)
                dork_val = d.get('dork', '')
                if d.get('dg'):
                    lbl = f"DorkGen: {d.get('dg_cat','all')} [{d.get('mode','soft')}]"
                else:
                    lbl = ('Scan: ' + dork_val[:55]).rstrip()
            elif jtype == 'urltest':
                cmd, out = build_urltest_cmd(d)
                lbl = 'URLTest: ' + d.get('url', '')[:55]
            elif jtype == 'file':
                cmd, out = build_file_cmd(d)
                lbl = 'FileMode: ' + d.get('file', '')[:50]
            else:
                return jsonify({'error': f'Unknown type: {jtype}'}), 400

            jid = JOBS.spawn(cmd, lbl, output_file=out)
            return jsonify({'job_id': jid, 'label': lbl, 'output': out})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Dump listing ─────────────────────────────────────────────────────────
    @app.route('/api/dump')
    def api_dump():
        return jsonify(list_dump_files())

    # ── Template file list ────────────────────────────────────────────────────
    @app.route('/api/templates/list')
    def api_tpl_list():
        files = [p.name for p in sorted(TEMPLATES_DIR.glob('*.yaml'))] if TEMPLATES_DIR.exists() else []
        return jsonify({'files': files})

    # ── Template categories ───────────────────────────────────────────────────
    @app.route('/api/templates/categories')
    def api_tpl_cats():
        tpl = request.args.get('tpl', '')
        try:
            DorkGenerator = _get_dork_generator()
            tpl_files     = _resolve_template(tpl)
            cats          = set()
            for tf in tpl_files:
                if tf.exists():
                    gen  = DorkGenerator(str(tf))
                    cats.update(gen.get_available_categories())
            # FIX: includi info diagnostica nella risposta
            return jsonify({
                'categories': sorted(cats),
                'templates_dir': str(TEMPLATES_DIR),
                'files_found': [tf.name for tf in tpl_files if tf.exists()],
            })
        except Exception as e:
            return jsonify({'categories': [], 'error': str(e)})

    # ── DorkGen preview ───────────────────────────────────────────────────────
    @app.route('/api/dorkgen/preview', methods=['POST'])
    def api_dg_preview():
        d     = request.json or {}
        limit = min(int(d.get('max', 800)), 10000)
        try:
            DorkGenerator = _get_dork_generator()
            tpl_files     = _resolve_template(d.get('templates', ''))
            cat           = d.get('category', 'all')
            mode          = d.get('mode', 'soft')

            # FIX: diagnostica esplicita se nessun template è disponibile
            if not tpl_files:
                return jsonify({
                    'error': f'Nessun file .yaml trovato in {TEMPLATES_DIR}. '
                             f'Assicurati che la cartella Templates/ esista nella '
                             f'root del progetto ({ROOT}) e contenga almeno un file .yaml.',
                    'dorks': [],
                })

            dorks       = []
            loaded      = []
            missing     = []
            for tf in tpl_files:
                if tf.exists():
                    gen  = DorkGenerator(str(tf), max_combinations=limit)
                    cats = [cat] if cat != 'all' else None
                    dorks.extend(gen.generate(categories=cats, mode=mode))
                    loaded.append(tf.name)
                else:
                    missing.append(tf.name)

            # FIX: se tutti i template mancano, ritorna errore descrittivo
            if not loaded:
                return jsonify({
                    'error': f'Template non trovati: {missing}. '
                             f'Percorso atteso: {TEMPLATES_DIR}',
                    'dorks': [],
                })

            dorks = list(dict.fromkeys(dorks))[:limit]
            warn  = (f' | template mancanti: {missing}') if missing else ''
            return jsonify({
                'dorks':   dorks,
                'count':   len(dorks),
                'loaded':  loaded,
                'warning': warn.strip() if warn else None,
            })
        except Exception as e:
            return jsonify({'error': str(e), 'dorks': []})

    # ── DorkGen export (plain text) ───────────────────────────────────────────
    @app.route('/api/dorkgen/export', methods=['POST'])
    def api_dg_export():
        d     = request.json or {}
        limit = min(int(d.get('max', 800)), 10000)
        try:
            DorkGenerator = _get_dork_generator()
            tpl_files     = _resolve_template(d.get('templates', ''))
            cat           = d.get('category', 'all')
            mode          = d.get('mode', 'soft')
            dorks         = []
            for tf in tpl_files:
                if tf.exists():
                    gen  = DorkGenerator(str(tf), max_combinations=limit)
                    cats = [cat] if cat != 'all' else None
                    dorks.extend(gen.generate(categories=cats, mode=mode))
            dorks  = list(dict.fromkeys(dorks))[:limit]
            text   = '\n'.join(dorks)
            ts     = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname  = f'dorkeye_dorks_{ts}.txt'
            return Response(
                text,
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename="{fname}"'},
            )
        except Exception as e:
            return Response(f'Error: {e}', status=500)

    return app


# ══════════════════════════════════════════════════════════════════════════════
#  HTML TEMPLATE  (Matrix theme — matches dorkeye.py HTML output)
# ══════════════════════════════════════════════════════════════════════════════

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DorkEye | Web Console</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --g1:#00ff41;--g2:#00cc33;--g3:#009922;--g4:#005500;--g5:#002200;
  --bg:#000;--panel:rgba(0,10,0,.88);--border:#00aa2a;
  --red:#ff3333;--yellow:#ffcc00;--blue:#00aaff;--mag:#cc44ff;
  --font:'Courier New',Courier,monospace;
}
body{font-family:var(--font);background:var(--bg);color:var(--g1);height:100vh;overflow:hidden;display:flex;flex-direction:column}
#mc{position:fixed;inset:0;opacity:.28;pointer-events:none;z-index:0}
#app{position:relative;z-index:1;display:flex;flex-direction:column;height:100vh}

/* ── Header ── */
#hdr{display:flex;align-items:center;gap:14px;padding:7px 20px;border-bottom:1px solid var(--border);background:rgba(0,5,0,.97);flex-shrink:0;min-height:42px}
#logo{font-size:17px;letter-spacing:3px;font-weight:bold;color:var(--g1);text-shadow:0 0 14px var(--g1);white-space:nowrap}
#logo span{color:var(--red)}
.vbadge{font-size:10px;color:var(--g3);border:1px solid var(--g5);padding:2px 6px}
.pulse{width:8px;height:8px;border-radius:50%;background:var(--g1);animation:pulse 2s infinite;flex-shrink:0}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
#hdr-r{margin-left:auto;display:flex;gap:12px;align-items:center;font-size:11px}
#aj-badge{color:var(--yellow);display:none}
#aj-badge.show{display:inline}
#sclock{color:var(--g5)}

/* ── Layout ── */
#main{display:flex;flex:1;overflow:hidden}

/* ── Sidebar ── */
#sb{width:174px;border-right:1px solid var(--border);background:rgba(0,4,0,.95);display:flex;flex-direction:column;flex-shrink:0}
.nav{padding:11px 15px;cursor:pointer;font-size:11px;letter-spacing:1.5px;color:var(--g3);border-bottom:1px solid rgba(0,170,42,.12);display:flex;align-items:center;gap:9px;transition:all .14s;text-transform:uppercase;user-select:none}
.nav:hover{color:var(--g1);background:rgba(0,255,65,.05);padding-left:20px}
.nav.active{color:var(--g1);background:rgba(0,255,65,.1);border-left:3px solid var(--g1);padding-left:12px}
.nbadge{margin-left:auto;font-size:9px;background:rgba(0,255,65,.1);border:1px solid var(--g5);padding:1px 5px;color:var(--g2)}
#sb-ft{margin-top:auto;padding:10px 14px;font-size:10px;color:var(--g5);border-top:1px solid rgba(0,170,42,.15);line-height:1.6}
#sb-ft b{color:var(--g4)}

/* ── Content ── */
#cnt{flex:1;overflow-y:auto;overflow-x:hidden;padding:18px 22px}
#cnt::-webkit-scrollbar{width:5px}
#cnt::-webkit-scrollbar-thumb{background:var(--g5)}
.sec{display:none}
.sec.active{display:block}
.phdr{margin-bottom:18px}
.phdr h1{font-size:15px;letter-spacing:2.5px;color:var(--g1);text-shadow:0 0 8px rgba(0,255,65,.25)}
.phdr p{font-size:10px;color:var(--g3);margin-top:4px;letter-spacing:1px}

/* ── Cards ── */
.cg{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:18px}
.card{background:var(--panel);border:1px solid var(--border);padding:14px 16px;transition:border-color .18s;cursor:default}
.card:hover{border-color:var(--g1)}
.clbl{font-size:10px;color:var(--g3);letter-spacing:1.5px;text-transform:uppercase}
.cval{font-size:26px;font-weight:bold;color:var(--g1);margin-top:5px;text-shadow:0 0 8px rgba(0,255,65,.35)}
.csub{font-size:10px;color:var(--g5);margin-top:3px}

/* ── Quick actions ── */
.qa{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.qab{display:flex;flex-direction:column;align-items:center;gap:5px;background:var(--panel);border:1px solid var(--border);padding:14px 18px;cursor:pointer;min-width:110px;transition:all .14s}
.qab:hover{border-color:var(--g1);background:rgba(0,255,65,.06)}
.qai{font-size:20px}
.qal{font-size:10px;color:var(--g3);letter-spacing:1.5px;text-transform:uppercase}

/* ── Form ── */
.fs{background:var(--panel);border:1px solid var(--border);padding:16px 18px;margin-bottom:12px}
.fst{font-size:11px;color:var(--g1);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;border-bottom:1px solid rgba(0,170,42,.25);padding-bottom:7px;display:flex;align-items:center;gap:8px}
.fr{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:10px}
.fr:last-child{margin-bottom:0}
.fg{display:flex;flex-direction:column;gap:4px}
.fg label{font-size:10px;color:var(--g3);letter-spacing:1px;text-transform:uppercase}
input,select,textarea{background:rgba(0,6,0,.85);border:1px solid var(--g5);color:var(--g1);font-family:var(--font);font-size:12px;padding:6px 9px;outline:none;width:100%;transition:border-color .14s}
input:focus,select:focus,textarea:focus{border-color:var(--g3)}
textarea{resize:vertical;min-height:70px}
select option{background:#000}
input[type=number]{-moz-appearance:textfield}

/* ── Toggles ── */
.tr{display:flex;flex-wrap:wrap;gap:8px}
.tgl{display:flex;align-items:center;gap:7px;cursor:pointer;font-size:11px;color:var(--g3);letter-spacing:1px;padding:5px 10px;border:1px solid rgba(0,170,42,.25);transition:all .13s;user-select:none}
.tgl:hover{color:var(--g1);border-color:var(--g1);background:rgba(0,255,65,.05)}
.tgl.on{color:var(--g1);border-color:var(--g1);background:rgba(0,255,65,.09)}
.td{width:8px;height:8px;border-radius:50%;background:var(--g5);transition:background .13s;flex-shrink:0}
.tgl.on .td{background:var(--g1);box-shadow:0 0 5px var(--g1)}

/* ── Buttons ── */
.btn{background:rgba(0,8,0,.8);border:1px solid var(--g3);color:var(--g2);font-family:var(--font);font-size:11px;letter-spacing:2px;padding:7px 16px;cursor:pointer;text-transform:uppercase;transition:all .13s;display:inline-flex;align-items:center;gap:6px;text-decoration:none}
.btn:hover{background:var(--g1);color:#000;border-color:var(--g1)}
.btn.pri{border-color:var(--g1);color:var(--g1)}
.btn.pri:hover{background:var(--g1);color:#000}
.btn.dan{border-color:var(--red);color:var(--red)}
.btn.dan:hover{background:var(--red);color:#000}
.btn.blu{border-color:var(--blue);color:var(--blue)}
.btn.blu:hover{background:var(--blue);color:#000}
.btn.sm{padding:3px 9px;font-size:9px;letter-spacing:1.5px}
.btn:disabled{opacity:.38;cursor:not-allowed}
.btnr{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}

/* ── Tables ── */
.tbl{width:100%;border-collapse:collapse;font-size:11px}
.tbl th{color:var(--g3);font-weight:normal;letter-spacing:1.5px;text-transform:uppercase;padding:7px 10px;border-bottom:1px solid var(--border);text-align:left}
.tbl td{padding:7px 10px;border-bottom:1px solid rgba(0,170,42,.1);color:var(--g2);vertical-align:middle}
.tbl tr:hover td{background:rgba(0,255,65,.03)}
.tbl .uc{max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tbl a{color:var(--blue);text-decoration:none}
.tbl a:hover{text-decoration:underline}
.tbl .mono{font-size:10px;color:var(--g4);font-family:monospace}

/* ── Badges ── */
.badge{display:inline-block;padding:2px 7px;font-size:9px;letter-spacing:1px;text-transform:uppercase}
.badge.running{color:var(--yellow);border:1px solid var(--yellow);animation:bb .7s step-end infinite}
@keyframes bb{50%{opacity:.4}}
.badge.done{color:var(--g1);border:1px solid var(--g3)}
.badge.error{color:var(--red);border:1px solid var(--red)}
.badge.killed{color:var(--g5);border:1px solid var(--g5)}

/* ── Collapse ── */
.ctg{font-size:10px;color:var(--g3);cursor:pointer;letter-spacing:1px;margin-bottom:8px;display:flex;align-items:center;gap:6px;user-select:none}
.ctg:hover{color:var(--g1)}
.cb{display:none}
.cb.open{display:block}

/* ── File list ── */
.fi{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid rgba(0,170,42,.1);font-size:11px}
.fi:hover{background:rgba(0,255,65,.03)}
.fn{color:var(--g1);flex:1;cursor:pointer}
.fn:hover{text-decoration:underline}
.fsz{color:var(--g5);min-width:65px;text-align:right}
.fdt{color:var(--g5);min-width:128px;text-align:right}

/* ── Alerts ── */
.alt{padding:10px 14px;border-left:4px solid;margin-bottom:12px;font-size:11px}
.alt.ok{border-color:var(--g1);color:var(--g1);background:rgba(0,255,65,.04)}
.alt.warn{border-color:var(--yellow);color:var(--yellow);background:rgba(255,200,0,.04)}
.alt.err{border-color:var(--red);color:var(--red);background:rgba(255,0,0,.04)}

/* ── Dork preview ── */
#dgpl{max-height:380px;overflow-y:auto;background:rgba(0,4,0,.9);border:1px solid var(--g5);padding:8px;font-size:11px}
#dgpl::-webkit-scrollbar{width:4px}
#dgpl::-webkit-scrollbar-thumb{background:var(--g5)}
.de{padding:3px 2px;color:var(--g2);border-bottom:1px solid rgba(0,170,42,.08);word-break:break-all}

/* ── Section header row ── */
.shr{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.shr h1{font-size:15px;letter-spacing:2px}
.ml{margin-left:auto}

/* ── Terminal ── */
#trm{border-top:1px solid var(--border);background:rgba(0,3,0,.98);flex-shrink:0;display:flex;flex-direction:column}
#th{display:flex;align-items:center;padding:4px 14px;gap:10px;border-bottom:1px solid rgba(0,170,42,.18);cursor:pointer;font-size:11px;color:var(--g3);user-select:none;min-height:30px}
#th:hover{color:var(--g1)}
#tjl{color:var(--g1);font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#tsts{font-size:10px;margin-left:4px}
#ta{margin-left:auto;display:flex;gap:5px}
#ta button{padding:2px 8px;font-size:9px}
#tb{height:200px;overflow-y:auto;padding:8px 14px;font-size:11px;line-height:1.55;transition:height .2s}
#tb.ex{height:400px}
#tb::-webkit-scrollbar{width:4px}
#tb::-webkit-scrollbar-thumb{background:var(--g5)}
.tl{white-space:pre-wrap;word-break:break-all}
.t-ok{color:var(--g1)}
.t-w{color:var(--yellow)}
.t-e{color:var(--red)}
.t-i{color:var(--blue)}
.t-d{color:var(--g5)}
.t-m{color:var(--mag)}
.tcur{display:inline-block;width:8px;height:12px;background:var(--g1);animation:cur 1s step-end infinite;vertical-align:text-bottom}
@keyframes cur{50%{opacity:0}}
</style>
</head>
<body>
<canvas id="mc"></canvas>
<div id="app">

<!-- Header -->
<div id="hdr">
  <div id="logo">DORK<span> EYE</span></div>
  <div class="vbadge">v5.0</div>
  <div class="pulse"></div>
  <div class="vbadge">WEB CONSOLE</div>
  <div id="hdr-r">
    <span id="aj-badge">⚡ <b id="ajc">0</b> RUNNING</span>
    <span id="sclock"></span>
  </div>
</div>

<div id="main">
<!-- Sidebar -->
<div id="sb">
  <div class="nav active" data-s="dashboard" onclick="nav(this)"><span>◈</span> Dashboard</div>
  <div class="nav" data-s="scan"      onclick="nav(this)"><span>◉</span> New Scan</div>
  <div class="nav" data-s="urltest"   onclick="nav(this)"><span>◎</span> URL Tester</div>
  <div class="nav" data-s="dorkgen"   onclick="nav(this)"><span>⊞</span> Dork Gen</div>
  <div class="nav" data-s="jobs"      onclick="nav(this)"><span>▣</span> Jobs <span class="nbadge" id="jnb">0</span></div>
  <div class="nav" data-s="results"   onclick="nav(this)"><span>◧</span> Results <span class="nbadge" id="rnb">0</span></div>
  <div id="sb-ft">DorkEye Web<br><b>127.0.0.1:{{ port }}</b></div>
</div>

<!-- Content -->
<div id="cnt">

<!-- ══ DASHBOARD ══ -->
<div class="sec active" id="sec-dashboard">
  <div class="phdr"><h1>[ DASHBOARD ]</h1><p>OSINT DORKING CONSOLE — LOCAL SESSION</p></div>
  <div class="cg">
    <div class="card"><div class="clbl">Active Jobs</div><div class="cval" id="dc-a">0</div><div class="csub">running</div></div>
    <div class="card"><div class="clbl">Total Jobs</div><div class="cval" id="dc-t">0</div><div class="csub">this session</div></div>
    <div class="card"><div class="clbl">Result Files</div><div class="cval" id="dc-f">0</div><div class="csub">in Dump/</div></div>
    <div class="card"><div class="clbl">Dump Size</div><div class="cval" id="dc-s" style="font-size:20px;margin-top:8px">—</div><div class="csub">disk usage</div></div>
  </div>
  <div class="qa">
    <div class="qab" onclick="nav(qs('[data-s=scan]'))"><div class="qai">🔍</div><div class="qal">New Scan</div></div>
    <div class="qab" onclick="nav(qs('[data-s=urltest]'))"><div class="qai">🎯</div><div class="qal">URL Test</div></div>
    <div class="qab" onclick="nav(qs('[data-s=dorkgen]'))"><div class="qai">⚙️</div><div class="qal">Dork Gen</div></div>
    <div class="qab" onclick="nav(qs('[data-s=scan]'));setTimeout(()=>{ctgl('s-db','dba');if(!on('t-db'))tog(qs('#t-db'))},120)"><div class="qai">🗄</div><div class="qal">DB Scan</div></div>
    <div class="qab" onclick="nav(qs('[data-s=results]'))"><div class="qai">📂</div><div class="qal">Results</div></div>
  </div>
  <div style="font-size:11px;color:var(--g3);letter-spacing:1.5px;margin-bottom:9px">RECENT JOBS</div>
  <table class="tbl"><thead><tr><th>ID</th><th>Label</th><th>Status</th><th>Started</th><th></th></tr></thead>
  <tbody id="djt"></tbody></table>
</div>

<!-- ══ NEW SCAN ══ -->
<div class="sec" id="sec-scan">
  <div class="phdr"><h1>[ NEW SCAN ]</h1><p>CONFIGURE AND LAUNCH A DORKING SESSION</p></div>

  <div class="fs">
    <div class="fst">◈ TARGET</div>
    <div class="fr">
      <div class="fg" style="grid-column:1/-1">
        <label>Dork string or path to .txt file with dorks (one per line)</label>
        <textarea id="s-dork" rows="3" placeholder="site:example.com filetype:pdf&#10;OR /path/to/dorks.txt"></textarea>
      </div>
    </div>
    <div class="fr">
      <div class="fg"><label>Max results per dork (-c)</label><input type="number" id="s-count" value="50" min="1" max="500"></div>
      <div class="fg"><label>Output file (-o) — default: auto .html</label><input type="text" id="s-output" placeholder="e.g. results.html or report.json"></div>
    </div>
  </div>

  <div class="fs">
    <div class="fst">◉ MODE &amp; OPTIONS</div>
    <div class="fr">
      <div class="fg"><label>Search mode (--mode)</label>
        <select id="s-mode"><option value="soft">soft — minimal dorks</option><option value="medium">medium — moderate</option><option value="aggressive" selected>aggressive — full</option></select>
      </div>
    </div>
    <div class="tr" style="margin-bottom:10px">
      <div class="tgl" id="t-st"  onclick="tog(this)"><div class="td"></div>Stealth</div>
      <div class="tgl" id="t-sq"  onclick="tog(this)"><div class="td"></div>SQLi Detection</div>
      <div class="tgl" id="t-xs"  onclick="tog(this)"><div class="td"></div>XSS Detection</div>
      <div class="tgl" id="t-na"  onclick="tog(this)"><div class="td"></div>Skip Analysis</div>
      <div class="tgl" id="t-nf"  onclick="tog(this)"><div class="td"></div>No Fingerprint</div>
    </div>
    <div class="fr">
      <div class="fg"><label>XSS type (--xss-type)</label>
        <select id="s-xst"><option value="all">all</option><option value="reflected">reflected</option><option value="stored">stored</option><option value="dom">dom</option></select>
      </div>
    </div>
  </div>

  <div class="fs">
    <div class="ctg" onclick="ctgl('s-dg','dga')"><span id="dga">▶</span> ⊞ DORK GENERATOR (--dg)</div>
    <div class="cb" id="s-dg">
      <div class="tr" style="margin-bottom:10px"><div class="tgl" id="t-dg" onclick="tog(this);loadSCats()"><div class="td"></div>Enable DorkGen</div></div>
      <div class="fr">
        <div class="fg"><label>Templates (--templates)</label>
          <select id="s-tpl" onchange="loadSCats()"><option value="">default</option><option value="all">all</option></select>
        </div>
        <div class="fg"><label>Category (--dg=CAT)</label><select id="s-dcat"><option value="all">all</option></select></div>
        <div class="fg"><label>Max combos (--dg-max)</label><input type="number" id="s-dgmax" value="800" min="10" max="10000"></div>
      </div>
    </div>
  </div>

  <div class="fs">
    <div class="ctg" onclick="ctgl('s-fl','fla')"><span id="fla">▶</span> ◧ FILTERS</div>
    <div class="cb" id="s-fl">
      <div class="fr">
        <div class="fg"><label>Blacklist — space-separated (--blacklist)</label><input type="text" id="s-bl" placeholder="ads.tracker.io bad.domain.com"></div>
        <div class="fg"><label>Whitelist — space-separated (--whitelist)</label><input type="text" id="s-wl" placeholder="target.com"></div>
      </div>
      <div class="fr">
        <div class="fg"><label>Config file (--config)</label><input type="text" id="s-cfg" placeholder="dorkeye_config.yaml"></div>
      </div>
    </div>
  </div>

  <div class="fs">
    <div class="ctg" onclick="ctgl('s-an','ana')"><span id="ana">▶</span> 🔬 ANALYSIS PIPELINE (--analyze)</div>
    <div class="cb" id="s-an">
      <div class="tr" style="margin-bottom:10px">
        <div class="tgl" id="t-an" onclick="tog(this)"><div class="td"></div>Enable Analyze</div>
        <div class="tgl" id="t-af" onclick="tog(this)"><div class="td"></div>Fetch Pages</div>
      </div>
      <div class="fr">
        <div class="fg"><label>Max fetch (--analyze-fetch-max)</label><input type="number" id="s-afm" value="20" min="1" max="200"></div>
        <div class="fg"><label>Report format (--analyze-fmt)</label>
          <select id="s-afmt"><option value="html">html</option><option value="md">markdown</option><option value="json">json</option><option value="txt">txt</option></select>
        </div>
        <div class="fg"><label>Analysis output (--analyze-out)</label><input type="text" id="s-ao" placeholder="auto-generated"></div>
      </div>
    </div>
  </div>

  <div class="fs">
    <div class="ctg" onclick="ctgl('s-cr','cra')"><span id="cra">▶</span> 🕸 ADAPTIVE CRAWL (--crawl)</div>
    <div class="cb" id="s-cr">
      <div class="tr" style="margin-bottom:10px">
        <div class="tgl" id="t-cr"  onclick="tog(this)"><div class="td"></div>Enable Crawl</div>
        <div class="tgl" id="t-crs" onclick="tog(this)"><div class="td"></div>Crawl Stealth</div>
        <div class="tgl" id="t-crr" onclick="tog(this)"><div class="td"></div>Crawl Report</div>
      </div>
      <div class="fr">
        <div class="fg"><label>Rounds (--crawl-rounds)</label><input type="number" id="s-crr" value="4" min="1" max="20"></div>
        <div class="fg"><label>Max results (--crawl-max)</label><input type="number" id="s-crm" value="300" min="10" max="5000"></div>
        <div class="fg"><label>Per dork (--crawl-per-dork)</label><input type="number" id="s-crp" value="20" min="1" max="100"></div>
        <div class="fg"><label>Crawl output (--crawl-out)</label><input type="text" id="s-cro" placeholder="auto-generated"></div>
      </div>
    </div>
  </div>

  <div class="fs">
    <div class="ctg" onclick="ctgl('s-db','dba')"><span id="dba">▶</span> 🗄 DB PORT SCAN (--dbscan)</div>
    <div class="cb" id="s-db">
      <div class="tr" style="margin-bottom:10px">
        <div class="tgl" id="t-db" onclick="tog(this)"><div class="td"></div>Enable DB Scan</div>
      </div>
      <div class="fr">
        <div class="fg"><label>Timeout sec (--dbscan-timeout)</label><input type="number" id="s-dbt" value="2.5" min="0.5" max="30" step="0.5"></div>
        <div class="fg"><label>Threads/host (--dbscan-threads)</label><input type="number" id="s-dbth" value="60" min="1" max="200"></div>
        <div class="fg"><label>Max hosts (--dbscan-max-hosts)</label><input type="number" id="s-dbmh" value="200" min="1" max="1000"></div>
      </div>
    </div>
  </div>

  <div class="btnr">
    <button class="btn pri" onclick="runScan()">▶ LAUNCH SCAN</button>
    <button class="btn" onclick="resetScan()">↺ RESET FORM</button>
  </div>
  <div id="scan-fb" style="margin-top:10px"></div>
</div>

<!-- ══ URL TESTER ══ -->
<div class="sec" id="sec-urltest">
  <div class="phdr"><h1>[ URL TESTER ]</h1><p>DIRECT VULNERABILITY TEST ON A SPECIFIC TARGET</p></div>
  <div class="fs">
    <div class="fst">◎ TARGET URL</div>
    <div class="fr">
      <div class="fg" style="grid-column:1/-1"><label>Target URL (-u)</label>
        <input type="text" id="u-url" placeholder="https://target.com/page.php?id=1">
      </div>
    </div>
    <div class="tr" style="margin-bottom:10px">
      <div class="tgl" id="t-usq" onclick="tog(this)"><div class="td"></div>SQLi Test</div>
      <div class="tgl" id="t-uxs" onclick="tog(this)"><div class="td"></div>XSS Test</div>
      <div class="tgl" id="t-ust" onclick="tog(this)"><div class="td"></div>Stealth</div>
    </div>
    <div class="fr">
      <div class="fg"><label>XSS type</label>
        <select id="u-xst"><option value="all">all</option><option value="reflected">reflected</option><option value="stored">stored</option><option value="dom">dom</option></select>
      </div>
      <div class="fg"><label>Output file (-o)</label><input type="text" id="u-out" placeholder="url_test.html"></div>
    </div>
  </div>
  <div class="btnr"><button class="btn pri" onclick="runURL()">▶ RUN TEST</button></div>
  <div id="url-fb" style="margin-top:10px"></div>
</div>

<!-- ══ DORK GENERATOR ══ -->
<div class="sec" id="sec-dorkgen">
  <div class="phdr"><h1>[ DORK GENERATOR ]</h1><p>PREVIEW AND EXPORT DORK COMBINATIONS WITHOUT RUNNING A SCAN</p></div>
  <div class="fs">
    <div class="fst">⊞ GENERATOR SETTINGS</div>
    <div class="fr">
      <div class="fg"><label>Templates</label><select id="dg-tpl" onchange="loadDGCats()"><option value="">default</option><option value="all">all</option></select></div>
      <div class="fg"><label>Category</label><select id="dg-cat"><option value="all">all</option></select></div>
      <div class="fg"><label>Mode</label><select id="dg-mode"><option value="soft">soft</option><option value="medium">medium</option><option value="aggressive">aggressive</option></select></div>
      <div class="fg"><label>Max combos</label><input type="number" id="dg-max" value="800" min="10" max="10000"></div>
    </div>
  </div>
  <div class="btnr" style="margin-bottom:12px">
    <button class="btn pri" onclick="previewDorks()">⊞ PREVIEW</button>
    <button class="btn blu" onclick="exportDorks()">↓ EXPORT TXT</button>
  </div>
  <div id="dg-stats" style="font-size:11px;color:var(--g3);margin-bottom:8px"></div>
  <div id="dgpl"></div>
</div>

<!-- ══ JOBS ══ -->
<div class="sec" id="sec-jobs">
  <div class="shr"><h1>[ JOBS ]</h1><button class="btn ml" onclick="refreshJobs()">↺ REFRESH</button></div>
  <table class="tbl">
    <thead><tr><th>ID</th><th>Label</th><th>Status</th><th>Started</th><th>Ended</th><th>Output</th><th>Actions</th></tr></thead>
    <tbody id="jbt"></tbody>
  </table>
</div>

<!-- ══ RESULTS ══ -->
<div class="sec" id="sec-results">
  <div class="shr"><h1>[ RESULTS ]</h1><button class="btn ml" onclick="refreshResults()">↺ REFRESH</button></div>
  <div id="rlist"></div>
</div>

</div><!-- /cnt -->
</div><!-- /main -->

<!-- Terminal bar -->
<div id="trm">
  <div id="th" onclick="termExpand()">
    <span style="color:var(--g5);font-size:10px">▌</span>
    <span style="letter-spacing:2px">TERMINAL</span>
    <span id="tjl" style="margin-left:8px"></span>
    <span id="tsts"></span>
    <div id="ta" onclick.stop="void(0)" style="display:flex;gap:5px">
      <button class="btn sm" onclick="copyTerm(event)">COPY</button>
      <button class="btn sm" onclick="clearTerm(event)">CLEAR</button>
      <button class="btn sm dan" id="kbtn" style="display:none" onclick="killJob(event)">KILL</button>
    </div>
  </div>
  <div id="tb">
    <div class="tl t-d">DorkEye Web Console — Ready.</div>
    <div class="tl t-d">Launch a scan or select a job to stream output here.</div>
    <span class="tcur"></span>
  </div>
</div>

</div><!-- /app -->
<script>
// ─────────────────────────────────────────
// Matrix rain
// ─────────────────────────────────────────
(()=>{
  const c=document.getElementById('mc');const ctx=c.getContext('2d');
  function rz(){c.width=innerWidth;c.height=innerHeight;}rz();addEventListener('resize',rz);
  const ch='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*()_=[]{}|;:<>?アイウエカキクケコ01';
  const fs=13;let cols=Math.floor(innerWidth/fs);let dr=Array(cols).fill(1);
  setInterval(()=>{
    ctx.fillStyle='rgba(0,0,0,0.055)';ctx.fillRect(0,0,c.width,c.height);
    ctx.fillStyle='#00ff41';ctx.font=fs+'px monospace';
    dr.forEach((y,i)=>{ctx.fillText(ch[Math.floor(Math.random()*ch.length)],i*fs,y*fs);if(y*fs>c.height&&Math.random()>.975)dr[i]=0;dr[i]++;});
  },42);
})();

// ─────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────
const qs=s=>document.querySelector(s);
const qsa=s=>document.querySelectorAll(s);
let _tgls={};
function tog(el){el.classList.toggle('on');_tgls[el.id]=el.classList.contains('on');}
function on(id){return !!_tgls[id];}
function ctgl(id,arrow){const b=qs('#'+id),a=qs('#'+arrow);b.classList.toggle('open');if(a)a.textContent=b.classList.contains('open')?'▼':'▶';}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function fb(id,msg,type){
  const el=qs('#'+id);if(!el)return;
  el.innerHTML=`<div class="alt ${type}">${msg}</div>`;
  setTimeout(()=>{if(el.innerHTML.includes(msg))el.innerHTML='';},4000);
}

// ─────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────
function nav(el){
  qsa('.nav').forEach(n=>n.classList.remove('active'));
  el.classList.add('active');
  const s=el.dataset.s;
  qsa('.sec').forEach(x=>x.classList.remove('active'));
  qs('#sec-'+s).classList.add('active');
  if(s==='jobs')refreshJobs();
  if(s==='results')refreshResults();
  if(s==='dorkgen')loadDGCats();
}

// ─────────────────────────────────────────
// Terminal
// ─────────────────────────────────────────
let _aJob=null,_es=null,_tex=false,_lts=0;

function colorLine(l){
  if(!l)return`<span class="tl t-d"> </span>`;
  let cls='t-ok';
  if(/\[!\]|VULNERABLE|CRITICAL|error/i.test(l))cls='t-e';
  else if(/\[~\]|WARNING|WAF|skipping/i.test(l))cls='t-w';
  else if(/\[✓\]|SAFE| saved |done|completed/i.test(l))cls='t-ok';
  else if(/\[\*\]|Searching|Analyz|Loading|Starting/i.test(l))cls='t-i';
  else if(/potential|found|vuln|payload/i.test(l))cls='t-e';
  else if(/\[ Open\s*\]/i.test(l))cls='t-ok';
  else if(/\[ Closed\s*\]/i.test(l))cls='t-e';
  else if(/DBScan|db.port|portscan/i.test(l))cls='t-i';
  else if(/^[─│╭╰└├┌╔╗╚╝║═]/u.test(l))cls='t-i';
  else if(/^[\s]*$/u.test(l))cls='t-d';
  const lnk=esc(l).replace(/(https?:\/\/[^\s<>"]+)/g,'<a href="$1" target="_blank" style="color:var(--blue)">$1</a>');
  return`<span class="tl ${cls}">${lnk}</span>`;
}

function appendLines(lines){
  const tb=qs('#tb');
  const atBottom=tb.scrollHeight-tb.scrollTop-tb.clientHeight<120;
  const cur=tb.querySelector('.tcur');if(cur)cur.remove();
  lines.forEach(({l})=>{const d=document.createElement('div');d.innerHTML=colorLine(l);tb.appendChild(d);});
  const c=document.createElement('span');c.className='tcur';tb.appendChild(c);
  if(atBottom)tb.scrollTop=tb.scrollHeight;
}

function clearTerm(e){if(e)e.stopPropagation();qs('#tb').innerHTML='<span class="tcur"></span>';_lts=0;}
function copyTerm(e){if(e)e.stopPropagation();navigator.clipboard.writeText(qs('#tb').innerText);}
function termExpand(){_tex=!_tex;qs('#tb').classList.toggle('ex',_tex);}

function attachJob(jid,lbl){
  _aJob=jid;_lts=0;clearTerm();
  qs('#tjl').textContent=lbl||jid;
  if(_es){_es.close();_es=null;}
  const es=new EventSource('/api/stream/'+jid);_es=es;
  es.onmessage=e=>{
    try{
      const d=JSON.parse(e.data);
      if(d.done){es.close();_es=null;updKill(jid);qs('#tsts').textContent='['+d.status+']';return;}
      if(d.lines&&d.lines.length){appendLines(d.lines);_lts=d.lines[d.lines.length-1].t||_lts;}
    }catch(_){}
  };
  es.onerror=()=>{es.close();_es=null;};
  updKill(jid);
}

function updKill(jid){
  const kb=qs('#kbtn');const j=_jobs[jid];
  kb.style.display=(j&&j.status==='running')?'':'none';
  kb._jid=jid;
}

function killJob(e){
  if(e)e.stopPropagation();
  const jid=qs('#kbtn')._jid||_aJob;if(!jid)return;
  fetch('/api/jobs/'+jid,{method:'DELETE'}).then(()=>{qs('#kbtn').style.display='none';appendLines([{t:Date.now()/1e3,l:'[~] Kill signal sent.'}]);});
}

// ─────────────────────────────────────────
// Jobs
// ─────────────────────────────────────────
let _jobs={};
function refreshJobs(){
  fetch('/api/jobs').then(r=>r.json()).then(jobs=>{
    _jobs={};jobs.forEach(j=>_jobs[j.id]=j);
    const active=jobs.filter(j=>j.status==='running').length;
    qs('#dc-a').textContent=active;qs('#dc-t').textContent=jobs.length;
    qs('#jnb').textContent=jobs.length;
    const ab=qs('#aj-badge');ab.classList.toggle('show',active>0);qs('#ajc').textContent=active;
    renderJobs(jobs);renderDashJobs(jobs.slice(0,6));
    if(_aJob&&_jobs[_aJob])updKill(_aJob);
  });
}

function renderJobs(jobs){
  const tb=qs('#jbt');
  if(!jobs.length){tb.innerHTML='<tr><td colspan="7" style="color:var(--g5);padding:14px">No jobs this session.</td></tr>';return;}
  tb.innerHTML=jobs.map(j=>`<tr>
    <td class="mono">${j.id}</td>
    <td class="uc" style="max-width:230px">${esc(j.label)}</td>
    <td><span class="badge ${j.status}" id="jb-${j.id}">${j.status}</span></td>
    <td class="mono">${j.started||''}</td>
    <td class="mono" style="color:var(--g5)">${j.ended||'—'}</td>
    <td class="mono" style="color:var(--g5);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(j.output_file)}">${esc(j.output_file)||'—'}</td>
    <td style="white-space:nowrap">
      <button class="btn sm" onclick="attachJob('${j.id}','${esc(j.label).replace(/'/g,"\\'")}')">TERM</button>
      ${j.output_file&&j.output_file.endsWith('.html')?`<a class="btn sm blu" href="/dump/${j.output_file}" target="_blank">VIEW</a>`:''}
      ${j.status==='running'?`<button class="btn sm dan" onclick="fetch('/api/jobs/${j.id}',{method:'DELETE'}).then(()=>refreshJobs())">KILL</button>`:''}
    </td>
  </tr>`).join('');
}

function renderDashJobs(jobs){
  const tb=qs('#djt');
  if(!jobs.length){tb.innerHTML='<tr><td colspan="5" style="color:var(--g5);padding:14px">No jobs yet. Launch a scan to begin.</td></tr>';return;}
  tb.innerHTML=jobs.map(j=>`<tr>
    <td class="mono">${j.id}</td>
    <td class="uc">${esc(j.label)}</td>
    <td><span class="badge ${j.status}">${j.status}</span></td>
    <td class="mono" style="color:var(--g3)">${j.started||''}</td>
    <td><button class="btn sm" onclick="attachJob('${j.id}','${esc(j.label).replace(/'/g,"\\'")}');nav(qs('[data-s=jobs]'))">TERM</button></td>
  </tr>`).join('');
}

// ─────────────────────────────────────────
// Results
// ─────────────────────────────────────────
function refreshResults(){
  fetch('/api/dump').then(r=>r.json()).then(d=>{
    qs('#dc-f').textContent=d.files.length;
    qs('#dc-s').textContent=d.total_size_str;
    qs('#rnb').textContent=d.files.length;
    const el=qs('#rlist');
    if(!d.files.length){el.innerHTML='<div style="color:var(--g5);padding:14px;font-size:11px">No result files found in Dump/.</div>';return;}
    el.innerHTML=d.files.map(f=>`<div class="fi">
      <span style="font-size:14px;color:var(--g4)">${f.name.endsWith('.html')?'📄':f.name.endsWith('.json')?'📋':'📁'}</span>
      <span class="fn" onclick="openR('${f.name}')">${esc(f.name)}</span>
      <span class="fsz">${f.size_str}</span>
      <span class="fdt">${f.mtime}</span>
      <button class="btn sm" onclick="fileMode('${f.name}')">FILE MODE</button>
      <a class="btn sm blu" href="/dump/${f.name}" download>↓ DL</a>
      ${f.name.endsWith('.html')?`<a class="btn sm" href="/dump/${f.name}" target="_blank">OPEN</a>`:''}
    </div>`).join('');
  });
}

function openR(f){if(f.endsWith('.html'))window.open('/dump/'+f,'_blank');}
function fileMode(f){
  fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'file',file:'Dump/'+f})})
  .then(r=>r.json()).then(d=>{if(d.job_id){attachJob(d.job_id,'FileMode: '+f);nav(qs('[data-s=jobs]'));refreshJobs();}});
}

// ─────────────────────────────────────────
// Scan
// ─────────────────────────────────────────
function runScan(){
  const dork=qs('#s-dork').value.trim();
  if(!dork&&!on('t-dg')){fb('scan-fb','Enter a dork string or enable DorkGen.','warn');return;}
  const p={
    type:'scan',dork:dork,
    count:+qs('#s-count').value||50,
    output:qs('#s-output').value.trim(),
    mode:qs('#s-mode').value,
    stealth:on('t-st'),sqli:on('t-sq'),xss:on('t-xs'),
    xss_type:qs('#s-xst').value,
    no_analyze:on('t-na'),no_fingerprint:on('t-nf'),
    blacklist:qs('#s-bl').value.trim(),whitelist:qs('#s-wl').value.trim(),
    config:qs('#s-cfg').value.trim(),
    dg:on('t-dg'),dg_cat:qs('#s-dcat').value,
    dg_max:+qs('#s-dgmax').value||800,
    templates:qs('#s-tpl').value,
    analyze:on('t-an'),analyze_fetch:on('t-af'),
    analyze_fetch_max:+qs('#s-afm').value||20,
    analyze_fmt:qs('#s-afmt').value,
    analyze_out:qs('#s-ao').value.trim(),
    crawl:on('t-cr'),crawl_rounds:+qs('#s-crr').value||4,
    crawl_max:+qs('#s-crm').value||300,
    crawl_per_dork:+qs('#s-crp').value||20,
    crawl_stealth:on('t-crs'),crawl_report:on('t-crr'),
    crawl_out:qs('#s-cro').value.trim(),
    dbscan:on('t-db'),
    dbscan_timeout:+qs('#s-dbt').value||2.5,
    dbscan_threads:+qs('#s-dbth').value||60,
    dbscan_max_hosts:+qs('#s-dbmh').value||200,
  };
  post('/api/run',p,(d)=>{
    if(d.job_id){attachJob(d.job_id,d.label);fb('scan-fb','Job '+d.job_id+' started!','ok');setTimeout(()=>{nav(qs('[data-s=jobs]'));refreshJobs();},250);}
    else fb('scan-fb',d.error||'Error launching job.','err');
  });
}

function runURL(){
  const url=qs('#u-url').value.trim();
  if(!url){fb('url-fb','Enter a URL.','warn');return;}
  const p={type:'urltest',url,sqli:on('t-usq'),xss:on('t-uxs'),xss_type:qs('#u-xst').value,stealth:on('t-ust'),output:qs('#u-out').value.trim()};
  post('/api/run',p,(d)=>{
    if(d.job_id){attachJob(d.job_id,d.label);fb('url-fb','Job '+d.job_id+' started!','ok');setTimeout(()=>{nav(qs('[data-s=jobs]'));refreshJobs();},250);}
    else fb('url-fb',d.error||'Error.','err');
  });
}

function resetScan(){
  qs('#s-dork').value='';qs('#s-count').value=50;qs('#s-output').value='';
  qsa('.tgl.on').forEach(t=>{t.classList.remove('on');_tgls[t.id]=false;});
}

// ─────────────────────────────────────────
// Dork Gen
// ─────────────────────────────────────────
function loadDGCats(){
  const tpl=qs('#dg-tpl').value;
  fetch('/api/templates/categories?tpl='+encodeURIComponent(tpl)).then(r=>r.json()).then(d=>{
    const sel=qs('#dg-cat');const cur=sel.value;
    sel.innerHTML='<option value="all">all</option>'+d.categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
    if(d.categories.includes(cur))sel.value=cur;
  });
}

function loadSCats(){
  const tpl=qs('#s-tpl').value;
  fetch('/api/templates/categories?tpl='+encodeURIComponent(tpl)).then(r=>r.json()).then(d=>{
    const sel=qs('#s-dcat');const cur=sel.value;
    sel.innerHTML='<option value="all">all</option>'+d.categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
    if(d.categories.includes(cur))sel.value=cur;
  });
}

function previewDorks(){
  const p={templates:qs('#dg-tpl').value,category:qs('#dg-cat').value,mode:qs('#dg-mode').value,max:+qs('#dg-max').value||800};
  qs('#dgpl').innerHTML='<div class="t-d" style="padding:8px">Generating...</div>';
  qs('#dg-stats').textContent='';
  post('/api/dorkgen/preview',p,(d)=>{
    // FIX: controlla error PRIMA di controllare dorks (array vuoto e' truthy in JS)
    if(d.error){
      qs('#dg-stats').textContent='';
      qs('#dgpl').innerHTML=`<div class="t-e" style="padding:8px;line-height:1.6">
        <b style="color:var(--red)">! Errore generazione dork</b><br><br>${esc(d.error)}
        <br><br><span style="color:var(--g5);font-size:10px">Verifica che la cartella Templates/ esista nella root del progetto e contenga file .yaml</span>
      </div>`;
      return;
    }
    if(!d.dorks||d.dorks.length===0){
      qs('#dg-stats').textContent='Generated: 0 dorks';
      qs('#dgpl').innerHTML=`<div class="t-w" style="padding:8px;line-height:1.6">
        <b>Nessun dork generato.</b><br>
        Template caricati: ${esc((d.loaded||[]).join(', ')||'nessuno')}<br>
        Prova a cambiare mode (soft/medium/aggressive) o seleziona una categoria diversa.
      </div>`;
      return;
    }
    let stats='Generated: '+d.count+' dorks | mode: '+p.mode+(d.count>200?' — showing first 200':'');
    if(d.warning)stats+=' | '+d.warning;
    qs('#dg-stats').textContent=stats;
    qs('#dgpl').innerHTML=d.dorks.slice(0,200).map(dk=>`<div class="de">${esc(dk)}</div>`).join('');
  });
}

function exportDorks(){
  const p={templates:qs('#dg-tpl').value,category:qs('#dg-cat').value,mode:qs('#dg-mode').value,max:+qs('#dg-max').value||800};
  fetch('/api/dorkgen/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})
  .then(r=>r.blob()).then(b=>{const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='dorkeye_dorks.txt';a.click();});
}

// ─────────────────────────────────────────
// Generic POST
// ─────────────────────────────────────────
function post(url,data,cb){
  fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
  .then(r=>r.json()).then(cb).catch(e=>console.error(e));
}

// ─────────────────────────────────────────
// Polling / Init
// ─────────────────────────────────────────
function tick(){qs('#sclock').textContent=new Date().toLocaleTimeString('en-GB');}
setInterval(tick,1000);tick();

function poll(){
  refreshJobs();
  fetch('/api/dump').then(r=>r.json()).then(d=>{
    qs('#dc-f').textContent=d.files.length;
    qs('#dc-s').textContent=d.total_size_str;
    qs('#rnb').textContent=d.files.length;
  });
}
setInterval(poll,5000);

// Load template list and categories on boot
fetch('/api/templates/list').then(r=>r.json()).then(d=>{
  const extra=d.files.map(f=>`<option value="${esc(f)}">${esc(f)}</option>`).join('');
  ['s-tpl','dg-tpl'].forEach(id=>{
    const sel=qs('#'+id);if(!sel)return;
    sel.innerHTML='<option value="">default</option><option value="all">all</option>'+extra;
  });
  loadSCats();loadDGCats();
});

poll();
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  Launcher
# ══════════════════════════════════════════════════════════════════════════════

def launch_web(start_port: int = 8080, no_browser: bool = False) -> None:
    """Start the DorkEye web dashboard and open the browser."""
    if not _FLASK:
        print(
            '\n[!] Flask is not installed.\n'
            '    Run:  pip install flask\n'
            '    Then: python dorkeye.py --ui\n'
        )
        sys.exit(1)

    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    port = find_free_port(start_port)
    app  = create_app(port)
    url  = f'http://127.0.0.1:{port}'

    print(f'\n  ██████╗  ██████╗ ██████╗ ██╗  ██╗███████╗██╗   ██╗███████╗')
    print(f'  ██╔══██╗██╔═══██╗██╔══██╗██║ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝')
    print(f'  ██║  ██║██║   ██║██████╔╝█████╔╝ █████╗   ╚████╔╝ █████╗  ')
    print(f'  ██║  ██║██║   ██║██╔══██╗██╔═██╗ ██╔══╝    ╚██╔╝  ██╔══╝  ')
    print(f'  ██████╔╝╚██████╔╝██║  ██║██║  ██╗███████╗   ██║   ███████╗')
    print(f'  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝')
    print(f'\n  [ WEB CONSOLE ]  v4.9\n')
    print(f'  ▸ URL     →  {url}')
    print(f'  ▸ Port    →  {port}{"  (auto-selected)" if port != start_port else ""}')
    print(f'  ▸ Root    →  {ROOT}')
    print(f'  ▸ Dump    →  {DUMP_DIR}')
    print(f'\n  Press Ctrl+C to stop the server.\n')

    if not no_browser:
        def _open():
            time.sleep(1.1)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    # ── Ripristina il handler SIGINT di default prima di avviare Flask.
    # dorkeyes.py installa un handler custom (skip/exit) che intercetta
    # Ctrl+C senza propagare KeyboardInterrupt → Werkzeug non riceve
    # mai il segnale di shutdown e la porta rimane appesa.
    import signal as _sig
    _sig.signal(_sig.SIGINT, _sig.SIG_DFL)

    # ── Usa make_server invece di app.run() per poter impostare
    # SO_REUSEADDR direttamente sul socket del server Flask,
    # garantendo il rilascio immediato della porta anche dopo un
    # kill forzato (TIME_WAIT).
    try:
        from werkzeug.serving import make_server as _make_server
    except ImportError:
        # Fallback: werkzeug non disponibile separatamente, usa app.run()
        try:
            app.run(
                host='127.0.0.1',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True,
            )
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            print('\n  [!] Server stopped. Port released.\n')
            sys.exit(0)

    srv = _make_server('127.0.0.1', port, app, threaded=True)
    srv.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        srv.server_close()
        print('\n  [!] Server stopped. Port released.\n')
        sys.exit(0)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='DorkEye Web Dashboard')
    p.add_argument('--port',       type=int, default=8080)
    p.add_argument('--no-browser', action='store_true')
    a = p.parse_args()
    launch_web(start_port=a.port, no_browser=a.no_browser)
