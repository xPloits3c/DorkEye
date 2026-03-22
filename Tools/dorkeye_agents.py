"""
DorkEye Agents v3.0
====================
Pipeline di analisi post-ricerca per DorkEye v4.8+

Gli agenti vengono invocati DOPO che DorkEye ha completato la ricerca.
Non interferiscono con il flusso di ricerca — lavorano sui risultati gia' raccolti.

Pipeline (attivata con --analyze):
  1. TriageAgent          — classifica i risultati per priorità OSINT (+ bonus sqli/accessible)
  2. PageFetchAgent       — scarica pagine HIGH/CRITICAL (retry, UA rotation, salva headers)
  3. HeaderIntelAgent     — analizza response headers: info leak, security header mancanti
  4. TechFingerprintAgent — rileva CMS, framework, versioni JS/server dai contenuti
  5. SecretsAgent         — regex su secrets/credenziali + hash detection + severity
  6. PiiDetectorAgent     — rileva PII: email, phone, IBAN, CF, CC, SSN, DOB
  7. EmailHarvesterAgent  — raccoglie e categorizza email da tutti i risultati
  8. SubdomainHarvesterAgent — estrae subdomini e produce dork per DorkCrawler
  9. ReportAgent          — report HTML/MD/JSON con tutte le sezioni nuove
 10. DorkCrawlerAgent     — crawl ricorsivo adattivo (alimentato da TechFP + SubHarvest)

Uso CLI:
    python dorkeye.py --dg=all --analyze -o risultati.json
    python dorkeye.py -d dorks.txt --analyze --analyze-fetch --analyze-fmt=html

Uso standalone (da results file):
    python dorkeye_agents.py results.json --analyze-fmt=html --analyze-out=report.html

Autore: DorkEye Project
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from html.parser import HTMLParser as _HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

# ── Rich console ──────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.table   import Table
    _console = Console()

    def _log(msg: str, style: str = "cyan") -> None:
        _console.print(f"[{style}]{msg}[/{style}]")

    def _panel(body: str, title: str = "", border: str = "cyan") -> None:
        _console.print(Panel(body, title=title, border_style=border))

except ImportError:
    _console = None  # type: ignore

    def _log(msg: str, style: str = "") -> None:  # type: ignore
        print(msg)

    def _panel(body: str, title: str = "", border: str = "") -> None:  # type: ignore
        print(f"\n[{title}]\n{body}")


# ══════════════════════════════════════════════════════════════════════════════
#  PATTERN LIBRARY — importata da dorkeye_patterns.py
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
#  BASE AGENT
# ══════════════════════════════════════════════════════════════════════════════

def _safe_json_local(raw: str, expected_type: type = dict):
    """
    Parser JSON robusto — standalone, nessuna dipendenza esterna.
    Gestisce: markdown fences, trailing commas, testo extra attorno al JSON.
    """
    import re as _re
    text = _re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    text = _re.sub(r",\s*([}\]])", r"\1", text)

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


class BaseAgent(ABC):
    """
    Classe base per tutti gli agenti DorkEye.
    Funziona senza LLM (plugin=None) — gli agenti usano regex di default.
    Se plugin e' fornito, i passi LLM vengono attivati come enhancement.
    """

    def __init__(self, plugin=None, name: str = "Agent"):
        self.plugin = plugin   # None = modalita' autonoma (no LLM)
        self.name   = name

    def _call_llm(self, prompt: str, max_tokens: int = 700) -> str:
        """Chiama l'LLM se disponibile, altrimenti solleva RuntimeError."""
        if not self.plugin:
            raise RuntimeError(f"[{self.name}] LLM non disponibile — usa modalita' regex")
        return self.plugin._call(
            prompt,
            max_tokens=max_tokens,
            cache=True,
            mem_user=f"[{self.name}] {prompt[:100]}",
        )

    @property
    def has_llm(self) -> bool:
        """True se il plugin LLM e' attivo e disponibile."""
        return self.plugin is not None

    def _safe_json(self, raw: str, expected_type: type = dict):
        """Parser JSON robusto — non dipende da dorkeye_llm_plugin."""
        return _safe_json_local(raw, expected_type=expected_type)

    @staticmethod
    def _label(score: int) -> str:
        """Delega a dorkeye_patterns.label_from_score() — unica source of truth."""
        return label_from_score(score)

    @abstractmethod
    def run(self, *args, **kwargs):
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  TRIAGE AGENT
# ══════════════════════════════════════════════════════════════════════════════

