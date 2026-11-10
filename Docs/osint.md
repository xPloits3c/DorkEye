# OSINT Graph — DorkEye Project

`--osint` builds a correlation graph around the hosts DorkEye finds (or the seeds you give it),
using public registries and archives only. No API keys are needed.

Requires `Tools/osint.py`. It uses only `requests` and the Python standard library, so there
is nothing extra to install.

---

## How it works

1. **Seeds** — the starting points: the hosts found by your dorks, the `-u` URL, or explicit
   `--osint-seed` values (domain, host, IP or URL).
2. **Chain** — an ordered list of steps. Each step runs one source on the nodes of a given type
   (for example, `crtsh` on every `domain`).
3. **Child nodes** — everything a source finds (subdomains, IPs, ASNs, emails…) is stored as a
   child of the node that produced it, so later steps can expand it further.
4. **Graph** — at the end the nodes are correlated (shared IPs, ASN clusters, known CVEs) and
   written to an HTML report with an embedded SQLite database.

Everything is stored in a small SQLite graph, created fresh for every run (see [Database](#database)).

---

## Sources

| Source | Expands | Finds |
|--------|---------|-------|
| `rdap` | domain | Registrar, creation/expiry dates, nameservers, registrant contacts (rdap.org) |
| `crtsh` | domain | Subdomains from Certificate Transparency logs (crt.sh) |
| `dns` | domain, host | A / AAAA / MX / NS / TXT records (Cloudflare DNS-over-HTTPS) |
| `wayback` | domain | Sample of archived URLs (Wayback Machine CDX, up to 40) |
| `http` | host, domain | Status code, `Server` header, `<title>`, `security.txt`, emails/phones in the page |
| `internetdb` | IP | Open ports, CPEs, known CVEs, hostnames (Shodan InternetDB, keyless) |
| `ptr` | IP | Reverse-DNS hostname (Cloudflare DNS-over-HTTPS) |
| `ipmeta` | IP | ASN, organisation/ISP, country/city (ipwho.is, keyless) |

All sources except `http` query third-party services, never the target. The `http` step makes
one HTTPS request to each host it expands (plus `/.well-known/security.txt`), so it does touch
the target. It is only part of level 3 and of the `recon-contacts` chain.

Private, loopback and link-local addresses are never expanded.

---

## Intensity levels

| `--osint` | Chain | Steps | Touches the target |
|-----------|-------|-------|--------------------|
| `1` | `recon-basic` | rdap → crtsh → dns | No |
| `2` *(default)* | `recon-ip` | level 1 + internetdb, ptr, ipmeta on every IP | No |
| `3` | `recon-passive` | level 2 + wayback and http | Yes (`http` step) |

`--osint` with no value means level 2. Instead of a number you can pass a chain name or a JSON
file (see [Custom chains](#custom-chains)):

| Chain | Steps |
|-------|-------|
| `recon-contacts` | rdap, crtsh, dns, internetdb, ipmeta, http — focused on emails and phones |

---

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--osint [LEVEL]` | off (`2` when given without a value) | Run OSINT. `LEVEL` is `1`, `2`, `3`, a chain name or a `.json` chain file |
| `--osint-seed VALUE` | none | Extra seed (domain, host, IP or URL), added to the dork / `-u` hosts. Repeatable. On its own it runs OSINT only, at level 2 |
| `--osint-db PATH` | per run (see [Database](#database)) | SQLite database for the graph, recreated on every run. Its file name (without extension) also names the OSINT report and extra exports in `Dump/` |
| `--osint-threads N` | `2` | Worker threads per step. Kept low for small devices |
| `--osint-max-nodes N` | `2000` | Stop once this run has collected this many nodes (seeds included) |
| `--osint-export LIST` | none | Extra files next to the HTML, comma-separated: `csv`, `json`, `graphml`, `txt` |

Each worker waits 0.5 s before every source call, and each request times out after 15 s.

---

## Where seeds come from

| Command | Seeds |
|---------|-------|
| `-d` / `--dg` / `-f` + `--osint` | Every `--osint-seed`, then every unique host in the results (private hosts skipped) |
| `-u URL --osint` | The URL's host, plus any `--osint-seed` |
| `--osint-seed VALUE` alone | Only the given seeds — no dork search is run |

A URL seed is reduced to its host. An IPv4 address is treated as an IP; anything else as a domain.

---

## Output

**With dork results** (`-d`, `--dg`, `-f`): OSINT becomes the **OSINT** tab of the single
tabbed report, next to Dorks (and Analyze, DBScan or Crawl when those ran too).
The report is `Dump/<-o name>.html`. When `-o` is `.json`, `.csv` or `.txt`, that file keeps
the results and the tabbed report is written beside it with the same name and `.html`.

**Standalone** (`--osint-seed` only, or `-u --osint`): the report is written to
`Dump/<db name>.html`, e.g. `Dump/osint_example.com_20261110_190850.html`.

### Report sections

| Section | Content |
|---------|---------|
| Graph | Interactive node/edge view, coloured by type |
| Findings | IPs with known CVEs (with ports), hosts with telling names (`admin`, `dev`, `staging`, `vpn`, `jenkins`, `backup`…), most common open ports |
| Contacts (MetaByte) | Emails and phone numbers found in RDAP records, pages and `security.txt` |
| All IPs | Every IP with ports, ASN, organisation, country and PTR |
| Pivots — shared IP | IPs that serve more than one host |
| ASN clusters | IPs grouped by autonomous system |

The page works offline and can download the graph as JSON, CSV (nodes and edges), a TXT
summary, GraphML and the SQLite database (embedded when it is 8 MB or smaller).

### `--osint-export`

| Value | File written in `Dump/` |
|-------|-------------------------|
| `csv` | `<name>.csv` — all nodes |
| `json` | `<name>_graph.json` — nodes, edges, clusters, findings |
| `graphml` | `<name>.graphml` — for Gephi, yEd, Cytoscape |
| `txt` | `<name>_summary.txt` — plain-text summary: seeds, chain, counts, vulnerable IPs, interesting hosts, shared-IP pivots, contacts |

---

## Database

Every run starts from an empty graph, so each report shows only the targets of that run and
every seed is always queried again.

| Run | Database (in `Dump/`) | Notes |
|-----|-----------------------|-------|
| Dorks + OSINT (`-d`, `--dg`, `-f`) | `<-o name>_osint.sqlite` | Rewritten together with the report when you reuse the same `-o` |
| OSINT only (`--osint-seed`, `-u --osint`, wizard) | `osint_<first seed>_<date>_<time>.sqlite` | A new file every run — earlier runs are kept |
| `--osint-db PATH` | `PATH` | Recreated from scratch at the start of the run |

```bash
python dorkeye.py --osint-seed example.com --osint-db Dump/example_osint.sqlite
```

---

## Custom chains

A chain is a JSON list of steps. Each step names a source and the node types it expands:

```json
{
  "chain": [
    {"source": "crtsh",      "on": ["domain"]},
    {"source": "dns",        "on": ["domain", "host"]},
    {"source": "internetdb", "on": ["ip"]}
  ]
}
```

A bare list (without the `"chain"` key) also works. Pass the file to `--osint`:

```bash
python dorkeye.py --osint-seed example.com --osint=my_chain.json
```

Node types a step can expand: `domain`, `host`, `ip`, `asn`, `url`, `email`, `phone`, `whois`, `meta`.

---

## Wizard and Web Console

- **Wizard** — after the search options it asks `Enable OSINT? 0=no 1=basic 2=medium 3=full`.
  OSINT then runs on the hosts in the results and writes its own report to
  `Dump/osint_<first host>_<date>_<time>.html`.
- **Web Console** — the **OSINT (--osint)** selector in the scan form (`Off`, `1 — basic`,
  `2 — medium`, `3 — full`) adds `--osint=N` to the job.

---

## Standalone (`python Tools/osint.py`)

| Flag | Default | Description |
|------|---------|-------------|
| `--seed VALUE` | *(required)* | Seed (domain, host, IP or URL). Repeatable |
| `--chain NAME` | `recon-basic` | Built-in chain name or path to a `.json` chain |
| `--db PATH` | `Dump/osint_<seed>_<time>.sqlite` | SQLite output path, recreated every run |
| `--threads N` | `2` | Worker threads |
| `--timeout S` | `15` | Request timeout in seconds |
| `--max-nodes N` | `2000` | Node cap |
| `--html PATH` | next to the DB | HTML report path |
| `--export LIST` | none | `csv`, `json`, `graphml`, `txt` |

---

## Examples

```bash
# Dorks + OSINT on every host found (level 2), one tabbed report
python dorkeye.py -d "site:example.com" --osint -o example.html

# Quick registry/CT-only pass on saved results
python dorkeye.py -f Dump/results.json --osint=1 -o results.html

# Full pass with exports, separate database for this target
python dorkeye.py -d dorks.txt --osint=3 --osint-db Dump/target.sqlite --osint-export csv,graphml -o target.html

# OSINT only, no dork search
python dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Dorks + OSINT, with an extra seed that the dorks may not find
python dorkeye.py -d "site:example.com" --osint --osint-seed 203.0.113.10 -o example.html

# Single URL: OSINT only, or OSINT + SQLi/XSS test
python dorkeye.py -u "https://example.com/page.php?id=1" --osint
python dorkeye.py -u "https://example.com/page.php?id=1" --osint --sqli --xss -o test.json

# Standalone module
python Tools/osint.py --seed example.com --chain recon-ip --export csv
```

---

> Use OSINT only on domains you own or are authorized to assess.
