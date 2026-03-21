# Adaptive Recursive Crawler — DorkEye v4.8

The crawler runs additional rounds of DuckDuckGo searches after the initial result set, automatically refining its dorks based on what it found in each round. No AI — everything is driven by pattern matching and template logic.

---

## Enable

```bash
# Append --crawl to any search command
python dorkeye.py -d "site:example.com inurl:admin" --crawl -o crawl.json

# With the Dork Generator
python dorkeye.py --dg=sqli --crawl -o crawl.json

# On a saved result file (v4.8)
python dorkeye.py -f Dump/results.json --crawl -o crawl.json
```

---

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--crawl` | off | Enable the adaptive recursive crawler |
| `--crawl-rounds N` | `4` | Maximum number of refinement rounds |
| `--crawl-max N` | `300` | Total result ceiling across all rounds |
| `--crawl-per-dork N` | `20` | DuckDuckGo results per dork per round |
| `--crawl-stealth` | off | Longer delays between round searches |
| `--crawl-report` | off | Generate a dedicated HTML crawl report |
| `--crawl-out FILE` | auto | Path for the crawl report (default: `dorkeye_crawl_TIMESTAMP.html`) |

---

## How It Works — Round by Round

Each round follows the same 5-step cycle:

```
1. Search    — run current dork set via DuckDuckGo
2. Dedup     — remove URLs already seen in previous rounds
3. Triage    — score and label new results with TriageAgent
4. Extract   — pull intelligence from HIGH/CRITICAL results
5. Generate  — build refined follow-up dorks for next round
```

**Intelligence extracted per round:**

| Signal | What gets extracted |
|--------|-------------------|
| Domain / subdomain | `site:sub.domain` dorks |
| Interesting path | `inurl:admin`, `inurl:backup`, `inurl:api`, etc. |
| Technology (CMS/framework) | CMS-specific dork templates |
| Sensitive file extension | Extension-specific dork variants |

### CMS-specific follow-up dorks (examples)

| Detected CMS | Dorks generated |
|--------------|----------------|
| WordPress | `site:{domain} inurl:wp-config.php`, `inurl:wp-json/users`, `inurl:xmlrpc.php` |
| Joomla | `site:{domain} inurl:configuration.php`, `inurl:administrator/index.php` |
| Laravel | `site:{domain} inurl:.env`, `filetype:log inurl:storage/logs` |
| Django | `site:{domain} "DisallowedHost"`, `"DEBUG = True"` |
| phpMyAdmin | `site:{domain} intitle:"phpMyAdmin" inurl:index.php` |

### v4.8 integration

The crawler also receives CVE dorks from **TechFingerprintAgent** and `site:subdomain` dorks from **SubdomainHarvesterAgent** — both run during the Agents v3.0 pipeline. This means the crawler can be pre-seeded with precise, technology-aware targets on the very first round.

---

## Stop Conditions

The crawler stops at the first condition that fires:

| Condition | Description |
|-----------|-------------|
| `max_rounds_reached` | All rounds completed without early stop |
| `no_new_results` | A round returned zero new unique URLs |
| `no_new_findings` | Round 2+ found fewer than 1 new HIGH/CRITICAL result |
| `no_new_dorks` | No new follow-up dorks could be generated |
| `max_results_reached` | Total results hit `--crawl-max` ceiling |

The stop reason is shown in the terminal summary and in the crawl report.

---

## Terminal Output

```
[Crawl] Avvio crawl ricorsivo adattivo...
[Crawl] ── Round 1/4 (3 dork, 0 risultati fin qui) ──
[Crawl] Round 1: 41 trovati, 38 nuovi unici
[Crawl] Triage round 1: CRITICAL+HIGH=12 | TOTAL=38
[Crawl] 9 dork follow-up generati per round 2
  → site:target.com inurl:wp-config.php
  → site:target.com inurl:xmlrpc.php
  → site:api.target.com
  ... e altri 6

[Crawl] ── Round 2/4 (9 dork, 38 risultati fin qui) ──
...

[Crawl] Completato — 3 round | +74 nuovi risultati | stop: no_new_findings
```

---

## Combining Crawl with Other Features

```bash
# Crawl + SQLi on found URLs
python dorkeye.py -d "site:target.com" --sqli --crawl -o results.json

# Crawl + analysis pipeline
python dorkeye.py -d "site:target.com" \
  --analyze --analyze-fetch \
  --crawl --crawl-rounds 5 --crawl-report \
  -o results.json

# Maximum configuration
python dorkeye.py --dg=all --mode=aggressive \
  --sqli --stealth \
  --analyze --analyze-fetch --analyze-fetch-max 50 \
  --crawl --crawl-rounds 6 --crawl-max 500 \
  --crawl-stealth --crawl-report --crawl-out crawl_report.html \
  -o results.json
```

---

## Notes

- All crawl results are deduplicated against the initial search results — no URL appears twice in the final output.
- New crawl results are merged into the main result list and saved to the same `-o` output file.
- `--crawl-stealth` is independent of `--stealth` — each controls delays in its own context.
- `--crawl-out` only produces a file when `--crawl-report` is also set.
