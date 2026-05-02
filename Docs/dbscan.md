# DB Port Scanner — DorkEye

> Scans exposed database ports on hosts extracted from dork results.
> Detects open services, grabs banners, and confirms unauthenticated access via protocol-level probes.

-----

## Overview

`db_portscan.py` is a multi-threaded database port scanner integrated into the DorkEye pipeline.
It extracts unique hostnames from result sets, scans them for exposed database services,
and classifies each finding by severity based on whether authentication is required.

The scanner uses **protocol-aware probes** — not just TCP connect checks — so it can
distinguish between a port that is open-but-authenticated and one that is directly accessible
with no credentials.

**Lives in:** `DorkEye/Tools/db_portscan.py`

-----

## Usage

### Integrated (via `dorkeye.py`)

```bash
# Enable DB scan on results from a dork search
python dorkeye.py -d dorks.txt --dbscan -o results.json

# With custom timeout and thread count
python dorkeye.py -d dorks.txt --dbscan --dbscan-timeout 3 --dbscan-threads 80 -o results.json

# Re-process an existing results file
python dorkeye.py -f Dump/results.json --dbscan -o retest.json

# Full pipeline with DB scan
python dorkeye.py \
  --dg=sqli \
  --mode=aggressive \
  --sqli \
  --dbscan \
  --dbscan-timeout 2.5 \
  --dbscan-threads 80 \
  --dbscan-max-hosts 200 \
  -o full.json
```

### Standalone

```bash
python Tools/db_portscan.py results.json
python Tools/db_portscan.py results.json --timeout 3 --threads 80
python Tools/db_portscan.py results.json --ports 3306 5432 27017 6379
python Tools/db_portscan.py results.json --stealth --max-hosts 50
python Tools/db_portscan.py results.json --out Dump/custom_report
```

-----

## Flags

### Integrated flags (via `dorkeye.py`)

|Flag                  |Default|Description                                            |
|----------------------|-------|-------------------------------------------------------|
|`--dbscan`            |off    |Enable DB port scan on all hosts extracted from results|
|`--dbscan-timeout N`  |`2.5`  |TCP connect timeout per port in seconds                |
|`--dbscan-threads N`  |`60`   |Worker threads per host (hard cap: 200)                |
|`--dbscan-max-hosts N`|`200`  |Maximum unique hosts to scan per run                   |

### Standalone flags (`python Tools/db_portscan.py`)

|Flag          |Default     |Description                                                       |
|--------------|------------|------------------------------------------------------------------|
|`results_file`|*(required)*|DorkEye `.json` results file                                      |
|`--timeout`   |`2.5`       |TCP connect timeout in seconds                                    |
|`--threads`   |`60`        |Worker threads per host                                           |
|`--ports N…`  |all DB ports|Space-separated custom port list to scan                          |
|`--max-hosts` |`200`       |Max unique hosts to scan                                          |
|`--stealth`   |off         |Add random inter-host delay (1.5–3.5 s) to reduce detection risk  |
|`--out FILE`  |auto        |Output base path — writes `_dbscan_<ts>.json` + `_dbscan_<ts>.txt`|

-----

## Detected Services

### Default scan set

|Service      |Port |Probe Method                                              |
|-------------|-----|----------------------------------------------------------|
|Elasticsearch|9200 |HTTP GET `/` — checks `cluster_name`, `version`, `tagline`|
|Elasticsearch|9300 |TCP banner                                                |
|CouchDB      |5984 |HTTP GET `/` — checks `couchdb`, `Welcome`                |
|InfluxDB     |8086 |HTTP GET `/ping` — HTTP 204 = alive                       |
|Neo4j HTTP   |7474 |HTTP GET `/` — checks `neo4j`, `bolt`                     |
|Riak HTTP    |8098 |HTTP GET `/`                                              |
|RethinkDB    |28015|TCP banner                                                |
|MySQL        |3306 |TCP banner                                                |
|PostgreSQL   |5432 |TCP banner                                                |
|MongoDB      |27017|OP_MSG `isMaster` handshake                               |
|Redis        |6379 |`PING\r\n` → `+PONG` = no-auth confirmed                  |
|Memcached    |11211|`stats\r\n` → `STAT` = no-auth confirmed                  |
|MSSQL        |1433 |TCP banner                                                |
|Oracle       |1521 |TCP banner                                                |
|Cassandra    |9042 |TCP banner                                                |

