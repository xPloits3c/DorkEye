#!/usr/bin/env python3
"""
DorkEye v3.1 - Advanced OSINT Dorking Tool
Enhanced with SQL injection detection, improved results, and better stealth
This tool was created by @xPloits3c | https://github.com/xPloits3c
"""

import os
import sys
import time
import json
import yaml
import random
import argparse
import hashlib
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
from urllib.parse import urlparse, unquote, parse_qs
from collections import defaultdict, Counter

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from ddgs import DDGS

console = Console()

ASCII_LOGO = """
     \n[bold yellow]  ___[/bold yellow][bold red]
 [bold yellow]__H__[/bold yellow]  [bold white]    Advanced OSINT Dorking Tool [/bold white]
 [bold yellow] [[/bold yellow][bold red],[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red])[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red];[/bold red][bold yellow]][/bold yellow][bold yellow]    DorkEye[bold red] OSINT[/bold red][/bold yellow]
 [bold yellow] |_|[/bold yellow]  [bold red]  ᵛ³ˑ¹_ˣᴾˡᵒⁱᵗˢ³ᶜ [/bold red]
 [bold yellow]  V[/bold yellow]
    \n[bold red]Legal disclaimer:[/bold red][bold yellow] attacking targets without prior mutual consent is illegal.[/bold yellow]
[bold red][!][/bold red][bold yellow] It is the end user's responsibility to obey all applicable local, state and federal laws.[/bold yellow]
"""

USER_AGENTS = {
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ],
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    ]
}