class TriageAgent(BaseAgent):
    """
    Classifica ogni risultato per priorita' OSINT.

    Step 1 — Regex pre-scoring (sempre, senza LLM): 0-50 punti
    Step 2 — LLM scoring (opzionale, batch_size risultati per volta): 0-100 punti
    Score finale = max(regex*2, llm_score)

    Aggiunge a ogni result: triage_score (0-100), triage_label, triage_reason.
    Ordina per score decrescente.
    """

    def __init__(self, plugin=None, batch_size: int = 15):
        super().__init__(plugin, name="TriageAgent")
        self.batch_size = batch_size

    def run(self, results: List[dict], use_llm: bool = True) -> List[dict]:
        if not results:
            return results

        _log(
            f"[{self.name}] Triage {len(results)} risultati "
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

        # Calcola score finale e pulisci campi temporanei
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
            "Sei un analista OSINT. Assegna uno score OSINT 0-100 a ogni risultato.\n\n"
            "CRITERI:\n"
            "  90-100 CRITICAL — credenziali, DB admin, shell, config esposti\n"
            "  70-89  HIGH     — pannelli admin, .env, .git, backup, file config\n"
            "  50-69  MEDIUM   — directory listing, CMS vulnerabili, login page interessante\n"
            "  20-49  LOW      — login standard, pagine generiche\n"
            "   0-19  SKIP     — irrilevante\n\n"
            f"RISULTATI:\n" + "\n".join(lines) + "\n\n"
            "Rispondi SOLO con JSON array (un elemento per risultato, stesso ordine):\n"
            '[{"id":0,"score":85,"label":"HIGH","reason":"pannello phpMyAdmin esposto"},...]\n###'
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
            _log(f"[{self.name}] LLM batch {b_idx} fallito: {e}", style="yellow")

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

        # ── Bonus runtime da dati già presenti nel result (v4.8) ──────────────
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

        # Numero parametri GET — più parametri = superficie maggiore
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


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE FETCH AGENT
# ══════════════════════════════════════════════════════════════════════════════

class _ScriptStyleStripper(_HTMLParser):
    """HTMLParser che rimuove blocchi <script> e <style> in modo sicuro.

    Sostituisce la regex bypassabile (CWE-20/116/185/186) con il parser
    built-in che gestisce correttamente tutte le varianti sintatticamente
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


# Fallback regex — usato SOLO se HTMLParser lancia eccezione su HTML
# gravemente malformato. Non è il percorso principale.
#
# FIX CWE-20/116/185/186 ("Bad HTML filtering regexp"):
#   - Apertura : `(?:[^>]*)` invariato (gestisce attributi senza `>` non quotato)
#   - Chiusura : sostituito `\s*>` con `[^>]*>` per coprire varianti browser-accettate
#               come `</script anything>` o `</  script  foo>` (spazi dopo `</`
#               gestiti da `\s*` aggiunto prima del nome tag).
# Questo percorso è intenzionalmente un last-resort: il path primario usa
# _ScriptStyleStripper (HTMLParser built-in) che è immune a queste varianti.
_SCRIPT_STYLE_RE_FALLBACK = re.compile(  # noqa: S608
    r"<(?:script|style)(?:[^>]*)>[\s\S]*?</\s*(?:script|style)[^>]*>",
    re.IGNORECASE,
)


def _strip_page_content(text: str) -> str:
    """Rimuove tag script/style con HTMLParser, poi ripulisce i restanti tag HTML."""
    stripper = _ScriptStyleStripper()
    try:
        stripper.feed(text)
        stripper.close()
        text = stripper.get_result()
    except Exception:
        text = _SCRIPT_STYLE_RE_FALLBACK.sub(" ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s{3,}", "\n", text).strip()
    return text


# Alias locali per compatibilità con i riferimenti esistenti nel codice
_FETCH_UA        = _FETCH_UA_SHARED
_SKIP_EXTENSIONS = _SKIP_EXTENSIONS_SHARED


class PageFetchAgent(BaseAgent):
    """
    Scarica il contenuto HTML reale delle pagine HIGH e CRITICAL.

    Invece di analizzare gli snippet DDG (100-200 caratteri, spesso inutili),
    questo agente scarica l'HTML/testo reale della pagina per dare al
    SecretsAgent materiale concreto su cui lavorare.

    Aggiunge 'page_content' (str) a ogni risultato processato.
    Rispetta il rate limiting con un piccolo delay tra le fetch.
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
        Scarica il contenuto delle pagine prioritarie.
        Modifica i result in-place aggiungendo 'page_content'.
        Restituisce la lista aggiornata.
        """
        _label_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "SKIP": 0}
        min_rank    = _label_rank.get(self.min_label.upper(), 3)

        targets = [
            r for r in results
            if _label_rank.get(r.get("triage_label", "LOW"), 1) >= min_rank
            and "page_content" not in r
        ][:self.max_pages]

        if not targets:
            _log(f"[{self.name}] Nessuna pagina da scaricare (min_label={self.min_label}).", style="dim")
            return results

        _log(
            f"[{self.name}] Fetch {len(targets)} pagine "
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
            # v4.8 — salva headers grezzi per HeaderIntelAgent
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
            f"[{self.name}] Completato: {ok_count}/{len(targets)} pagine scaricate.",
            style="green"
        )
        return results

    def _fetch(self, url: str) -> str:
        """Scarica e restituisce il testo della pagina (troncato a max_chars).
        v4.8: retry max 2, UA rotation, salva response_headers nel result.
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

                # Salva gli header grezzi nel _fetch_meta (verrà usato da HeaderIntelAgent)
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

        _log(f"[{self.name}] Fetch fallito dopo 3 tentativi: {url[:60]} — {last_exc}", style="dim")
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  SECRETS AGENT
# ══════════════════════════════════════════════════════════════════════════════

# _censor importata come _censor_shared da dorkeye_patterns — alias locale
def _censor(value: str, visible: int = 4) -> str:
    return _censor_shared(value, show=visible)


class SecretsAgent(BaseAgent):
    """
    Analizza il contenuto reale delle pagine (page_content) alla ricerca
    di credenziali, chiavi API, connessioni DB, e altri dati sensibili.

    Lavora in due fasi:
      1. Regex scan (veloce, senza LLM) — trova pattern noti con certezza alta
      2. LLM scan (opzionale) — analisi contestuale per pattern ambigui o nascosti

    Priorita' del contenuto analizzato:
      page_content (contenuto reale scaricato) > snippet (DDG snippet)

    Aggiunge 'secrets' (lista) a ogni risultato con findings.
    """

    def __init__(self, plugin=None, use_llm: bool = True, max_content: int = 6000):
        super().__init__(plugin, name="SecretsAgent")
        self.use_llm     = use_llm and plugin is not None
        self.max_content = max_content

    def run(self, results: List[dict]) -> List[dict]:
        """
        Scansiona tutti i risultati che hanno contenuto disponibile.
        Restituisce la lista con 'secrets' popolato.
        """
        # Lavora solo su risultati con contenuto (page_content o snippet non vuoto)
        candidates = [
            r for r in results
            if (r.get("page_content") or r.get("snippet"))
            and r.get("triage_label", "SKIP") != "SKIP"
        ]

        if not candidates:
            _log(f"[{self.name}] Nessun contenuto disponibile da scansionare.", style="dim")
            return results

        _log(
            f"[{self.name}] Secrets scan su {len(candidates)} risultati "
            f"(LLM: {'on' if self.use_llm else 'off'})...",
            style="bold cyan"
        )

        total_found = 0
        for r in candidates:
            # Preferisci il contenuto reale della pagina
            content = r.get("page_content") or r.get("snippet") or ""
            content = content[:self.max_content]
            url     = r.get("url", "")

            findings: List[dict] = []

            # Fase 1: regex scan
            regex_hits = self._regex_scan(content, url)
            findings.extend(regex_hits)

            # Fase 2: LLM scan (solo se LLM attivo e contenuto abbastanza ricco)
            if self.use_llm and len(content) > 100:
                llm_hits = self._llm_scan(content, url)
                # Aggiungi solo nuovi findings non gia' trovati dalla regex
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
            f"[{self.name}] Scan completato: {total_found} segreti totali trovati.",
            style="bold green" if total_found == 0 else "bold red"
        )
        return results

    def _regex_scan(self, content: str, url: str) -> List[dict]:
        findings = []
        # Dedup per valore normalizzato (evita duplicati stessa chiave ripetuta)
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

                # Contesto: 70 caratteri prima e dopo il match
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
            "Sei un esperto di sicurezza. Analizza questo testo e trova TUTTI i segreti o dati sensibili.\n\n"
            f"SORGENTE: {url}\n"
            f"CONTENUTO:\n{content[:3000]}\n\n"
            "Cerca: API key, token, password, hash, JWT, connessioni DB, credenziali cloud, chiavi SSH.\n"
            "Rispondi SOLO con JSON array (vuoto [] se nulla trovato):\n"
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
                    # Aggiungi severity se non presente
                    if "severity" not in item:
                        item["severity"] = _SECRET_SEVERITY.get(
                            item.get("type", ""), "MEDIUM"
                        )
                    results.append(item)
            return results
        except Exception as e:
            _log(f"[{self.name}] LLM scan error ({url[:50]}): {e}", style="yellow")
            return []


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT AGENT
# ══════════════════════════════════════════════════════════════════════════════