### Non-default ports (require explicit `--ports`)

|Service       |Port |Probe Method   |
|--------------|-----|---------------|
|RethinkDB     |5000 |TCP banner     |
|DB2           |50000|TCP banner     |
|MongoDB Shard |27018|OP_MSG isMaster|
|MongoDB Config|27019|OP_MSG isMaster|

-----

## Probe Methods

The scanner uses six distinct probe strategies depending on the service:

|Probe      |How it works                                                                                                       |
|-----------|-------------------------------------------------------------------------------------------------------------------|
|`banner`   |TCP connect → wait for service banner → close. Confirms port is open; banner identifies service.                   |
|`http`     |HTTP GET with `requests`. Tries `http://` then `https://`. Checks response body for service-specific keys.         |
|`redis`    |Sends `PING\r\n`. `+PONG` response = unauthenticated. `-NOAUTH` = auth required.                                   |
|`mongodb`  |Sends a raw OP_MSG `isMaster` packet. Valid response = port open; `ismaster`/`isWritablePrimary` in body = no-auth.|
|`memcached`|Sends `stats\r\n`. Response starting with `STAT` = unauthenticated access; version extracted.                      |
|`none`     |TCP connect only — port open/closed, no further probing.                                                           |

-----

## Severity Levels

|Level     |Condition                                                   |Action recommended                           |
|----------|------------------------------------------------------------|---------------------------------------------|
|`CRITICAL`|Port open **and** unauthenticated access confirmed          |Immediate investigation — data likely exposed|
|`HIGH`    |Port open and service identity confirmed via banner/protocol|Verify auth configuration                    |
|`MEDIUM`  |Port open, service identity unclear                         |Manual verification                          |
|`INFO`    |Port closed / filtered / timeout                            |No action required                           |

-----

## Port Hints

The scanner reads the `dork`, `title`, `snippet`, and `url` fields of each result and
matches them against a built-in pattern table. Matching ports are promoted to the **front
of the scan queue** for that host, reducing time-to-finding on likely targets.

|Pattern matched in result          |Priority ports|
|-----------------------------------|--------------|
|`phpmyadmin`, `mysqladmin`         |3306          |
|`pgadmin`, `postgresql`, `postgres`|5432          |
|`mongodb`, `mongo`, `robo3t`       |27017, 27018  |
|`redis`, `redisinsight`            |6379          |
|`elasticsearch`, `kibana`          |9200, 9300    |
|`couchdb`, `fauxton`               |5984          |
|`influx`                           |8086          |
|`neo4j`                            |7474          |
|`mssql`, `sqlserver`, `sql server` |1433          |
|`oracle`, `tns listener`           |1521          |
|`cassandra`                        |9042          |
|`memcache`                         |11211         |

Remaining ports are shuffled randomly to avoid predictable scan patterns.

-----

## Host Extraction & Filtering

Hosts are extracted from the `url` field of each result using `urlparse`.

**Automatically excluded:**

- Duplicate hostnames (one scan per unique host)
- Private/loopback addresses: `127.x`, `192.168.x`, `10.x`, `172.16–31.x`,
  `169.254.x`, `0.0.0.0`, `localhost`, `::1`, `fc00::/7`
- Hosts without a dot in the name (bare hostnames)

The `--max-hosts` cap is applied after filtering — hosts beyond the limit are silently skipped.

-----

## Threading Model

Each host is scanned with an internal worker pool:

- `--threads` (or `--dbscan-threads`) controls workers **per host**
- All ports for a host are queued internally; workers pull from the queue concurrently
- Hosts are processed **sequentially** (one at a time) to keep network impact predictable
- In stealth mode a random delay of 1.5–3.5 s is added between hosts