DEFAULT_CONFIG = {
    "extensions": {
        "documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods"],
        "archives": [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2"],
        "databases": [".sql", ".db", ".sqlite", ".mdb"],
        "backups": [".bak", ".backup", ".old", ".tmp"],
        "configs": [".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".xml"],
        "scripts": [".php", ".asp", ".aspx", ".jsp", ".sh", ".bat", ".ps1"],
        "credentials": [".env", ".git", ".svn", ".htpasswd"]
    },
    "blacklist": [],
    "whitelist": [],
    "analyze_files": True,
    "max_file_size_check": 10485760,
    "sqli_detection": False,
    "stealth_mode": False,
    "user_agent_rotation": True
}
class SQLiDetector:
    """Detects potential SQL injection vulnerabilities in URLs"""

    SQLI_PATTERNS = [
        r'\.php\?id=',
        r'\.php\?page=',
        r'\.php\?cat=',
        r'\.php\?product=',
        r'\.php\?item=',
        r'\.asp\?id=',
        r'\.aspx\?id=',
        r'\.jsp\?id=',
    ]

    SQL_ERRORS = [
        r'SQL syntax.*MySQL',
        r'Warning.*mysql_.*',
        r'MySQLSyntaxErrorException',
        r'valid MySQL result',
        r'PostgreSQL.*ERROR',
        r'Warning.*pg_.*',
        r'valid PostgreSQL result',
        r'Npgsql\.',
        r'Driver.* SQL[\-\_\ ]*Server',
        r'OLE DB.* SQL Server',
        r'SQLServer JDBC Driver',
        r'Microsoft SQL Native Client error',
        r'ODBC SQL Server Driver',
        r'SQLite/JDBCDriver',
        r'SQLite.Exception',
        r'System.Data.SQLite.SQLiteException',
        r'Oracle error',
        r'Oracle.*Driver',
        r'Warning.*oci_.*',
    ]

    def __init__(self, stealth: bool = False):
        self.stealth = stealth
        self.sqli_payloads = ["'", "1' OR '1'='1", "1 AND 1=1", "1' AND '1'='1"]

    def is_potential_sqli_url(self, url: str) -> bool:
        """Check if URL matches SQLi patterns"""
        for pattern in self.SQLI_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def test_sqli(self, url: str, user_agent: str) -> Dict:
        """Test URL for SQL injection vulnerability"""
        result = {
            "vulnerable": False,
            "confidence": "none",
            "evidence": [],
            "tested": False
        }

        if not self.is_potential_sqli_url(url):
            return result

        result["tested"] = True

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            if not params:
                return result

            headers = {"User-Agent": user_agent}

            try:
                base_response = requests.get(url, headers=headers, timeout=10, verify=False)
                base_length = len(base_response.text)
            except:
                return result

            for param_name in params.keys():
                for payload in self.sqli_payloads:
                    test_url = url.replace(f"{param_name}={params[param_name][0]}",
                                          f"{param_name}={payload}")

                    try:
                        test_response = requests.get(test_url, headers=headers, timeout=10, verify=False)

                        for error_pattern in self.SQL_ERRORS:
                            if re.search(error_pattern, test_response.text, re.IGNORECASE):
                                result["vulnerable"] = True
                                result["confidence"] = "high"
                                result["evidence"].append(f"SQL error detected with payload: {payload}")
                                return result

                        test_length = len(test_response.text)
                        diff_ratio = abs(test_length - base_length) / base_length if base_length > 0 else 0

                        if diff_ratio > 0.3:
                            result["vulnerable"] = True
                            result["confidence"] = "medium"
                            result["evidence"].append(f"Significant response change with payload: {payload}")

                        if self.stealth:
                            time.sleep(random.uniform(2, 4))

                    except Exception as e:
                        continue

            if result["evidence"] and result["confidence"] == "medium":
                result["confidence"] = "low" if len(result["evidence"]) == 1 else "medium"

        except Exception as e:
            result["error"] = str(e)

        return result
class UserAgentRotator:
    """Rotates user agents for better results"""

    def __init__(self):
        self.agents = []
        for agents_list in USER_AGENTS.values():
            self.agents.extend(agents_list)
        self.current_index = 0

    def get_random(self) -> str:
        """Get random user agent"""
        return random.choice(self.agents)

    def get_next(self) -> str:
        """Get next user agent in rotation"""
        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        return agent


class FileAnalyzer:
    """Analyzes URLs and files found during dorking"""

    def __init__(self, config: Dict, ua_rotator: UserAgentRotator):
        self.config = config
        self.ua_rotator = ua_rotator
        self.extension_map = self._flatten_extensions()
        self.sqli_detector = SQLiDetector(stealth=config.get("stealth_mode", False))

    def _flatten_extensions(self) -> Dict[str, str]:
        """Create a map of extension -> category"""
        ext_map = {}
        for category, extensions in self.config["extensions"].items():
            for ext in extensions:
                ext_map[ext.lower()] = category
        return ext_map

    def get_file_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = os.path.splitext(path)[1].lower()
        return ext if ext else ""

    def categorize_url(self, url: str) -> str:
        """Categorize URL based on extension"""
        ext = self.get_file_extension(url)
        if not ext:
            return "webpage"
        return self.extension_map.get(ext, "other")

    def is_blacklisted(self, url: str) -> bool:
        """Check if URL extension is blacklisted"""
        if not self.config["blacklist"]:
            return False
        ext = self.get_file_extension(url)
        return ext in self.config["blacklist"]

    def is_whitelisted(self, url: str) -> bool:
        """Check if URL extension is whitelisted"""
        if not self.config["whitelist"]:
            return True
        ext = self.get_file_extension(url)
        return ext in self.config["whitelist"]

    def analyze_file(self, url: str) -> Dict:
        """Analyze file metadata (headers only, no download)"""
        result = {
            "url": url,
            "extension": self.get_file_extension(url),
            "category": self.categorize_url(url),
            "size": None,
            "content_type": None,
            "accessible": False,
            "status_code": None
        }

        try:
            headers = {"User-Agent": self.ua_rotator.get_random()}
            response = requests.head(url, timeout=5, allow_redirects=True, headers=headers, verify=False)
            result["status_code"] = response.status_code
            result["accessible"] = response.status_code == 200

            if "content-length" in response.headers:
                result["size"] = int(response.headers["content-length"])

            if "content-type" in response.headers:
                result["content_type"] = response.headers["content-type"]

        except Exception as e:
            result["error"] = str(e)

        return result

    def check_sqli(self, url: str) -> Dict:
        """Check for SQL injection vulnerability"""
        if not self.config.get("sqli_detection", False):
            return {"tested": False}

        return self.sqli_detector.test_sqli(url, self.ua_rotator.get_random())
class DorkEyeEnhanced:
    """Main DorkEye class with enhanced functionality"""

    def __init__(self, config: Dict, output_file: str = None):
        self.config = config
        self.output_file = output_file
        self.ua_rotator = UserAgentRotator()
        self.analyzer = FileAnalyzer(config, self.ua_rotator)
        self.results: List[Dict] = []
        self.stats = defaultdict(int)
        self.url_hashes: Set[str] = set()
        self.start_time = time.time()

    def _hash_url(self, url: str) -> str:
        """Create hash of URL for deduplication"""
        return hashlib.md5(url.encode()).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        """Check if URL is duplicate"""
        url_hash = self._hash_url(url)
        if url_hash in self.url_hashes:
            return True
        self.url_hashes.add(url_hash)
        return False

    def process_dorks(self, dork_input: str) -> List[str]:
        """Process dork input (file or single dork)"""
        if os.path.isfile(dork_input):
            with open(dork_input, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return [dork_input]

    def search_dork(self, dork: str, count: int) -> List[Dict]:
        """Search single dork with improved result gathering"""
        console.print(f"\n[bold green][*] Searching dork:[/bold green] {dork}")
        results = []
        total_fetched = 0
        max_attempts = 3

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Searching DuckDuckGo...", total=count)

            for attempt in range(max_attempts):
                try:
                    ddgs = DDGS()

                    batch_size = min(50, count - total_fetched)
                    if batch_size <= 0:
                        break

                    search_results = ddgs.text(dork, max_results=batch_size)

                    for r in search_results:
                        url = r.get("href") or r.get("url")
                        if not url:
                            continue

                        if self.analyzer.is_blacklisted(url):
                            self.stats["blacklisted"] += 1
                            continue

                        if not self.analyzer.is_whitelisted(url):
                            self.stats["not_whitelisted"] += 1
                            continue

                        if self.is_duplicate(url):
                            self.stats["duplicates"] += 1
                            continue

                        result = {
                            "url": url,
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "dork": dork,
                            "timestamp": datetime.now().isoformat(),
                            "extension": self.analyzer.get_file_extension(url),
                            "category": self.analyzer.categorize_url(url)
                        }

                        results.append(result)
                        total_fetched += 1
                        self.stats["total_found"] += 1
                        self.stats[f"category_{result['category']}"] += 1

                        progress.update(task, completed=min(total_fetched, count))

                        if total_fetched >= count:
                            break

                    if total_fetched >= count:
                        break

                    if attempt < max_attempts - 1 and total_fetched < count:
                        if self.config.get("stealth_mode", False):
                            delay = random.uniform(5, 8)
                        else:
                            delay = random.uniform(2, 4)
                        time.sleep(delay)

                except Exception as e:
                    console.print(f"[yellow][!] Attempt {attempt + 1} failed: {str(e)}[/yellow]")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                    continue

        console.print(f"[bold blue][+] Found {len(results)} unique results for this dork[/bold blue]")
        return results
    def analyze_results(self, results: List[Dict]) -> List[Dict]:
        """Analyze files and check for SQLi in results"""
        if not self.config.get("analyze_files", False) and not self.config.get("sqli_detection", False):
            return results

        console.print("\n[bold yellow][*] Analyzing results...[/bold yellow]")

        files_to_analyze = [r for r in results if r["category"] != "webpage"]
        urls_to_test_sqli = [r for r in results if self.config.get("sqli_detection", False)]

        with Progress(console=console) as progress:
            if self.config.get("analyze_files", False) and files_to_analyze:
                task1 = progress.add_task("[cyan]Analyzing files...", total=len(files_to_analyze))
                for result in files_to_analyze:
                    analysis = self.analyzer.analyze_file(result["url"])
                    result.update({
                        "file_size": analysis["size"],
                        "content_type": analysis["content_type"],
                        "accessible": analysis["accessible"],
                        "status_code": analysis["status_code"]
                    })
                    progress.advance(task1)

                    if self.config.get("stealth_mode", False):
                        time.sleep(random.uniform(1, 2))
                    else:
                        time.sleep(0.5)

            if self.config.get("sqli_detection", False) and urls_to_test_sqli:
                task2 = progress.add_task("[cyan]Testing for SQLi...", total=len(urls_to_test_sqli))
                for result in urls_to_test_sqli:
                    sqli_result = self.analyzer.check_sqli(result["url"])
                    result["sqli_test"] = sqli_result

                    if sqli_result.get("vulnerable", False):
                        self.stats["sqli_vulnerable"] += 1
                        console.print(f"[bold red][!] Potential SQLi found: {result['url']}[/bold red]")

                    progress.advance(task2)

                    if self.config.get("stealth_mode", False):
                        time.sleep(random.uniform(3, 6))

        return results

    def run_search(self, dorks: List[str], count: int):
        """Run search for all dorks"""
        console.print(f"[bold cyan][*] Starting search with {len(dorks)} dork(s)[/bold cyan]\n")

        if self.config.get("stealth_mode", False):
            console.print("[bold magenta][*] Stealth mode: ACTIVE[/bold magenta]")
        if self.config.get("sqli_detection", False):
            console.print("[bold red][*] SQL Injection Detection: ENABLED[/bold red]")

        for index, dork in enumerate(dorks, start=1):
            results = self.search_dork(dork, count)

            if self.config.get("analyze_files", False) or self.config.get("sqli_detection", False):
                results = self.analyze_results(results)

            self.results.extend(results)

            if self.output_file:
                self.save_results()

            if index < len(dorks):
                if self.config.get("stealth_mode", False):
                    delay = round(random.uniform(25, 35), 2)
                else:
                    delay = round(random.uniform(16, 27), 2)

                console.print(f"[yellow][~] Waiting {delay}s before next dork...[/yellow]")
                time.sleep(delay)

                if index % 2 == 0:
                    if self.config.get("stealth_mode", False):
                        long_delay = round(random.uniform(120, 150), 2)
                    else:
                        long_delay = round(random.uniform(85, 110), 2)
                    console.print(f"[bold magenta][~] Extended delay: {long_delay}s (rate limit protection)[/bold magenta]")
                    time.sleep(long_delay)
    def save_results(self):
        """Save results in multiple formats"""
        if not self.output_file:
            return
        
        downloads_folder = os.path.dirname(os.path.abspath(__file__))
        downloads_folder = os.path.join(downloads_folder, "Dump")
        os.makedirs(downloads_folder, exist_ok=True)
         
        base_name = os.path.join(downloads_folder, self.output_file)
        self._save_csv(f"{base_name}.csv")
        self._save_json(f"{base_name}.json")
        self._save_html(f"{base_name}.html")

    def _save_csv(self, filename: str):
        """Save results as CSV with SQLi info"""
        if not self.results:
            return

        fieldnames = [
            "url", "title", "snippet", "dork", "timestamp",
            "extension", "category", "file_size", "content_type",
            "accessible", "status_code", "sqli_vulnerable", "sqli_confidence"
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for result in self.results:
                row = result.copy()
                if "sqli_test" in result:
                    row["sqli_vulnerable"] = result["sqli_test"].get("vulnerable", False)
                    row["sqli_confidence"] = result["sqli_test"].get("confidence", "none")
                writer.writerow(row)

        console.print(f"[green][✓] CSV saved: {filename}[/green]")

    def _save_json(self, filename: str):
        """Save results as JSON with SQLi details"""
        data = {
            "metadata": {
                "total_results": len(self.results),
                "generated_at": datetime.now().isoformat(),
                "sqli_detection_enabled": self.config.get("sqli_detection", False),
                "sqli_vulnerabilities_found": self.stats.get("sqli_vulnerable", 0),
                "stealth_mode": self.config.get("stealth_mode", False),
                "statistics": dict(self.stats)
            },
            "results": self.results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"[green][✓] JSON saved: {filename}[/green]")
    def _save_html(self, filename: str):
        """Save results as HTML report with SQLi warnings"""
        sqli_count = self.stats.get("sqli_vulnerable", 0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DorkEye v3.1 Report</title>
    <style>
        body {{ font-family: 'Courier New', monospace; margin: 20px; background: #0a0a0a; color: #00ff00; }}
        .header {{ background: #1a1a1a; color: #00ff00; padding: 20px; border: 2px solid #00ff00; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }}
        .stat-card {{ background: #1a1a1a; padding: 15px; border: 1px solid #00ff00; }}
        .stat-card h3 {{ margin: 0; color: #00ff00; font-size: 14px; }}
        .stat-card p {{ font-size: 20px; font-weight: bold; margin: 10px 0 0 0; color: #fff; }}
        .sqli-alert {{ background: #330000; border: 2px solid #ff0000; padding: 15px; margin: 20px 0; color: #ff0000; }}
        table {{ width: 100%; border-collapse: collapse; background: #1a1a1a; margin: 20px 0; border: 1px solid #00ff00; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0a0a0a; color: #00ff00; border-bottom: 2px solid #00ff00; }}
        tr:hover {{ background: #2a2a2a; }}
        a {{ color: #00aaff; text-decoration: none; }}
        a:hover {{ color: #00ff00; }}
        .category {{ display: inline-block; padding: 2px 8px; border: 1px solid; font-size: 11px; }}
        .category-documents {{ border-color: #ff6b6b; color: #ff6b6b; }}
        .category-archives {{ border-color: #ffa500; color: #ffa500; }}
        .category-databases {{ border-color: #9b59b6; color: #9b59b6; }}
        .category-backups {{ border-color: #e67e22; color: #e67e22; }}
        .category-configs {{ border-color: #1abc9c; color: #1abc9c; }}
        .category-scripts {{ border-color: #f1c40f; color: #f1c40f; }}
        .category-webpage {{ border-color: #95a5a6; color: #95a5a6; }}
        .sqli-vuln {{ color: #ff0000; font-weight: bold; }}
        .sqli-safe {{ color: #00ff00; }}
        .sqli-untested {{ color: #888; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>┌─[ DorkEye v3.1 - OSINT Report ]</h1>
        <p>└─> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

        if sqli_count > 0:
            html += f"""    <div class="sqli-alert">
        <h2>⚠ SECURITY ALERT ⚠</h2>
        <p><strong>{sqli_count}</strong> potential SQL injection vulnerabilities detected!</p>
        <p>Review the results marked with [SQLI VULN] below.</p>
    </div>
"""

        html += f"""    <div class="stats">
        <div class="stat-card">
            <h3>┌─[ Total Results ]</h3>
            <p>└─> {len(self.results)}</p>
        </div>
        <div class="stat-card">
            <h3>┌─[ Duplicates Filtered ]</h3>
            <p>└─> {self.stats.get('duplicates', 0)}</p>
        </div>
        <div class="stat-card">
            <h3>┌─[ SQLi Vulnerabilities ]</h3>
            <p class="sqli-vuln">└─> {sqli_count}</p>
        </div>
        <div class="stat-card">
            <h3>┌─[ Execution Time ]</h3>
            <p>└─> {round(time.time() - self.start_time, 2)}s</p>
        </div>
    </div>

    <h2>┌─[ Results ]</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>URL</th>
                <th>Title</th>
                <th>Category</th>
                <th>SQLi Status</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>
"""

        for idx, result in enumerate(self.results, 1):
            size = self._format_size(result.get('file_size'))

            sqli_status = "N/A"
            sqli_class = "sqli-untested"

            if "sqli_test" in result and result["sqli_test"].get("tested", False):
                if result["sqli_test"].get("vulnerable", False):
                    confidence = result["sqli_test"].get("confidence", "unknown")
                    sqli_status = f"VULNERABLE ({confidence})"
                    sqli_class = "sqli-vuln"
                else:
                    sqli_status = "SAFE"
                    sqli_class = "sqli-safe"

            html += f"""            <tr>
                <td>{idx}</td>
                <td><a href="{result['url']}" target="_blank">{result['url'][:80]}...</a></td>
                <td>{result.get('title', 'N/A')[:50]}</td>
                <td><span class="category category-{result['category']}">{result['category']}</span></td>
                <td class="{sqli_class}">{sqli_status}</td>
                <td>{size}</td>
            </tr>
"""

        html += """        </tbody>
    </table>
</body>
</html>
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        console.print(f"[green][✓] HTML report saved: {filename}[/green]")
    def _format_size(self, size):
        """Format file size"""
        if size is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def print_statistics(self):
        """Print final statistics in SQLMap style"""
        table = Table(title="", show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        console.print("\n[bold cyan]┌─[ Search Statistics ][/bold cyan]")
        console.print("[bold cyan]│[/bold cyan]")

        table.add_row("├─> Total Results Found", str(self.stats.get("total_found", 0)))
        table.add_row("├─> Unique Results", str(len(self.results)))
        table.add_row("├─> Duplicates Removed", str(self.stats.get("duplicates", 0)))
        table.add_row("├─> Blacklisted", str(self.stats.get("blacklisted", 0)))

        if self.config.get("sqli_detection", False):
            table.add_row("├─> SQLi Vulnerabilities", f"[bold red]{self.stats.get('sqli_vulnerable', 0)}[/bold red]")

        table.add_row("└─> Execution Time", f"{round(time.time() - self.start_time, 2)}s")

        console.print(table)

        categories = {k.replace("category_", ""): v for k, v in self.stats.items() if k.startswith("category_")}
        if categories:
            cat_table = Table(title="", show_header=False, box=None, padding=(0, 2))
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="green", justify="right")

            console.print("\n[bold yellow]┌─[ Results by Category ][/bold yellow]")
            console.print("[bold yellow]│[/bold yellow]")

            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            for i, (category, count) in enumerate(sorted_cats):
                prefix = "└─>" if i == len(sorted_cats) - 1 else "├─>"
                cat_table.add_row(f"{prefix} {category.capitalize()}", str(count))

            console.print(cat_table)
def load_config(config_file: str = None) -> Dict:
    """Load configuration from file or use defaults"""
    if not config_file:
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_file, 'r') as f:
            if config_file.endswith('.json'):
                user_config = json.load(f)
            elif config_file.endswith(('.yaml', '.yml')):
                user_config = yaml.safe_load(f)
            else:
                console.print("[red][!] Unsupported config format. Use JSON or YAML[/red]")
                return DEFAULT_CONFIG.copy()

        config = DEFAULT_CONFIG.copy()
        config.update(user_config)
        return config

    except Exception as e:
        console.print(f"[red][!] Error loading config: {e}[/red]")
        console.print("[yellow][!] Using default configuration[/yellow]")
        return DEFAULT_CONFIG.copy()


def create_sample_config():
    """Create sample configuration file"""
    config_yaml = """# DorkEye v3.1 Configuration

extensions:
  documents: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
  archives: [".zip", ".rar", ".tar", ".gz", ".7z"]
  databases: [".sql", ".db", ".sqlite", ".mdb"]
  backups: [".bak", ".backup", ".old"]
  configs: [".conf", ".config", ".ini", ".yaml", ".json", ".xml"]
  scripts: [".php", ".asp", ".jsp", ".sh"]
  credentials: [".env", ".git", ".htpasswd"]

# Extensions to block (empty = allow all)
blacklist: []

# Extensions to allow (empty = allow all)
whitelist: []

# Analyze file metadata
analyze_files: true

# Enable SQL injection detection
sqli_detection: false

# Enable stealth mode (slower but safer)
stealth_mode: false

# Maximum file size to check (in bytes)
max_file_size_check: 10485760  # 10MB

# Rotate user agents
user_agent_rotation: true
"""

    with open("dorkeye_config.yaml", "w") as f:
        f.write(config_yaml)

    console.print("[green][✓] Sample config created: dorkeye_config.yaml[/green]")
def main():
    parser = argparse.ArgumentParser(
        description="DorkEye v3.1 - Advanced Dorking Tool with SQLi Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d "site:example.com filetype:pdf" -o results
  %(prog)s -d dorks.txt -c 100 -o output --analyze
  %(prog)s -d dorks.txt --config custom_config.yaml --sqli
  %(prog)s -d "inurl:.php?id=" --sqli --stealth -o scan
  %(prog)s --create-config
        """
    )

    parser.add_argument("-d", "--dork", help="Single dork or file containing dorks")
    parser.add_argument("-o", "--output", help="Output filename (without extension)")
    parser.add_argument("-c", "--count", type=int, default=50,
                       help="Results per dork (default: 50)")
    parser.add_argument("--config", help="Configuration file (YAML or JSON)")
    parser.add_argument("--no-analyze", action="store_true",
                       help="Disable file analysis")
    parser.add_argument("--sqli", action="store_true",
                       help="Enable SQL injection detection")
    parser.add_argument("--stealth", action="store_true",
                       help="Enable stealth mode (slower, safer)")
    parser.add_argument("--blacklist", nargs="+",
                       help="Extensions to blacklist (e.g., .pdf .doc)")
    parser.add_argument("--whitelist", nargs="+",
                       help="Extensions to whitelist (e.g., .pdf .xls)")
    parser.add_argument("--create-config", action="store_true",
                       help="Create sample configuration file")

    args = parser.parse_args()

    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    console.print(ASCII_LOGO, style="bold cyan")

    if args.create_config:
        create_sample_config()
        return

    if not args.dork:
        parser.print_help()
        return

    config = load_config(args.config)

    if args.no_analyze:
        config["analyze_files"] = False

    if args.sqli:
        config["sqli_detection"] = True

    if args.stealth:
        config["stealth_mode"] = True

    if args.blacklist:
        config["blacklist"] = args.blacklist

    if args.whitelist:
        config["whitelist"] = args.whitelist

    dorkeye = DorkEyeEnhanced(config, args.output)

    dorks = dorkeye.process_dorks(args.dork)
    console.print(f"[bold cyan]┌─[ LOADED {len(dorks)} DORK(s) ][/bold cyan]")
    console.print(f"[bold cyan]└─>[/bold cyan] Ready to search\n")

    try:
        dorkeye.run_search(dorks, args.count)
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Search interrupted by user[/yellow]")

    dorkeye.print_statistics()

    if args.output:
        console.print(f"\n[bold green]┌─[ Results Saved Successfully ][/bold green]")
        console.print(f"[bold green]├─>[/bold green] CSV:  {args.output}.csv")
        console.print(f"[bold green]├─>[/bold green] JSON: {args.output}.json")
        console.print(f"[bold green]└─>[/bold green] HTML: {args.output}.html")


if __name__ == "__main__":
    main()
    