class ReportAgent(BaseAgent):
    """
    Genera il report finale della sessione di analisi.

    Input: risultati triaggiati con secrets, analisi LLM opzionale
    Output: file HTML (dark theme), Markdown, o JSON
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
        Genera il report nel formato richiesto.

        Args:
            results:     risultati triaggiati (con secrets, pii, email, ecc.)
            analysis:    dict da llm_plugin.analyze_results() (opzionale)
            target:      descrizione del target originale
            output_path: path di salvataggio (None = non salva)
            fmt:         "html" | "md" | "json"
            extra:       dict con emails, pii, subdomains, cve_dorks (v3.0)

        Returns:
            Stringa del report nel formato richiesto.
        """
        _log(f"[{self.name}] Generazione report (fmt={fmt})...", style="bold cyan")

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
                _log(f"[{self.name}] Report salvato: {output_path}", style="bold green")
            except IOError as e:
                _log(f"[{self.name}] Errore salvataggio: {e}", style="red")

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

        lines = [
            "# DorkEye Analysis Report",
            f"\n> {now}  |  Target: `{target or 'N/A'}`  |  DorkEye v4.8 + Agents v3.0\n",
            "---\n",
            "## Summary\n",
            analysis.get("summary", "_Nessuna analisi LLM disponibile._"),
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
        lines.append(f"\n\n---\n*DorkEye v4.8 + Agents v3.0 — {now}*")
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

        def section(title, content, show=True):
            if not show:
                return ""
            return f"<h2>{title}</h2><div class='card'>{content}</div>"

        return f"""<!DOCTYPE html>
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
<div class="meta">Generated: {now} &nbsp;|&nbsp; Target: <code>{target or 'N/A'}</code> &nbsp;|&nbsp; DorkEye v4.8 + Agents v3.0</div>
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
<footer>DorkEye v4.8 + Agents v3.0 &mdash; {now}</footer>
</body></html>"""

    def _json(self, results, analysis, secrets, counts, target, extra=None) -> str:
        extra = extra or {}
        return json.dumps({
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "target":       target or "",
                "engine":       "DorkEye v4.8 + Agents v3.0",
            },
            "metrics": {
                "total":     len(results),
                "by_label":  counts,
                "secrets":   len(secrets),
                "pii":       len(extra.get("pii", [])),
                "emails":    len(extra.get("emails", [])),
                "subdomains": sum(len(v) for v in extra.get("subdomains", {}).values()),
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


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER INTEL AGENT (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

# Security headers che dovrebbero essere presenti
_SECURITY_HEADERS_REQUIRED = {
    "strict-transport-security": "HSTS absent — MITM risk",
    "content-security-policy":   "CSP absent — XSS risk",
    "x-frame-options":           "Clickjacking protection absent",
    "x-content-type-options":    "MIME sniffing protection absent",
    "referrer-policy":           "Referrer-Policy absent",
    "permissions-policy":        "Permissions-Policy absent",
}

# Header che rivelano informazioni sul server/tecnologia
_INFO_LEAK_HEADERS = [
    "server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version",
    "x-generator", "x-drupal-cache", "x-wordpress-cache",
    "x-runtime", "x-rack-cache", "via",
]

# Pattern per versioni obsolete nei header
_OUTDATED_VERSION_RE = re.compile(
    r"(?:apache|nginx|php|openssl|iis|tomcat|jetty|lighttpd)[/\s]"
    r"(\d+\.\d+(?:\.\d+)?)",
    re.I,
)


class HeaderIntelAgent(BaseAgent):
    """
    Analizza i response headers HTTP salvati da PageFetchAgent.

    Per ogni result con 'response_headers' rileva:
      - Info leak: Server, X-Powered-By, versioni software
      - Security headers mancanti: HSTS, CSP, X-Frame-Options, ecc.
      - Versioni obsolete nel valore degli header

    Aggiunge 'header_intel' (dict) a ogni result processato.
    Non esegue richieste HTTP — lavora sui dati già presenti.
    """

    def __init__(self, plugin=None):
        super().__init__(plugin, name="HeaderIntelAgent")

    def run(self, results: List[dict]) -> List[dict]:
        candidates = [r for r in results if r.get("response_headers")]
        if not candidates:
            _log(f"[{self.name}] Nessun header disponibile — esegui con --analyze-fetch.", style="dim")
            return results

        _log(f"[{self.name}] Analisi headers per {len(candidates)} risultati...", style="bold cyan")

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

        _log(f"[{self.name}] Completato: {total_findings} finding(s) header totali.", style="bold green")
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


# ══════════════════════════════════════════════════════════════════════════════
#  TECH FINGERPRINT AGENT (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

# Signatures tecnologie: (pattern, tech_name, category)
_TECH_SIGNATURES: List[Tuple[re.Pattern, str, str]] = [
    # CMS
    (re.compile(r"wp-content|wp-json|wordpress",               re.I), "WordPress",    "cms"),
    (re.compile(r"joomla|option=com_",                         re.I), "Joomla",       "cms"),
    (re.compile(r"drupal|sites/default",                       re.I), "Drupal",       "cms"),
    (re.compile(r"magento|mage/|varien/",                      re.I), "Magento",      "cms"),
    (re.compile(r"prestashop|modules/paypal",                  re.I), "PrestaShop",   "cms"),
    (re.compile(r"typo3|fileadmin/",                           re.I), "TYPO3",        "cms"),
    (re.compile(r"shopify",                                    re.I), "Shopify",      "cms"),
    (re.compile(r"wix\.com|wixstatic",                         re.I), "Wix",          "cms"),
    # Framework
    (re.compile(r"laravel|artisan|eloquent",                   re.I), "Laravel",      "framework"),
    (re.compile(r"django|wsgi\.py|manage\.py",                 re.I), "Django",       "framework"),
    (re.compile(r"rails|ruby on rails|action_controller",      re.I), "Rails",        "framework"),
    (re.compile(r"flask|werkzeug",                             re.I), "Flask",        "framework"),
    (re.compile(r"express\.js|expressjs",                      re.I), "Express.js",   "framework"),
    (re.compile(r"next\.js|_next/static",                      re.I), "Next.js",      "framework"),
    (re.compile(r"nuxt|nuxtjs",                                re.I), "Nuxt.js",      "framework"),
    # JS Libraries (con versione)
    (re.compile(r"jquery[/-](\d+\.\d+\.\d+)",                  re.I), "jQuery",       "js_lib"),
    (re.compile(r"react(?:\.min)?\.js|react-dom",              re.I), "React",        "js_lib"),
    (re.compile(r"vue(?:\.min)?\.js|vue@\d",                   re.I), "Vue.js",       "js_lib"),
    (re.compile(r"angular(?:\.min)?\.js|angular/core",         re.I), "Angular",      "js_lib"),
    (re.compile(r"bootstrap[/-](\d+\.\d+\.\d+)",               re.I), "Bootstrap",    "js_lib"),
    # Server / infra
    (re.compile(r"apache[/ ](\d+\.\d+)",                       re.I), "Apache",       "server"),
    (re.compile(r"nginx[/ ](\d+\.\d+)",                        re.I), "Nginx",        "server"),
    (re.compile(r"microsoft-iis[/ ](\d+\.\d+)",                re.I), "IIS",          "server"),
    (re.compile(r"openssl[/ ](\d+\.\d+)",                      re.I), "OpenSSL",      "server"),
    (re.compile(r"php[/ ](\d+\.\d+)",                          re.I), "PHP",          "lang"),
    (re.compile(r"python[/ ](\d+\.\d+)",                       re.I), "Python",       "lang"),
    (re.compile(r"node\.js[/ ](\d+\.\d+)",                     re.I), "Node.js",      "lang"),
    # DevOps / infra
    (re.compile(r"jenkins|hudson",                             re.I), "Jenkins",      "devops"),
    (re.compile(r"gitlab",                                     re.I), "GitLab",       "devops"),
    (re.compile(r"kibana",                                     re.I), "Kibana",       "devops"),
    (re.compile(r"grafana",                                    re.I), "Grafana",      "devops"),
    (re.compile(r"docker|dockerfile",                          re.I), "Docker",       "devops"),
    (re.compile(r"kubernetes|k8s",                             re.I), "Kubernetes",   "devops"),
    (re.compile(r"elasticsearch",                              re.I), "Elasticsearch","devops"),
    # DB panels
    (re.compile(r"phpmyadmin|pma_",                            re.I), "phpMyAdmin",   "db_panel"),
    (re.compile(r"adminer\.php|adminer/",                      re.I), "Adminer",      "db_panel"),
    (re.compile(r"pgadmin",                                    re.I), "pgAdmin",      "db_panel"),
]

# Dork CVE mirati per tecnologia (alimenta DorkCrawlerAgent)
_TECH_CVE_DORK_TEMPLATES: Dict[str, List[str]] = {
    "WordPress":  [
        'site:{domain} inurl:wp-login.php',
        'site:{domain} inurl:xmlrpc.php',
        'site:{domain} inurl:wp-config.php.bak',
    ],
    "Joomla":     ['site:{domain} inurl:configuration.php', 'site:{domain} inurl:/administrator/'],
    "Drupal":     ['site:{domain} inurl:CHANGELOG.txt', 'site:{domain} inurl:sites/default/files'],
    "Laravel":    ['site:{domain} inurl:.env', 'site:{domain} filetype:log storage/logs'],
    "Django":     ['site:{domain} "DisallowedHost"', 'site:{domain} "DEBUG = True"'],
    "phpMyAdmin": ['site:{domain} intitle:"phpMyAdmin" inurl:index.php'],
    "Jenkins":    ['site:{domain} intitle:"Dashboard [Jenkins]"', 'site:{domain} inurl:/jenkins/api/'],
    "Kibana":     ['site:{domain} inurl:app/kibana', 'site:{domain} intitle:"Kibana"'],
    "Grafana":    ['site:{domain} inurl:3000/login intitle:Grafana'],
    "jQuery":     ['site:{domain} inurl:jquery-1', 'site:{domain} inurl:jquery-2'],
}


class TechFingerprintAgent(BaseAgent):
    """
    Rileva tecnologie usate dal target da page_content + response_headers.

    Per ogni result con contenuto disponibile:
      - Identifica CMS, framework, JS libraries, server, linguaggi
      - Tenta di estrarre versioni specifiche
      - Produce 'tech_fingerprint' (dict) e aggiunge dork CVE mirati
        per alimentare DorkCrawlerAgent al round successivo

    Aggiunge 'tech_fingerprint' a ogni result processato.
    Restituisce anche 'cve_dorks' (List[str]) nella return value.
    """

    def __init__(self, plugin=None):
        super().__init__(plugin, name="TechFingerprintAgent")

    def run(self, results: List[dict]) -> List[dict]:
        candidates = [
            r for r in results
            if r.get("page_content") or r.get("response_headers") or r.get("snippet")
        ]
        if not candidates:
            _log(f"[{self.name}] Nessun contenuto disponibile.", style="dim")
            return results

        _log(f"[{self.name}] Fingerprinting {len(candidates)} risultati...", style="bold cyan")

        total_techs = 0
        for r in candidates:
            # Unisci tutto il testo disponibile
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

        _log(f"[{self.name}] Completato: {total_techs} tecnologie rilevate.", style="bold green")
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

                # Genera dork CVE se disponibili
                if name in _TECH_CVE_DORK_TEMPLATES and domain:
                    for tmpl in _TECH_CVE_DORK_TEMPLATES[name]:
                        fp["cve_dorks"].append(tmpl.replace("{domain}", domain))

        return fp

    def get_all_cve_dorks(self, results: List[dict]) -> List[str]:
        """Raccoglie tutti i dork CVE generati — da passare a DorkCrawlerAgent."""
        dorks: List[str] = []
        seen: set = set()
        for r in results:
            for d in r.get("tech_fingerprint", {}).get("cve_dorks", []):
                if d not in seen:
                    seen.add(d)
                    dorks.append(d)
        return dorks


# ══════════════════════════════════════════════════════════════════════════════
#  EMAIL HARVESTER AGENT (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Categorie email per prefisso
_EMAIL_CATEGORIES = {
    "admin":    re.compile(r"^(?:admin|administrator|root|sysadmin|webmaster|hostmaster|postmaster)@", re.I),
    "security": re.compile(r"^(?:security|abuse|vuln|pentest|csirt|cert|soc|noc|infosec)@",          re.I),
    "info":     re.compile(r"^(?:info|contact|hello|support|help|service|sales|marketing)@",          re.I),
    "noreply":  re.compile(r"^(?:no.?reply|noreply|donotreply|mailer.?daemon|bounce)@",               re.I),
}


class EmailHarvesterAgent(BaseAgent):
    """
    Raccoglie e categorizza indirizzi email da snippet + page_content.

    Categorie: admin, security, info, noreply, personal (tutto il resto).
    Produce 'emails_found' (List[dict]) per il result e una lista globale
    accessibile via get_all_emails().

    Non esegue richieste HTTP — lavora sui dati già presenti.
    """

    def __init__(self, plugin=None):
        super().__init__(plugin, name="EmailHarvesterAgent")
        self._global_emails: Dict[str, dict] = {}  # email → entry, dedup globale

    def run(self, results: List[dict]) -> List[dict]:
        candidates = [
            r for r in results
            if r.get("page_content") or r.get("snippet")
        ]
        if not candidates:
            _log(f"[{self.name}] Nessun contenuto disponibile.", style="dim")
            return results

        _log(f"[{self.name}] Email harvesting su {len(candidates)} risultati...", style="bold cyan")

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
        _log(f"[{self.name}] Completato: {total} email uniche trovate.", style="bold green")
        return results

    def _harvest(self, text: str, source_url: str) -> List[dict]:
        found = []
        for m in _EMAIL_RE.finditer(text):
            email = m.group(0).lower().strip()
            if email in self._global_emails:
                continue  # dedup globale
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
        """Restituisce tutte le email raccolte, ordinate per categoria."""
        order = {"admin": 0, "security": 1, "info": 2, "personal": 3, "noreply": 4}
        return sorted(self._global_emails.values(), key=lambda e: order.get(e["category"], 9))


# ══════════════════════════════════════════════════════════════════════════════
#  PII DETECTOR AGENT (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

class PiiDetectorAgent(BaseAgent):
    """
    Rileva dati personali (PII) in snippet + page_content.

    Tipi rilevati: email, telefono (IT/EU/US), IBAN, codice fiscale IT,
    carta di credito (Luhn validation), SSN US, data di nascita, passport,
    IP pubblici.

    Aggiunge 'pii_found' (List[dict]) a ogni result con findings.
    Separato da SecretsAgent — PII ≠ credenziali tecniche.
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
            _log(f"[{self.name}] Nessun contenuto disponibile.", style="dim")
            return results

        _log(f"[{self.name}] PII scan su {len(candidates)} risultati...", style="bold cyan")

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
            f"[{self.name}] Completato: {total_found} PII totali trovati.",
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


# ══════════════════════════════════════════════════════════════════════════════
#  SUBDOMAIN HARVESTER AGENT (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

class SubdomainHarvesterAgent(BaseAgent):
    """
    Estrae subdomini da URL + snippet + page_content di tutti i risultati.

    Per ogni dominio base rilevato raccoglie subdomini unici, li deduplicano
    e genera dork 'site:sub.domain.*' pronti per essere iniettati nel
    DorkCrawlerAgent al round successivo.

    Aggiunge 'subdomains' (List[str]) a ogni result e produce una lista
    globale accessibile via get_all_subdomains() e get_followup_dorks().
    """

    def __init__(self, plugin=None):
        super().__init__(plugin, name="SubdomainHarvesterAgent")
        self._global_subdomains: Dict[str, set] = {}  # base_domain → {subdomains}

    def run(self, results: List[dict]) -> List[dict]:
        if not results:
            return results

        _log(f"[{self.name}] Subdomain harvesting su {len(results)} risultati...", style="bold cyan")

        # Estrai dominio base dalla maggioranza degli URL
        base_domains: set = set()
        for r in results:
            bd = self._base_domain(r.get("url", ""))
            if bd:
                base_domains.add(bd)
        if not base_domains:
            _log(f"[{self.name}] Nessun dominio base trovato.", style="dim")
            return results

        _log(f"[{self.name}] Domini base: {', '.join(list(base_domains)[:5])}", style="dim")

        # Build regex per cercare subdomini di ciascun base domain
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
        _log(f"[{self.name}] Completato: {total} subdomini unici trovati.", style="bold green")
        for bd, subs in self._global_subdomains.items():
            _log(f"[{self.name}]   {bd}: {', '.join(sorted(subs)[:8])}", style="dim")
        return results

    @staticmethod
    def _base_domain(url: str) -> str:
        """Estrae il dominio base (es. example.com da sub.example.com)."""
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
        """Trova tutte le occorrenze di *.base_domain nel testo."""
        escaped = re.escape(base_domain)
        pattern = re.compile(
            r"\b((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+?"
            + escaped + r")\b"
        )
        results = []
        for m in pattern.finditer(text):
            sub = m.group(1).lower()
            # Escludi il base domain stesso e pattern non-sensati
            if sub != base_domain and len(sub) < 200:
                results.append(sub)
        return results

    def get_all_subdomains(self) -> Dict[str, List[str]]:
        """Restituisce tutti i subdomini trovati per dominio base."""
        return {bd: sorted(subs) for bd, subs in self._global_subdomains.items()}

    def get_followup_dorks(self) -> List[str]:
        """Genera dork site:subdomain per alimentare DorkCrawlerAgent."""
        dorks = []
        for bd, subs in self._global_subdomains.items():
            for sub in sorted(subs):
                dorks.append(f'site:{sub}')
                dorks.append(f'site:{sub} inurl:admin')
                dorks.append(f'site:{sub} inurl:.env OR inurl:.git')
        return dorks


# ══════════════════════════════════════════════════════════════════════════════
#  DORK CRAWLER AGENT — recursive adaptive dorking
# ══════════════════════════════════════════════════════════════════════════════

# Template di dork per CMS/tecnologie rilevate
_CMS_DORK_TEMPLATES: Dict[str, List[str]] = {
    "wordpress": [
        'site:{domain} inurl:wp-config.php',
        'site:{domain} inurl:wp-content/uploads filetype:php',
        'site:{domain} inurl:wp-json/wp/v2/users',
        'site:{domain} inurl:xmlrpc.php',
        'site:{domain} inurl:wp-admin/install.php',
        'site:{domain} filetype:log inurl:wp-content',
    ],
    "joomla": [
        'site:{domain} inurl:configuration.php',
        'site:{domain} inurl:administrator/index.php',
        'site:{domain} inurl:components/com_',
        'site:{domain} filetype:xml inurl:joomla',
    ],
    "drupal": [
        'site:{domain} inurl:sites/default/settings.php',
        'site:{domain} inurl:/user/login',
        'site:{domain} inurl:node?destination=',
        'site:{domain} filetype:php inurl:modules',
    ],
    "laravel": [
        'site:{domain} inurl:.env',
        'site:{domain} filetype:log inurl:storage/logs',
        'site:{domain} inurl:public/index.php',
        'site:{domain} inurl:api/v1',
    ],
    "django": [
        'site:{domain} inurl:admin/',
        'site:{domain} "debug" "traceback" "request"',
        'site:{domain} inurl:static/ filetype:py',
        'site:{domain} filetype:sqlite3',
    ],
    "phpmyadmin": [
        'site:{domain} inurl:phpmyadmin/index.php',
        'site:{domain} inurl:pma/ intitle:phpMyAdmin',
        'site:{domain} inurl:phpmyadmin setup',
    ],
    "adminer": [
        'site:{domain} inurl:adminer.php',
        'site:{domain} inurl:adminer/ intitle:Adminer',
    ],
    "magento": [
        'site:{domain} inurl:/admin/ intitle:Magento',
        'site:{domain} inurl:app/etc/local.xml',
        'site:{domain} inurl:downloader/index.php',
    ],
    "prestashop": [
        'site:{domain} inurl:admin123',
        'site:{domain} inurl:/config/settings.inc.php',
        'site:{domain} inurl:modules/paypal',
    ],
}

# Template per path/percorsi interessanti trovati
_PATH_DORK_TEMPLATES: List[str] = [
    'site:{domain} inurl:{path}',
    'site:{domain} inurl:{path} filetype:php',
    'site:{domain} inurl:{path} filetype:env',
    'site:{domain} inurl:{path} filetype:log',
    'site:{domain} inurl:{path} filetype:sql',
    'site:{domain} inurl:{path} filetype:bak',
    'site:{domain} inurl:{path} intitle:"index of"',
]

# Template per estensioni file sensibili trovate
_EXT_DORK_TEMPLATES: Dict[str, List[str]] = {
    ".env":    ['site:{domain} filetype:env', 'site:{domain} inurl:.env.backup', 'site:{domain} inurl:.env.old'],
    ".sql":    ['site:{domain} filetype:sql', 'site:{domain} inurl:backup filetype:sql', 'site:{domain} inurl:dump filetype:sql'],
    ".bak":    ['site:{domain} filetype:bak', 'site:{domain} inurl:backup filetype:bak', 'site:{domain} ext:bak'],
    ".log":    ['site:{domain} filetype:log', 'site:{domain} inurl:logs filetype:log', 'site:{domain} ext:log inurl:error'],
    ".php":    ['site:{domain} filetype:php inurl:config', 'site:{domain} filetype:php inurl:install', 'site:{domain} filetype:php inurl:setup'],
    ".xml":    ['site:{domain} filetype:xml inurl:config', 'site:{domain} filetype:xml inurl:api', 'site:{domain} ext:xml inurl:sitemap'],
    ".json":   ['site:{domain} filetype:json inurl:api', 'site:{domain} filetype:json inurl:config', 'site:{domain} ext:json inurl:secret'],
    ".yaml":   ['site:{domain} filetype:yaml', 'site:{domain} ext:yml inurl:config', 'site:{domain} filetype:yml inurl:docker'],
    ".conf":   ['site:{domain} filetype:conf', 'site:{domain} ext:conf inurl:nginx', 'site:{domain} ext:conf inurl:apache'],
    ".sqlite": ['site:{domain} filetype:sqlite', 'site:{domain} ext:db', 'site:{domain} filetype:sqlite3'],
    ".git":    ['site:{domain} inurl:.git/config', 'site:{domain} inurl:.git/HEAD', 'site:{domain} inurl:.git/COMMIT_EDITMSG'],
}

# Pattern per riconoscere tecnologie dagli snippet/titoli/URL
_TECH_DETECTION: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"wp-content|wp-admin|wordpress",            re.I), "wordpress"),
    (re.compile(r"joomla|com_content|option=com_",           re.I), "joomla"),
    (re.compile(r"drupal|sites/default|node/\d+",            re.I), "drupal"),
    (re.compile(r"laravel|artisan|eloquent|blade\.php",      re.I), "laravel"),
    (re.compile(r"django|wsgi|settings\.py|manage\.py",      re.I), "django"),
    (re.compile(r"phpmyadmin|pma_|phpMyAdmin",               re.I), "phpmyadmin"),
    (re.compile(r"adminer\.php|adminer/",                    re.I), "adminer"),
    (re.compile(r"magento|mage/|varien/",                    re.I), "magento"),
    (re.compile(r"prestashop|/modules/|/themes/community",   re.I), "prestashop"),
]

# Path considerati "interessanti" per il follow-up
_INTERESTING_PATHS = re.compile(
    r"/(admin|administrator|backup|backups|config|configs|api|v1|v2|v3|"
    r"debug|test|tests|dev|staging|old|archive|logs|log|uploads|files|"
    r"db|database|sql|data|export|dump|install|setup|portal|panel|"
    r"private|secret|hidden|internal|manage|management|dashboard)/",
    re.I
)

# Parametri GET sospetti
_SUSPICIOUS_PARAMS = re.compile(
    r"[?&](id|file|path|page|url|redirect|include|require|src|doc|"
    r"template|view|module|action|query|search|q|load|read|show|"
    r"download|open|image|img|lang|locale)=",
    re.I
)


class DorkCrawlerAgent(BaseAgent):
    """
    Agente di crawling ricorsivo adattivo tramite DDGS.

    Esegue piu' round di dorking, raffinando automaticamente i dork
    ad ogni round in base ai pattern trovati nei risultati precedenti.
    Zero LLM — tutto basato su regex, template e pattern matching.

    Pipeline per round:
      1. Cerca con i dork correnti via DDGS
      2. TriageAgent classifica i nuovi risultati
      3. _extract_intelligence() estrae pattern: domini, path, CMS, ext
      4. _generate_followup_dorks() produce nuovi dork mirati
      5. Controlla stop conditions
      6. Riparte dal passo 1 con i nuovi dork

    Stop conditions (prima che scatti vengono tutte valutate):
      - Raggiunto max_rounds
      - Raggiunto max_results totali
      - Nessun nuovo risultato HIGH/CRITICAL nell'ultimo round
      - Nessun nuovo dork generabile (tutti gia' usati)

    Args:
        plugin:         LLMProvider opzionale (arricchisce il triage se presente)
        max_rounds:     numero massimo di round (default: 4)
        max_results:    limite totale risultati aggregati (default: 300)
        results_per_dork: risultati DDGS per dork per round (default: 20)
        min_new_high:   min. nuovi HIGH/CRITICAL per continuare (default: 1)
        delay_between:  pausa in secondi tra una ricerca e l'altra (default: 3.0)
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
        Esegue il crawl ricorsivo adattivo.

        Args:
            seed_dorks: lista dork di partenza (round 1)
            target:     descrizione del target (per il log)

        Returns:
            dict con:
                results       — tutti i risultati aggregati e triaggiati
                rounds        — numero di round completati
                dorks_used    — tutti i dork usati
                round_log     — dettaglio per round
                stop_reason   — motivo dello stop
        """
        if not seed_dorks:
            _log(f"[{self.name}] Nessun seed dork fornito.", style="yellow")
            return self._build_output("no_seed_dorks")

        _log(
            f"[{self.name}] Avvio crawl ricorsivo — "
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
                f"{len(self._all_results)} risultati fin qui) ──",
                style="bold cyan"
            )

            # ── Cerca con i dork correnti ──────────────────────────────────
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
                f"{len(round_results)} trovati, {len(new_results)} nuovi unici",
                style="cyan"
            )

            if not new_results:
                _log(f"[{self.name}] Nessun risultato nuovo — stop.", style="yellow")
                stop_reason = "no_new_results"
                break

            # ── Triage sui nuovi risultati ─────────────────────────────────
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
                    f"[{self.name}] Solo {n_high} nuovo/i HIGH/CRITICAL "
                    f"(min={self.min_new_high}) — stop.",
                    style="yellow"
                )
                stop_reason = "no_new_findings"
                break

            # ── Ultimo round: non generare altri dork ──────────────────────
            if round_n == self.max_rounds:
                stop_reason = "max_rounds_reached"
                break

            # ── Estrai intelligence e genera dork follow-up ────────────────
            intelligence = self._extract_intelligence(new_triaged)
            self._log_intelligence(intelligence, round_n)

            next_dorks = self._generate_followup_dorks(intelligence)
            if not next_dorks:
                _log(f"[{self.name}] Nessun nuovo dork generabile — stop.", style="yellow")
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
        """Esegue le ricerche DDGS per tutti i dork del round corrente."""
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

            # Piccola pausa tra dork dello stesso round
            time.sleep(max(1.0, self.delay_between / 3))

        return results

    # ── Intelligence extraction ───────────────────────────────────────────────

    def _extract_intelligence(self, results: List[dict]) -> dict:
        """
        Estrae pattern strutturali dai risultati triaggiati.

        Analizza URL, titoli e snippet di tutti i risultati (con priorità
        a quelli HIGH/CRITICAL) per costruire un'intelligence map che
        guida la generazione dei dork follow-up.

        Returns:
            dict con: domains, paths, technologies, extensions, params
        """
        intelligence: dict = {
            "domains":      set(),
            "paths":        set(),
            "technologies": set(),
            "extensions":   set(),
            "params":       set(),
        }

        # Priorità: CRITICAL e HIGH per prima
        prioritized = sorted(
            results,
            key=lambda r: r.get("triage_score", 0),
            reverse=True
        )

        for r in prioritized:
            url     = r.get("url", "")
            title   = r.get("title", "")
            snippet = r.get("snippet", "") or ""
            combined = f"{url} {title} {snippet}"

            # ── Dominio ────────────────────────────────────────────────────
            parsed = urlparse(url)
            if parsed.netloc:
                # Usa solo il dominio principale (no www.)
                domain = parsed.netloc.lstrip("www.")
                intelligence["domains"].add(domain)

            # ── Path interessanti ──────────────────────────────────────────
            path = parsed.path
            for m in _INTERESTING_PATHS.finditer(path):
                intelligence["paths"].add(m.group(1).lower())

            # ── Tecnologie/CMS ─────────────────────────────────────────────
            for pattern, tech in _TECH_DETECTION:
                if pattern.search(combined):
                    intelligence["technologies"].add(tech)

            # ── Estensioni file ────────────────────────────────────────────
            ext = Path(path).suffix.lower()
            if ext and ext in _EXT_DORK_TEMPLATES:
                intelligence["extensions"].add(ext)

            # ── Parametri GET sospetti ─────────────────────────────────────
            for m in _SUSPICIOUS_PARAMS.finditer(url):
                intelligence["params"].add(m.group(1).lower())

        # Converti in liste per serializzazione
        return {k: sorted(v) for k, v in intelligence.items()}

    # ── Dork generation ───────────────────────────────────────────────────────

    def _generate_followup_dorks(self, intelligence: dict) -> List[str]:
        """
        Genera dork di follow-up da intelligence estratta.
        Deduplicati vs dork già usati.
        """
        generated: set = set()

        domains     = intelligence.get("domains", [])[:8]   # max 8 domini
        paths       = intelligence.get("paths", [])[:5]     # max 5 path
        technologies = intelligence.get("technologies", [])
        extensions  = intelligence.get("extensions", [])
        params      = intelligence.get("params", [])[:4]    # max 4 param

        # ── Template per tecnologie rilevate ──────────────────────────────
        for tech in technologies:
            templates = _CMS_DORK_TEMPLATES.get(tech, [])
            for tmpl in templates:
                for domain in domains:
                    dork = tmpl.format(domain=domain)
                    if dork not in self._used_dorks:
                        generated.add(dork)

        # ── Template per path × domini ────────────────────────────────────
        for path in paths:
            for domain in domains[:4]:  # max 4 domini per path
                for tmpl in _PATH_DORK_TEMPLATES[:3]:  # max 3 template per path
                    dork = tmpl.format(domain=domain, path=path)
                    if dork not in self._used_dorks:
                        generated.add(dork)

        # ── Template per estensioni × domini ──────────────────────────────
        for ext in extensions:
            templates = _EXT_DORK_TEMPLATES.get(ext, [])
            for tmpl in templates[:2]:  # max 2 template per ext
                for domain in domains[:4]:
                    dork = tmpl.format(domain=domain)
                    if dork not in self._used_dorks:
                        generated.add(dork)

        # ── Dork per parametri GET sospetti × domini ───────────────────────
        for param in params:
            for domain in domains[:3]:
                dorks_from_params = [
                    f'site:{domain} inurl:"?{param}="',
                    f'site:{domain} inurl:"{param}=" filetype:php',
                ]
                for d in dorks_from_params:
                    if d not in self._used_dorks:
                        generated.add(d)

        # ── Dork generici per domini trovati (sempre) ──────────────────────
        for domain in domains[:5]:
            generic = [
                f'site:{domain} intitle:"index of"',
                f'site:{domain} inurl:backup',
                f'site:{domain} inurl:.git',
                f'site:{domain} inurl:api',
                f'site:{domain} filetype:env',
            ]
            for d in generic:
                if d not in self._used_dorks:
                    generated.add(d)

        return list(generated)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_intelligence(self, intel: dict, round_n: int) -> None:
        """Stampa un riepilogo dell'intelligence estratta."""
        parts = []
        if intel.get("domains"):
            parts.append(f"domini:{len(intel['domains'])}")
        if intel.get("technologies"):
            parts.append(f"tech:{','.join(intel['technologies'])}")
        if intel.get("paths"):
            parts.append(f"path:{len(intel['paths'])}")
        if intel.get("extensions"):
            parts.append(f"ext:{','.join(intel['extensions'])}")
        if intel.get("params"):
            parts.append(f"params:{','.join(intel['params'])}")
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
        """Stampa il riepilogo finale del crawl."""
        _panel(
            f"  Rounds completati : {output['rounds']}/{self.max_rounds}\n"
            f"  Stop reason       : {output['stop_reason']}\n"
            f"  Dork usati        : {len(output['dorks_used'])}\n"
            f"  Risultati totali  : {output['total']}\n"
            f"  CRITICAL          : {output['critical']}\n"
            f"  HIGH              : {output['high']}\n"
            f"  MEDIUM            : {output['medium']}",
            title="[bold cyan][ DorkCrawlerAgent — Crawl Summary ][/bold cyan]",
            border="cyan",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CLI INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

def add_crawler_args(parser) -> object:
    """Aggiunge i flag --crawl-* al parser CLI di DorkEye."""
    g = parser.add_argument_group(
        "Crawl Ricorsivo — dorking adattivo multi-round (no AI)"
    )
    g.add_argument(
        "--crawl",
        action="store_true",
        help="Attiva il crawl ricorsivo adattivo dopo la ricerca iniziale",
    )
    g.add_argument(
        "--crawl-rounds",
        type=int, default=4,
        help="Numero massimo di round di raffinamento (default: 4)",
    )
    g.add_argument(
        "--crawl-max",
        type=int, default=300,
        help="Limite totale risultati aggregati (default: 300)",
    )
    g.add_argument(
        "--crawl-per-dork",
        type=int, default=20,
        help="Risultati DDGS per dork per round (default: 20)",
    )
    g.add_argument(
        "--crawl-stealth",
        action="store_true",
        help="Modalita' stealth: delay piu' lunghi tra le ricerche",
    )
    g.add_argument(
        "--crawl-report",
        action="store_true",
        help="Genera report HTML del crawl al termine",
    )
    g.add_argument(
        "--crawl-out",
        type=str, default=None,
        help="Path report crawl (default: dorkeye_crawl_<timestamp>.html)",
    )
    return parser


def run_crawl(
    seed_dorks: List[str],
    args,
    target:  str = "",
    plugin       = None,
) -> dict:
    """
    Entry point per dorkeye.py — avvia il DorkCrawlerAgent.

    Args:
        seed_dorks: dork iniziali (da -d o --dg)
        args:       argparse.Namespace con i flag --crawl-*
        target:     descrizione del target
        plugin:     LLMProvider opzionale

    Returns:
        dict output del crawler (results, rounds, dorks_used, ecc.)
    """
    crawler = DorkCrawlerAgent(
        plugin          = plugin,
        max_rounds      = getattr(args, "crawl_rounds",   4),
        max_results     = getattr(args, "crawl_max",      300),
        results_per_dork = getattr(args, "crawl_per_dork", 20),
        stealth         = getattr(args, "crawl_stealth",  False),
    )

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
        _log(f"[Crawl] Report salvato: {out}", style="bold green")

    return output


def run_analysis_pipeline(
    results:    List[dict],
    llm_plugin = None,
    args       = None,
    target:    str = "",
) -> dict:
    """
    Esegue la pipeline di analisi post-ricerca v3.0.

    Funziona SENZA LLM (llm_plugin=None):
        1.  TriageAgent             — classifica con regex + bonus runtime
        2.  PageFetchAgent          — scarica pagine HIGH/CRITICAL (se --analyze-fetch)
        3.  HeaderIntelAgent        — analizza response headers
        4.  TechFingerprintAgent    — rileva CMS/framework/versioni
        5.  SecretsAgent            — scansione secrets + hash + severity
        6.  PiiDetectorAgent        — rileva PII (CC, IBAN, CF, SSN, ecc.)
        7.  EmailHarvesterAgent     — raccoglie e categorizza email
        8.  SubdomainHarvesterAgent — estrae subdomini, genera follow-up dorks
        9.  ReportAgent             — genera report HTML/MD/JSON completo

    Args:
        results:    lista risultati DorkEye
        llm_plugin: DorkEyeLLMPlugin (opzionale — None = solo regex)
        args:       argparse.Namespace con i flag --analyze-*
        target:     descrizione target (per il report)

    Returns:
        dict con: triaged, secrets_total, pii_total, emails_total,
                  subdomains, cve_dorks, report_path, analysis
    """
    if args is None:
        args = type("A", (), {
            "analyze_fetch":         False,
            "analyze_fetch_max":     20,
            "analyze_no_llm_triage": False,
            "analyze_report":        True,
            "analyze_fmt":           "html",
            "analyze_out":           None,
        })()

    output = {
        "triaged":       None,
        "secrets_total": 0,
        "pii_total":     0,
        "emails_total":  0,
        "subdomains":    {},
        "cve_dorks":     [],
        "report_path":   None,
        "analysis":      {},
    }

    if not results:
        _log("[Agents] Nessun risultato da analizzare.", style="yellow")
        return output

    mode_label = "LLM + regex" if llm_plugin else "regex autonomo"
    _log(f"[Agents] Pipeline v3.0 — modalità: {mode_label}", style="bold cyan")

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

    # ── 3. Header Intel ───────────────────────────────────────────────────────
    header_agent = HeaderIntelAgent()
    triaged      = header_agent.run(triaged)

    # ── 4. Tech Fingerprint ───────────────────────────────────────────────────
    tech_agent = TechFingerprintAgent()
    triaged    = tech_agent.run(triaged)
    cve_dorks  = tech_agent.get_all_cve_dorks(triaged)
    output["cve_dorks"] = cve_dorks
    if cve_dorks:
        _log(f"[Agents] TechFP: {len(cve_dorks)} CVE dork generati.", style="cyan")

    # ── 5. Secrets scan ───────────────────────────────────────────────────────
    use_llm_secrets = llm_plugin is not None
    secrets_agent   = SecretsAgent(plugin=llm_plugin, use_llm=use_llm_secrets)
    triaged         = secrets_agent.run(triaged)

    all_secrets = [s for r in triaged for s in r.get("secrets", [])]
    output["secrets_total"] = len(all_secrets)

    if all_secrets:
        # Ordina per severity
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

    # ── 6. PII Detection ──────────────────────────────────────────────────────
    pii_agent = PiiDetectorAgent()
    triaged   = pii_agent.run(triaged)
    all_pii   = [p for r in triaged for p in r.get("pii_found", [])]
    output["pii_total"] = len(all_pii)
    if all_pii:
        _log(f"[Agents] PII: {len(all_pii)} dato/i personale/i rilevato/i.", style="bold red")

    # ── 7. Email Harvesting ───────────────────────────────────────────────────
    email_agent   = EmailHarvesterAgent()
    triaged       = email_agent.run(triaged)
    all_emails    = email_agent.get_all_emails()
    output["emails_total"] = len(all_emails)
    if all_emails:
        _log(f"[Agents] Email: {len(all_emails)} email univoche raccolte.", style="cyan")

    # ── 8. Subdomain Harvesting ───────────────────────────────────────────────
    subdomain_agent = SubdomainHarvesterAgent()
    triaged         = subdomain_agent.run(triaged)
    all_subdomains  = subdomain_agent.get_all_subdomains()
    followup_dorks  = subdomain_agent.get_followup_dorks()
    output["subdomains"] = all_subdomains
    output["cve_dorks"]  = list(dict.fromkeys(cve_dorks + followup_dorks))  # dedup preserving order
    if all_subdomains:
        total_subs = sum(len(v) for v in all_subdomains.values())
        _log(f"[Agents] Subdomain: {total_subs} subdomini trovati.", style="cyan")

    # ── 9. LLM analysis (solo se llm_plugin disponibile) ─────────────────────
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

        reporter = ReportAgent(plugin=llm_plugin)
        reporter.run(
            results     = triaged,
            analysis    = analysis,
            target      = target,
            output_path = out,
            fmt         = fmt,
            extra        = {
                "emails":     all_emails,
                "pii":        all_pii,
                "subdomains": all_subdomains,
                "cve_dorks":  output["cve_dorks"],
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


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE — analizza un file JSON di risultati DorkEye
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse as _ap
    import sys

    parser = _ap.ArgumentParser(
        description="DorkEye Agents v3.0 — Analisi autonoma su file risultati",
        formatter_class=_ap.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  # Analisi autonoma (nessun LLM richiesto)\n"
            "  python dorkeye_agents.py results.json\n"
            "  python dorkeye_agents.py results.json --analyze-fetch --analyze-fmt=html\n\n"
            "  # Con LLM Ollama (opzionale — aggiunge summary e analisi contestuale)\n"
            "  python dorkeye_agents.py results.json --llm --analyze-fetch\n"
        ),
    )
    parser.add_argument(
        "results_file",
        help="File JSON dei risultati DorkEye (prodotto con -o results.json)",
    )
    parser.add_argument("--target", default="", help="Descrizione target (opzionale)")
    parser.add_argument("--analyze-fetch",     action="store_true",
                        help="Scarica pagine HIGH/CRITICAL per analisi piu' accurata")
    parser.add_argument("--analyze-fetch-max", type=int, default=20,
                        help="Max pagine da scaricare (default: 20)")
    parser.add_argument("--analyze-no-llm-triage", action="store_true",
                        help="Triage solo regex (ignora LLM anche se disponibile)")
    parser.add_argument("--analyze-report",    action="store_true", default=True,
                        help="Genera report file (default: True)")
    parser.add_argument("--analyze-fmt",       choices=["html","md","json","txt"],
                        default="html", help="Formato report (default: html)")
    parser.add_argument("--analyze-out",       default=None,
                        help="Path output report")

    # Argomenti LLM opzionali — importati solo se disponibili
    _llm_available = False
    try:
        from dorkeye_llm_plugin import add_llm_args, init_llm_plugin
        add_llm_args(parser)
        _llm_available = True
    except ImportError:
        parser.add_argument("--llm", action="store_true",
                            help="(non disponibile: dorkeye_llm_plugin.py mancante)")

    args     = parser.parse_args()
    args.llm = getattr(args, "llm", False)

    # Carica risultati
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
        print(f"[!] Nessun risultato in '{p}'.", file=sys.stderr)
        sys.exit(1)

    # Init LLM (opzionale)
    llm = None
    if args.llm and _llm_available:
        llm = init_llm_plugin(args)
        if not llm:
            print("[!] LLM non inizializzato — continuo in modalita' autonoma.", file=sys.stderr)
    elif args.llm and not _llm_available:
        print("[!] dorkeye_llm_plugin.py non trovato — modalita' autonoma.", file=sys.stderr)

    print(f"\n[*] Analisi di {len(results)} risultati da '{p.name}'")
    print(f"[*] Modalita': {'LLM + regex' if llm else 'autonoma (regex)'}")

    out = run_analysis_pipeline(
        results    = results,
        llm_plugin = llm,
        args       = args,
        target     = args.target,
    )

    print()
    if out.get("report_path"):
        print(f"[✓] Report: {out['report_path']}")
    print(f"[✓] Segreti trovati: {out['secrets_total']}")
    print(f"[✓] PII trovati:     {out.get('pii_total', 0)}")
    print(f"[✓] Email raccolte:  {out.get('emails_total', 0)}")
    n_subs = sum(len(v) for v in out.get('subdomains', {}).values())
    print(f"[✓] Subdomini:       {n_subs}")
    print(f"[✓] CVE dorks:       {len(out.get('cve_dorks', []))}")
    if out.get("triaged"):
        from collections import Counter
        dist = Counter(r.get("triage_label", "?") for r in out["triaged"])
        print(f"[✓] Triage: CRITICAL={dist.get('CRITICAL',0)} HIGH={dist.get('HIGH',0)} "
              f"MEDIUM={dist.get('MEDIUM',0)} LOW={dist.get('LOW',0)}")
