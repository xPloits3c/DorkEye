"""
DorkEye Patterns
======================
dorkeye_patterns.py — Shared pattern library for DorkEye Project
===============================================================
Centralises patterns, constants and helpers that were duplicated between
dorkeye_agents.py and dorkeye_analyze.py:

  - TRIAGE_RULES       — regex scoring for OSINT priority classification
  - SECRET_RULES       — credential/secret detection patterns (+ hashes)
  - SECRET_SEVERITY    — type → severity map (CRITICAL/HIGH/MEDIUM/LOW)
  - PII_RULES          — PII patterns geographically organised:
                           · EMAIL           (global)
                           · PHONE_US        (United States & Canada)
                           · PHONE_EU        (European Union + UK + CH + NO)
                           · PHONE_ME        (Middle East)
                           · PHONE_AS        (Asia-Pacific)
                           · IBAN            (global)
                           · TAX_ID_US       (SSN, EIN)
                           · TAX_ID_EU       (EU VAT / national fiscal codes)
                           · TAX_ID_ME       (Middle East national IDs)
                           · TAX_ID_AS       (Asian national IDs / tax IDs)
                           · CREDIT_CARD     (global, Luhn-validated)
                           · NIN_EU          (EU national identity numbers)
                           · NID_ME          (Middle East national identity numbers)
                           · NID_AS          (Asian national identity numbers)
                           · PASSPORT        (global)
                           · DOB             (global)
                           · PUBLIC_IP       (global)
  - SCORE_TO_LABEL     — score thresholds → label (CRITICAL/HIGH/MEDIUM/LOW/SKIP)
  - FETCH_UA           — shared User-Agent for page fetching
  - FETCH_UA_POOL      — UA pool for rotation
  - SKIP_EXTENSIONS    — binary extensions to skip during fetch
  - label_from_score() — score → label conversion function
  - censor()           — partial masking of sensitive values
  - luhn_check()       — credit card number validation (Luhn algorithm)

Changelog v2.0
--------------
  - PHONE_IT removed; replaced by PHONE_ME (Middle East) and PHONE_AS (Asia-Pacific)
  - CF_IT (Italian fiscal code) removed
  - PII_RULES fully reorganised by geographic area (US / EU / ME / AS)
  - TAX_ID added for all four geographic areas
  - NIN/NID (national identity numbers) added for EU, ME, AS
  - No direct targets; all patterns are generic OSINT-grade
"""

from __future__ import annotations

import re
from typing import List, Tuple

# ── Type aliases ──────────────────────────────────────────────────────────────
# (category, compiled_pattern, description, has_capture_group)
SecretRule = Tuple[str, re.Pattern, str, bool]
PiiRule    = Tuple[str, re.Pattern, str, bool]

# ══════════════════════════════════════════════════════════════════════════════
#  SCORE → LABEL
# ══════════════════════════════════════════════════════════════════════════════

SCORE_TO_LABEL: List[Tuple[int, str]] = [
    (90, "CRITICAL"),
    (70, "HIGH"),
    (50, "MEDIUM"),
    (20, "LOW"),
    (0,  "SKIP"),
]


def label_from_score(score: int) -> str:
    """Converts a score 0-100 to the corresponding priority label."""
    for threshold, lbl in SCORE_TO_LABEL:
        if score >= threshold:
            return lbl
    return "SKIP"


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# Shared User-Agent for page downloads.
FETCH_UA: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# UA pool for rotation (PageFetchAgent+)
FETCH_UA_POOL: list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Binary/non-text extensions: these URLs are skipped during fetch.
SKIP_EXTENSIONS: frozenset = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods",
    ".zip", ".rar", ".tar", ".gz", ".7z", ".bz2",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
    ".mp4", ".mp3", ".avi", ".mov", ".wmv",
    ".exe", ".dll", ".so", ".bin", ".apk",
})


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def censor(value: str, show: int = 4) -> str:
    """Partially masks a sensitive value, leaving 'show' characters visible
    at the start and end.

    Examples:
        censor("sk-abc123xyz456")  → "sk-a…x456"
        censor("ab12")             → "****"
    """
    v = value.strip()
    if len(v) <= show * 2:
        return "*" * len(v)
    return v[:show] + "…" + v[-show:]


# ══════════════════════════════════════════════════════════════════════════════
#  TRIAGE PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
# Each entry: (pattern, score_bonus, description)