The hard cap of 200 threads per host prevents resource exhaustion on large port lists.

-----

## Interrupt Handling

The scanner respects DorkEye’s global interrupt flags:

|Action                         |Effect                                       |
|-------------------------------|---------------------------------------------|
|**Single Ctrl+C**              |Stop current host scan → save partial results|
|**Double Ctrl+C** (within 1.5s)|Exit immediately → save partial results      |

-----

## Output Files

When run standalone or via `--dbscan`, two files are written alongside the main output:

### `_dbscan_<ts>.json`

Structured JSON with full per-host findings:

```json
{
  "generated_at": "2025-05-01 14:32:10",
  "stats": {
    "hosts_scanned": 12,
    "ports_scanned": 180,
    "open_ports": 4,
    "critical": 1,
    "high": 2,
    "medium": 1
  },
  "hosts": [
    {
      "host": "example.com",
      "scanned": 15,
      "duration": 3.21,
      "critical": 1,
      "high": 0,
      "findings": [
        {
          "host": "example.com",
          "port": 6379,
          "service": "Redis",
          "status": "open",
          "severity": "CRITICAL",
          "probe": "redis",
          "no_auth": true,
          "banner": "Unauthenticated PING/PONG — data directly accessible",
          "detail": "Unauthenticated PING/PONG — data directly accessible",
          "source_url": "https://example.com/admin",
          "timestamp": "2025-05-01 14:31:55"
        }
      ],
      "open_ports": [6379]
    }
  ]
}
```

### `_dbscan_<ts>.txt`

Human-readable report usable as a reference for follow-up tooling:

```
# DorkEye DB Port Scan Report
# Generated : 2025-05-01 14:32:10
# Hosts     : 12
# Open ports: 4
# CRITICAL  : 1  (no-auth confirmed)
# HIGH      : 2

## Host: example.com  (1 open port(s))
  [CRITICAL ] example.com:6379  Redis             NO-AUTH Unauthenticated PING/PONG
```

-----

## Terminal Output

During a scan, findings are printed in real time:

```
[DBScan] Scanning 12 host(s) × 15 port(s) — timeout: 2.5s  threads/host: 60

[DBScan] [1/12] example.com  (hints: [6379])
  [ Open   ] ⚠ CRITICAL  example.com:6379 [Redis] — Unauthenticated PING/PONG
  [ Closed ] 14 port(s) closed / filtered

[DBScan] [2/12] target.io
  [ Open   ] ! HIGH  target.io:27017 [MongoDB] — Open (probe error: ...)
  [ Open   ] ~ MEDIUM  target.io:9200 [Elasticsearch]
  [ Closed ] 13 port(s) closed / filtered
```

Closed ports are summarised as a single line per host to avoid log spam.

-----

## Dependencies

|Package   |Required|Used for                                                                                  |
|----------|--------|------------------------------------------------------------------------------------------|
|`socket`  |stdlib  |TCP connect for all probes                                                                |
|`requests`|optional|HTTP probes (ES, CouchDB, InfluxDB, Neo4j, Riak). Falls back to raw TCP banner if missing.|
|`rich`    |optional|Coloured terminal output. Falls back to plain `print()` if missing.                       |

Install optional dependencies:

```bash
pip install requests rich
```

-----

## Integration Notes

- The DBScan agent is instantiated by `dorkeye.py` after the main search/analysis pipeline
  completes, so it always has a full result set to work from.
- `DBPortScanAgent.run()` accepts the same result list format as the rest of the pipeline
  (`{"url": ..., "title": ..., "snippet": ..., "dork": ...}`).
- The `_exit_requested` and `_skip_current` flags are shared with `sqli.py` so Ctrl+C
  behaviour is consistent across all scanning modules.
- Results are stored in `DBScanReport` and can be serialised independently via
  `report.to_json()` or `report.to_txt_report()`.