TRIAGE_RULES: List[Tuple[re.Pattern, int, str]] = [
    (re.compile(r"\.(env|git|svn|htpasswd|bak|backup|sql|db|sqlite|dump)(\b|$)", re.I), 38, "config/backup exposed"),
    (re.compile(r"phpmyadmin|adminer|pgadmin|webmin|dbadmin",                     re.I), 35, "db admin panel"),
    (re.compile(r"wp-config\.php|configuration\.php|config\.inc\.php",            re.I), 34, "cms config file"),
    (re.compile(r"(?:^|/)\.env(?:\.|$)",                                          re.I), 38, ".env file"),
    (re.compile(r"/admin/|/administrator/|/wp-admin/|/panel/|/cpanel/|/plesk/",   re.I), 22, "admin panel"),
    (re.compile(r"api[_\-]?key|api[_\-]?secret|access[_\-]?token",               re.I), 28, "api credential"),
    (re.compile(r"password|passwd|credentials|credential",                        re.I), 24, "credentials"),
    (re.compile(r"directory\s+listing|index\s+of\s+/",                           re.I), 22, "directory listing"),
    (re.compile(r"config\.php|config\.yml|settings\.py|web\.config|appsettings",  re.I), 28, "config file"),
    (re.compile(r"\.php\?id=\d|\.asp\?id=\d|select\s.+from\s|union\s.+select",   re.I), 26, "sqli candidate"),
    (re.compile(r"wp-content|wordpress",                                          re.I), 12, "wordpress"),
    (re.compile(r"joomla|drupal|magento|prestashop",                              re.I), 14, "cms"),
    (re.compile(r"amazonaws\.com|storage\.googleapis|digitalocean\s*spaces",      re.I), 18, "cloud storage"),
    (re.compile(r"error|exception|stack\s*trace|debug\s*mode|traceback",          re.I), 14, "error/debug leak"),
    (re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY",                         re.I), 45, "private key exposed"),
    (re.compile(r"AKIA[0-9A-Z]{16}",                                                  ), 42, "aws key id"),
    (re.compile(r"(?:ssh|ftp|sftp|telnet)://[^\s]{6,}",                          re.I), 30, "protocol with credentials"),
    (re.compile(r"phpinfo|server-status|server-info",                             re.I), 20, "server info exposed"),
    (re.compile(r"swagger|openapi|api-docs|redoc",                                re.I), 16, "api docs exposed"),
    (re.compile(r"login|signin|logon",                                            re.I),  8, "login page"),
    # v4.8+
    (re.compile(r"jenkins|gitlab|github|bitbucket|sonarqube",                    re.I), 18, "devops panel"),
    (re.compile(r"kibana|grafana|prometheus|splunk|elasticsearch",                re.I), 22, "monitoring/log panel"),
    (re.compile(r"docker|kubernetes|k8s|helm|rancher",                            re.I), 16, "container infra"),
    (re.compile(r"\.log$|error\.log|access\.log|debug\.log",                     re.I), 20, "log file"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",                       ), 36, "jwt token"),
    (re.compile(r"AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}",                         ), 42, "cloud api key"),
    (re.compile(r"inurl:upload|inurl:shell|inurl:cmd|inurl:exec",                re.I), 30, "rce candidate"),
    (re.compile(r"xmlrpc\.php|eval\(|base64_decode\(",                           re.I), 24, "code injection hint"),
]


# ══════════════════════════════════════════════════════════════════════════════
#  SECRET PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
# Each entry: (category, compiled_pattern, description, has_capture_group)
# has_capture_group=True  → use match.group(1) for the value
# has_capture_group=False → use match.group(0) for the value

SECRET_RULES: List[SecretRule] = [
    # ── API Keys ──────────────────────────────────────────────────────────────
    ("API_KEY",    re.compile(r"api[_\-]?key\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",          re.I), "Generic API key",        True),
    ("API_KEY",    re.compile(r"api[_\-]?secret\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",       re.I), "API secret",             True),
    ("API_KEY",    re.compile(r"x[_\-]?api[_\-]?key\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",  re.I), "X-API-Key header value", True),

    # ── Tokens ────────────────────────────────────────────────────────────────
    ("TOKEN",      re.compile(r"(?:access|auth)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{20,})['\"]?",    re.I), "Access/auth token",     True),
    ("TOKEN",      re.compile(r"bearer\s+([A-Za-z0-9\-_.]{20,})",                                            re.I), "Bearer token",          True),
    ("TOKEN",      re.compile(r"(?:secret|private)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{16,})['\"]?", re.I), "Secret token",          True),
    ("TOKEN",      re.compile(r"(?:refresh|session)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{20,})['\"]?",re.I), "Session/refresh token", True),

    # ── Passwords ─────────────────────────────────────────────────────────────
    ("PASSWORD",   re.compile(r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"<>{}\[\]]{6,})['\"]?",        re.I), "Password",              True),
    ("PASSWORD",   re.compile(r"DB_PASS(?:WORD)?\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?",                       re.I), "DB password",           True),
    ("PASSWORD",   re.compile(r"(?:admin|root|user)[_\-]?pass(?:word)?\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?", re.I), "Admin/root password",   True),

    # ── Database connections ──────────────────────────────────────────────────
    ("DB_CONN",    re.compile(r"(mysql|postgresql|postgres|mongodb|redis|mssql|mariadb|sqlite)://[^\s'\"<>]+", re.I), "DB connection URI",    False),
    ("DB_CONN",    re.compile(r"(?:DATABASE_URL|MONGO_URI|REDIS_URL|DB_HOST)\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?", re.I), "DB URI/host env var", True),
    ("DB_CONN",    re.compile(r"(?:DB_NAME|DB_USER)\s*[=:]\s*['\"]?([^\s'\"]{2,})['\"]?",                     re.I), "DB name/user",          True),

    # ── JWT ───────────────────────────────────────────────────────────────────
    ("JWT",        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),                   "JWT token",             False),

    # ── AWS ───────────────────────────────────────────────────────────────────
    ("AWS_KEY",    re.compile(r"AKIA[0-9A-Z]{16}"),                                                                  "AWS Access Key ID",     False),
    ("AWS_KEY",    re.compile(r"aws[_\-]?secret[_\-]?(?:access[_\-]?)?key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?", re.I), "AWS Secret Key", True),
    ("AWS_KEY",    re.compile(r"(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{16,})['\"]?", re.I), "AWS env var",  True),

    # ── Google / GCP ──────────────────────────────────────────────────────────
    ("GCP_KEY",    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),                                                            "Google API Key",        False),
    ("GCP_KEY",    re.compile(r"\"type\"\s*:\s*\"service_account\""),                                                 "GCP Service Account",   False),
    ("GCP_KEY",    re.compile(r"(?:GOOGLE_API_KEY|FIREBASE_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?", re.I), "Google env var",       True),

    # ── Azure ─────────────────────────────────────────────────────────────────
    ("AZURE_KEY",  re.compile(r"AccountKey=([A-Za-z0-9+/=]{60,})",                                            re.I), "Azure Storage Key",     True),
    ("AZURE_KEY",  re.compile(r"(?:AZURE_CLIENT_SECRET|AZURE_TENANT_ID)\s*[=:]\s*['\"]?([A-Za-z0-9\-]{8,})['\"]?", re.I), "Azure secret",    True),

    # ── Private Keys ──────────────────────────────────────────────────────────
    ("PRIVATE_KEY",re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"),                "Private key",           False),
    ("PRIVATE_KEY",re.compile(r"-----BEGIN\s+CERTIFICATE-----"),                                                      "Certificate",           False),

    # ── Stripe ────────────────────────────────────────────────────────────────
    ("STRIPE_KEY", re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{24,}"),                                                 "Stripe Secret Key",     False),
    ("STRIPE_KEY", re.compile(r"pk_(?:live|test)_[A-Za-z0-9]{24,}"),                                                 "Stripe Public Key",     False),

    # ── GitHub ────────────────────────────────────────────────────────────────
    ("GITHUB_KEY", re.compile(r"ghp_[A-Za-z0-9]{36}"),                                                               "GitHub Personal Token", False),
    ("GITHUB_KEY", re.compile(r"github[_\-]?(?:token|secret)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?", re.I),   "GitHub token",          True),

    # ── Slack ─────────────────────────────────────────────────────────────────
    ("SLACK_KEY",  re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),                                                     "Slack token",           False),
    ("WEBHOOK",    re.compile(r"https://hooks\.(slack|discord|teams)\.com/[^\s'\"<>]+",                       re.I),  "Webhook URL",           False),

    # ── Generic secrets ───────────────────────────────────────────────────────
    ("SECRET",     re.compile(r"(?:client_secret|app_secret|app_key)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{16,})['\"]?",   re.I), "Client secret",   True),
    ("SECRET",     re.compile(r"(?:encryption_key|signing_key|hmac_key)\s*[=:]\s*['\"]?([A-Za-z0-9\-_+/=]{16,})['\"]?", re.I), "Crypto key",  True),

    # ── SSH / FTP credentials ─────────────────────────────────────────────────
    ("SSH_CRED",   re.compile(r"(?:ssh|ftp|sftp)://[^:@\s]{2,}:[^@\s]{4,}@[^\s'\"<>]{4,}",                  re.I),  "Protocol with credentials", False),

    # ── .env variables ────────────────────────────────────────────────────────
    ("ENV_VAR",    re.compile(r"^(?:SECRET|KEY|PASS|TOKEN|AUTH|CRED)[A-Z0-9_]*\s*=\s*.{6,}$",            re.M | re.I), ".env secret variable", False),

    # ── Internal IPs ──────────────────────────────────────────────────────────
    ("INTERNAL",   re.compile(r"(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)"), "Internal IP address", False),

    # ── Hash / Digest ─────────────────────────────────────────────────────────
    ("HASH_BCRYPT", re.compile(r"\$2[ayb]\$\d{2}\$[./A-Za-z0-9]{53}"),                                              "Bcrypt hash",           False),
    ("HASH_MD5",    re.compile(r"\b([a-fA-F0-9]{32})\b"),                                                            "MD5 hash",              False),
    ("HASH_SHA1",   re.compile(r"\b([a-fA-F0-9]{40})\b"),                                                            "SHA-1 hash",            False),
    ("HASH_SHA256", re.compile(r"\b([a-fA-F0-9]{64})\b"),                                                            "SHA-256 hash",          False),
    ("HASH_SHA512", re.compile(r"\b([a-fA-F0-9]{128})\b"),                                                           "SHA-512 hash",          False),
    ("HASH_NTLM",   re.compile(r"\b([a-fA-F0-9]{32}):[a-fA-F0-9]{32}\b"),                                           "NTLM hash pair",        False),

    # ── Additional Cloud / SaaS ───────────────────────────────────────────────
    ("TWILIO_KEY",  re.compile(r"SK[a-zA-Z0-9]{32}"),                                                                "Twilio API Key",        False),
    ("SENDGRID",    re.compile(r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}"),                                      "SendGrid API Key",      False),
    ("MAILGUN",     re.compile(r"key-[a-zA-Z0-9]{32}"),                                                              "Mailgun API Key",       False),
    ("HEROKU_KEY",  re.compile(r"heroku[_\-]?(?:api[_\-]?)?key\s*[=:]\s*['\"]?([a-f0-9\-]{36})['\"]?",    re.I),   "Heroku API key",        True),
    ("DOCKER_PAT",  re.compile(r"dckr_pat_[A-Za-z0-9_\-]{20,}"),                                                    "Docker PAT",            False),
    ("NPM_TOKEN",   re.compile(r"npm_[A-Za-z0-9]{36}"),                                                              "NPM token",             False),
    ("GITLAB_PAT",  re.compile(r"glpat-[A-Za-z0-9_\-]{20}"),                                                        "GitLab PAT",            False),
]


# ══════════════════════════════════════════════════════════════════════════════
#  SECRET SEVERITY MAP
# ══════════════════════════════════════════════════════════════════════════════

SECRET_SEVERITY: dict = {
    "PRIVATE_KEY":  "CRITICAL",
    "AWS_KEY":      "CRITICAL",
    "HASH_BCRYPT":  "CRITICAL",
    "HASH_NTLM":    "CRITICAL",
    "STRIPE_KEY":   "CRITICAL",
    "DB_CONN":      "HIGH",
    "JWT":          "HIGH",
    "GCP_KEY":      "HIGH",
    "AZURE_KEY":    "HIGH",
    "GITHUB_KEY":   "HIGH",
    "SENDGRID":     "HIGH",
    "PASSWORD":     "HIGH",
    "TWILIO_KEY":   "HIGH",
    "GITLAB_PAT":   "HIGH",
    "DOCKER_PAT":   "HIGH",
    "NPM_TOKEN":    "HIGH",
    "API_KEY":      "MEDIUM",
    "TOKEN":        "MEDIUM",
    "SECRET":       "MEDIUM",
    "SLACK_KEY":    "MEDIUM",
    "WEBHOOK":      "MEDIUM",
    "MAILGUN":      "MEDIUM",
    "HEROKU_KEY":   "MEDIUM",
    "SSH_CRED":     "MEDIUM",
    "ENV_VAR":      "MEDIUM",
    "HASH_MD5":     "LOW",
    "HASH_SHA1":    "LOW",
    "HASH_SHA256":  "LOW",
    "HASH_SHA512":  "LOW",
    "INTERNAL":     "LOW",
}


# ══════════════════════════════════════════════════════════════════════════════
#  PII PATTERNS v2.0 — Geographic organisation
#  Areas covered: US · EU · Middle East (ME) · Asia-Pacific (AS)
# ══════════════════════════════════════════════════════════════════════════════
#
#  Structure per category:
#  ┌─────────────────┬──────────────────────────────────────────────────────┐
#  │ Category        │ Geographic variants                                  │
#  ├─────────────────┼──────────────────────────────────────────────────────┤
#  │ EMAIL           │ global (single rule)                                 │
#  │ PHONE           │ PHONE_US · PHONE_EU · PHONE_ME · PHONE_AS           │
#  │ IBAN            │ global (covers EU + ME + select AS)                  │
#  │ TAX_ID          │ TAX_ID_US · TAX_ID_EU · TAX_ID_ME · TAX_ID_AS       │
#  │ NIN / NID       │ NIN_EU · NID_ME · NID_AS                            │
#  │ CREDIT_CARD     │ global (Luhn-validated by luhn_check())              │
#  │ SSN_US          │ US Social Security Number                            │
#  │ DOB             │ global                                               │
#  │ PASSPORT        │ global                                               │
#  │ PUBLIC_IP       │ global                                               │
#  └─────────────────┴──────────────────────────────────────────────────────┘

PII_RULES: List[PiiRule] = [

    # ══════════════════════════════════════════════════════════════════════════
    #  EMAIL — global
    # ══════════════════════════════════════════════════════════════════════════
    ("EMAIL",
     re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
     "Email address (global)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  PHONE — United States & Canada
    #  Formats: (NXX) NXX-XXXX · NXX-NXX-XXXX · +1 NXX NXX XXXX
    # ══════════════════════════════════════════════════════════════════════════
    ("PHONE_US",
     re.compile(r"\b(?:\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"),
     "Phone number — US/Canada (+1)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  PHONE — European Union + UK + CH + NO
    #  Country codes: +30 GR · +31 NL · +32 BE · +33 FR · +34 ES · +39 IT
    #                 +40 RO · +41 CH · +43 AT · +44 UK · +45 DK · +46 SE
    #                 +47 NO · +48 PL · +49 DE · +351 PT · +353 IE · +358 FI
    #                 +370 LT · +371 LV · +372 EE · +420 CZ · +421 SK
    # ══════════════════════════════════════════════════════════════════════════
    ("PHONE_EU",
     re.compile(
         r"\+(?:3[0-49]|4[1-9]|35[138]|37[012]|42[01])"
         r"[\s\-.]?[\d][\d\s\-\.]{6,13}\b",
         re.I),
     "Phone number — EU/UK/CH/NO", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  PHONE — Middle East
    #  Country codes: +20 EG · +90 TR · +92 PK* · +93 AF · +98 IR
    #                 +961 LB · +962 JO · +963 SY · +964 IQ · +965 KW
    #                 +966 SA · +967 YE · +968 OM · +970 PS · +971 AE
    #                 +972 IL · +973 BH · +974 QA · +975* · +976* · +977 NP*
    #  (* shared prefix — patterns constrained by digit length)
    # ══════════════════════════════════════════════════════════════════════════
    ("PHONE_ME",
     re.compile(
         r"\+(?:20|90|93|98|96[1-8]|97[012])"
         r"[\s\-.]?[\d][\d\s\-\.]{6,12}\b",
         re.I),
     "Phone number — Middle East", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  PHONE — Asia-Pacific
    #  Country codes: +60 MY · +61 AU · +62 ID · +63 PH · +64 NZ · +65 SG
    #                 +66 TH · +81 JP · +82 KR · +84 VN · +86 CN · +852 HK
    #                 +853 MO · +855 KH · +856 LA · +880 BD · +886 TW
    #                 +91 IN · +92 PK · +94 LK · +95 MM
    # ══════════════════════════════════════════════════════════════════════════
    ("PHONE_AS",
     re.compile(
         r"\+(?:6[0-6]|8[124689]|85[2-6]|88[06])"
         r"[\s\-.]?[\d][\d\s\-\.]{6,13}\b",
         re.I),
     "Phone number — Asia-Pacific", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  IBAN — global
    #  Covers EU, UK, Middle East (AE, SA, QA, KW, BH), and others.
    # ══════════════════════════════════════════════════════════════════════════
    ("IBAN",
     re.compile(r"\b[A-Z]{2}\d{2}[\s]?(?:[A-Z0-9]{4}[\s]?){3,7}[A-Z0-9]{1,4}\b"),
     "IBAN (global)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  TAX ID — United States
    #  Patterns: SSN (NNN-NN-NNNN), EIN (NN-NNNNNNN)
    # ══════════════════════════════════════════════════════════════════════════
    ("TAX_ID_US",
     re.compile(r"\b(?!000|666|9\d{2})\d{3}[\s\-](?!00)\d{2}[\s\-](?!0000)\d{4}\b"),
     "Tax ID — US SSN", False),

    ("TAX_ID_US",
     re.compile(r"\b\d{2}\-\d{7}\b"),
     "Tax ID — US EIN (Employer Identification Number)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  TAX ID — European Union
    #  Generic EU VAT number: 2-letter country code + 8–12 alphanumeric chars.
    #  Covers: DE · FR · GB · IT · ES · NL · PL · PT · SE · BE · AT · DK · FI
    # ══════════════════════════════════════════════════════════════════════════
    ("TAX_ID_EU",
     re.compile(
         r"\b(?:AT|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|GB|HR|HU|IE|IT"
         r"|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK)"
         r"[0-9A-Z]{8,12}\b",
         re.I),
     "Tax ID — EU VAT number", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  TAX ID — Middle East
    #  Patterns: generic 10–15 digit national tax / trade registration numbers
    #  used in SA (VAT: 15 digits), AE (TRN: 15 digits), EG (9 digits), TR (10 digits)
    # ══════════════════════════════════════════════════════════════════════════
    ("TAX_ID_ME",
     re.compile(
         r"(?:"
         r"(?:tax[_\s\-]?(?:id|number|no)|vat[_\s\-]?(?:id|number|no)|trn|crn)"
         r"\s*[=:\"']?\s*"
         r")"
         r"([0-9]{9,15})\b",
         re.I),
     "Tax ID — Middle East (SA/AE/EG/TR/IR)", True),

    # ══════════════════════════════════════════════════════════════════════════
    #  TAX ID — Asia-Pacific
    #  Patterns: CN (18-char USC), IN (PAN: 10 alphanumeric), JP (12 digits),
    #            KR (10 digits), SG (UEN: 9-10 chars), AU (ABN: 11 digits)
    # ══════════════════════════════════════════════════════════════════════════
    ("TAX_ID_AS",
     re.compile(
         r"\b(?:"
         r"[A-Z]{5}\d{4}[A-Z]"                        # IN PAN card
         r"|\d{18}"                                    # CN Unified Social Credit Code
         r"|\d{12}"                                    # JP My Number / KR TRN
         r"|[0-9A-Z]{9,10}"                            # SG UEN
         r"|\d{11}"                                    # AU ABN
         r")\b",
         re.I),
     "Tax ID — Asia-Pacific (IN/CN/JP/KR/SG/AU)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  NATIONAL IDENTITY NUMBER — European Union
    #  Generic NIN keyword-anchored detection; avoids country-specific hardcoding.
    #  Covers: NL BSN (9 digits), SE personnummer (10/12 digits + separator),
    #          DE SVNR (12 digits), FR NIR (15 digits), PL PESEL (11 digits)
    # ══════════════════════════════════════════════════════════════════════════
    ("NIN_EU",
     re.compile(
         r"(?:national[_\s]?id(?:entity)?[_\s]?(?:number|no|code)?|"
         r"social[_\s]?security[_\s]?(?:number|no)|"
         r"bsn|pesel|personnummer|svnr|nir|codice[_\s]?fiscale)"
         r"\s*[=:\"']?\s*"
         r"([A-Z0-9\-]{6,20})\b",
         re.I),
     "National Identity Number — EU", True),

    # ══════════════════════════════════════════════════════════════════════════
    #  NATIONAL IDENTITY NUMBER — Middle East
    #  SA National ID (10 digits starting with 1 or 2),
    #  AE Emirates ID (784-YYYY-NNNNNNN-C), EG National ID (14 digits),
    #  TR TC Kimlik (11 digits), IR National Code (10 digits),
    #  IL Teudat Zehut (9 digits)
    # ══════════════════════════════════════════════════════════════════════════
    ("NID_ME",
     re.compile(
         r"(?:national[_\s]?id(?:entity)?[_\s]?(?:number|no|card)?|"
         r"emirates[_\s]?id|kimlik|iqama|civil[_\s]?id|"
         r"nid|nin)"
         r"\s*[=:\"']?\s*"
         r"([0-9\-]{9,18})\b",
         re.I),
     "National Identity Number — Middle East", True),

    ("NID_ME",
     re.compile(r"\b784[\-]?\d{4}[\-]?\d{7}[\-]?\d\b"),
     "Emirates ID — AE (784-YYYY-NNNNNNN-C)", False),

    ("NID_ME",
     re.compile(r"\b[12]\d{9}\b"),
     "National ID — SA (10 digits, starts with 1 or 2)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  NATIONAL IDENTITY NUMBER — Asia-Pacific
    #  IN Aadhaar (12 digits), CN Resident ID (18 chars), KR RRN (13 digits),
    #  SG NRIC (S/T/F/G + 7 digits + 1 char), HK HKID (7–8 digits + check char),
    #  JP My Number (12 digits, keyword-anchored), AU TFN (8–9 digits)
    # ══════════════════════════════════════════════════════════════════════════
    ("NID_AS",
     re.compile(
         r"(?:aadhaar|aadhar|uid|my[_\s]?number|resident[_\s]?(?:registration[_\s]?)?number|"
         r"nric|hkid|tfn|tax[_\s]?file[_\s]?number)"
         r"\s*[=:\"']?\s*"
         r"([A-Z0-9\-]{8,18})\b",
         re.I),
     "National Identity Number — Asia-Pacific", True),

    ("NID_AS",
     re.compile(r"\b[STFG]\d{7}[A-Z]\b"),
     "NRIC — Singapore", False),

    ("NID_AS",
     re.compile(r"\b\d{6}[\-]?\d{7}\b"),
     "Resident Registration Number — South Korea (YYMMDD-NNNNNNN)", False),

    ("NID_AS",
     re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
     "Aadhaar number — India (XXXX XXXX XXXX)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  CREDIT CARD — global
    #  Visa · Mastercard · Amex · Discover
    #  Post-match validation: use luhn_check() to filter false positives.
    # ══════════════════════════════════════════════════════════════════════════
    ("CREDIT_CARD",
     re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
     "Credit card number (global)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  SSN — United States (standalone, without TAX_ID_US keyword anchor)
    # ══════════════════════════════════════════════════════════════════════════
    ("SSN_US",
     re.compile(r"\b(?!000|666|9\d{2})\d{3}[\s\-](?!00)\d{2}[\s\-](?!0000)\d{4}\b"),
     "US Social Security Number (SSN)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  DATE OF BIRTH — global (keyword-anchored)
    # ══════════════════════════════════════════════════════════════════════════
    ("DOB",
     re.compile(
         r"\b(?:birth[_\s]?date|date[_\s]?of[_\s]?birth|dob|born[_\s]?on|"
         r"fecha[_\s]?nac|data[_\s]?nasc|geburts(?:datum|tag)|"
         r"تاريخ[_\s]?الميلاد|出生[日期年月]|생년월일)"
         r"\s*[=:\"']?\s*"
         r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
         re.I),
     "Date of birth (global)", True),

    # ══════════════════════════════════════════════════════════════════════════
    #  PASSPORT — global (generic machine-readable format)
    # ══════════════════════════════════════════════════════════════════════════
    ("PASSPORT",
     re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
     "Possible passport number (global)", False),

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC IP — global
    # ══════════════════════════════════════════════════════════════════════════
    ("PUBLIC_IP",
     re.compile(
         r"\b(?!10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)(?!127\.)(?!0\.)"
         r"(?:\d{1,3}\.){3}\d{1,3}\b"),
     "Public IP address (global)", False),
]


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def luhn_check(number: str) -> bool:
    """Validates a credit card number using the Luhn algorithm.

    Returns True if the number passes the Luhn check; False otherwise.
    Non-digit characters (spaces, dashes) are stripped before validation.
    """
    import re as _re
    digits = [int(d) for d in _re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
