"""
dorkeye_patterns.py — Shared pattern library for DorkEye v4.8+
===============================================================
Centralizza pattern, costanti e helper che erano duplicati tra
dorkeye_agents.py e dorkeye_analyze.py:

  - TRIAGE_RULES       — scoring regex per classificazione priorità OSINT
  - SECRET_RULES       — pattern di rilevamento credenziali/secrets (+ hash)
  - SECRET_SEVERITY    — mappa tipo → severity (CRITICAL/HIGH/MEDIUM/LOW)
  - PII_RULES          — pattern PII (email, phone, IBAN, CF, CC, SSN, DOB)
  - SCORE_TO_LABEL     — soglie score → label (CRITICAL/HIGH/MEDIUM/LOW/SKIP)
  - FETCH_UA           — User-Agent condiviso per il fetch pagine
  - FETCH_UA_POOL      — pool UA per rotazione
  - SKIP_EXTENSIONS    — estensioni binarie da non scaricare
  - label_from_score() — funzione di conversione score → label
  - censor()           — mascheratura parziale valori sensibili
  - luhn_check()       — validazione numero carta di credito (Luhn)
"""

from __future__ import annotations

import re
from typing import List, Tuple

# ── Type alias ────────────────────────────────────────────────────────────────
# (category, compiled_pattern, description, has_capture_group)
SecretRule = Tuple[str, re.Pattern, str, bool]

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
    """Converte uno score 0-100 nell'etichetta di priorità corrispondente."""
    for threshold, lbl in SCORE_TO_LABEL:
        if score >= threshold:
            return lbl
    return "SKIP"


# ══════════════════════════════════════════════════════════════════════════════
#  FETCH CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# User-Agent condiviso per il download delle pagine.
FETCH_UA: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Pool di UA per la rotazione (PageFetchAgent+)
FETCH_UA_POOL: list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Estensioni binarie/non-testo: queste URL vengono skippate durante il fetch.
# Versione unificata: superset delle due liste precedenti.
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
    """Censura parzialmente un valore sensibile lasciando visibili 'show' caratteri
    all'inizio e alla fine.

    Esempi:
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
# Ogni entry: (pattern, score_bonus, descrizione)
# Fonte autorevole: dorkeye_analyze.py (19 regole vs 12 di agents.py).
# I punteggi sono stati allineati alla versione analyze.py.

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
    # nuove regole v4.8
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
# Fonte autorevole: dorkeye_analyze.py (42 regole vs 18 di agents.py).
# Ogni entry: (category, compiled_pattern, description, has_capture_group)
# has_capture_group=True  → usare match.group(1) per il valore
# has_capture_group=False → usare match.group(0) per il valore

SECRET_RULES: List[SecretRule] = [
    # ── API Keys ──────────────────────────────────────────────────────────────
    ("API_KEY",    re.compile(r"api[_\-]?key\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",          re.I), "Generic API key",        True),
    ("API_KEY",    re.compile(r"api[_\-]?secret\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",       re.I), "API secret",             True),
    ("API_KEY",    re.compile(r"x[_\-]?api[_\-]?key\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",  re.I), "X-API-Key header value", True),

    # ── Tokens ────────────────────────────────────────────────────────────────
    ("TOKEN",      re.compile(r"(?:access|auth)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{20,})['\"]?",   re.I), "Access/auth token",     True),
    ("TOKEN",      re.compile(r"bearer\s+([A-Za-z0-9\-_.]{20,})",                                           re.I), "Bearer token",          True),
    ("TOKEN",      re.compile(r"(?:secret|private)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{16,})['\"]?",re.I), "Secret token",          True),
    ("TOKEN",      re.compile(r"(?:refresh|session)[_\-]?token\s*[=:]\s*['\"]?([A-Za-z0-9\-_.]{20,})['\"]?",re.I),"Session/refresh token", True),

    # ── Passwords ─────────────────────────────────────────────────────────────
    ("PASSWORD",   re.compile(r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"<>{}\[\]]{6,})['\"]?",       re.I), "Password",              True),
    ("PASSWORD",   re.compile(r"DB_PASS(?:WORD)?\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?",                      re.I), "DB password",           True),
    ("PASSWORD",   re.compile(r"(?:admin|root|user)[_\-]?pass(?:word)?\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?",re.I), "Admin/root password",   True),

    # ── Database connections ──────────────────────────────────────────────────
    ("DB_CONN",    re.compile(r"(mysql|postgresql|postgres|mongodb|redis|mssql|mariadb|sqlite)://[^\s'\"<>]+", re.I), "DB connection URI",   False),
    ("DB_CONN",    re.compile(r"(?:DATABASE_URL|MONGO_URI|REDIS_URL|DB_HOST)\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?", re.I), "DB URI/host env var", True),
    ("DB_CONN",    re.compile(r"(?:DB_NAME|DB_USER)\s*[=:]\s*['\"]?([^\s'\"]{2,})['\"]?",                    re.I), "DB name/user",          True),

    # ── JWT ───────────────────────────────────────────────────────────────────
    ("JWT",        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),                  "JWT token",             False),

    # ── AWS ───────────────────────────────────────────────────────────────────
    ("AWS_KEY",    re.compile(r"AKIA[0-9A-Z]{16}"),                                                                 "AWS Access Key ID",     False),
    ("AWS_KEY",    re.compile(r"aws[_\-]?secret[_\-]?(?:access[_\-]?)?key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?", re.I), "AWS Secret Key", True),
    ("AWS_KEY",    re.compile(r"(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{16,})['\"]?", re.I), "AWS env var", True),

    # ── Google / GCP ──────────────────────────────────────────────────────────
    ("GCP_KEY",    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),                                                           "Google API Key",        False),
    ("GCP_KEY",    re.compile(r"\"type\"\s*:\s*\"service_account\""),                                               "GCP Service Account",   False),
    ("GCP_KEY",    re.compile(r"(?:GOOGLE_API_KEY|FIREBASE_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?", re.I), "Google env var",      True),

    # ── Azure ─────────────────────────────────────────────────────────────────
    ("AZURE_KEY",  re.compile(r"AccountKey=([A-Za-z0-9+/=]{60,})",                                           re.I), "Azure Storage Key",     True),
    ("AZURE_KEY",  re.compile(r"(?:AZURE_CLIENT_SECRET|AZURE_TENANT_ID)\s*[=:]\s*['\"]?([A-Za-z0-9\-]{8,})['\"]?", re.I), "Azure secret",    True),

    # ── Private Keys ──────────────────────────────────────────────────────────
    ("PRIVATE_KEY",re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"),               "Private key",           False),
    ("PRIVATE_KEY",re.compile(r"-----BEGIN\s+CERTIFICATE-----"),                                                     "Certificate",           False),

    # ── Stripe ────────────────────────────────────────────────────────────────
    ("STRIPE_KEY", re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{24,}"),                                                "Stripe Secret Key",     False),
    ("STRIPE_KEY", re.compile(r"pk_(?:live|test)_[A-Za-z0-9]{24,}"),                                                "Stripe Public Key",     False),

    # ── GitHub ────────────────────────────────────────────────────────────────
    ("GITHUB_KEY", re.compile(r"ghp_[A-Za-z0-9]{36}"),                                                              "GitHub Personal Token", False),
    ("GITHUB_KEY", re.compile(r"github[_\-]?(?:token|secret)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?", re.I),  "GitHub token",          True),

    # ── Slack ─────────────────────────────────────────────────────────────────
    ("SLACK_KEY",  re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),                                                    "Slack token",           False),
    ("WEBHOOK",    re.compile(r"https://hooks\.(slack|discord|teams)\.com/[^\s'\"<>]+",                      re.I), "Webhook URL",           False),

    # ── Generic secrets ───────────────────────────────────────────────────────
    ("SECRET",     re.compile(r"(?:client_secret|app_secret|app_key)\s*[=:]\s*['\"]?([A-Za-z0-9\-_]{16,})['\"]?",  re.I), "Client secret",   True),
    ("SECRET",     re.compile(r"(?:encryption_key|signing_key|hmac_key)\s*[=:]\s*['\"]?([A-Za-z0-9\-_+/=]{16,})['\"]?", re.I), "Crypto key", True),

    # ── SSH / FTP credentials ─────────────────────────────────────────────────
    ("SSH_CRED",   re.compile(r"(?:ssh|ftp|sftp)://[^:@\s]{2,}:[^@\s]{4,}@[^\s'\"<>]{4,}",                 re.I), "Protocol with credentials", False),

    # ── .env variables ────────────────────────────────────────────────────────
    ("ENV_VAR",    re.compile(r"^(?:SECRET|KEY|PASS|TOKEN|AUTH|CRED)[A-Z0-9_]*\s*=\s*.{6,}$",           re.M | re.I), ".env secret variable", False),

    # ── Internal IPs ─────────────────────────────────────────────────────────
    ("INTERNAL",   re.compile(r"(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)"), "Internal IP address", False),

    # ── Hash / Digest (v4.8) ──────────────────────────────────────────────────
    ("HASH_BCRYPT", re.compile(r"\$2[ayb]\$\d{2}\$[./A-Za-z0-9]{53}"),                                            "Bcrypt hash",           False),
    ("HASH_MD5",    re.compile(r"\b([a-fA-F0-9]{32})\b"),                                                         "MD5 hash",              False),
    ("HASH_SHA1",   re.compile(r"\b([a-fA-F0-9]{40})\b"),                                                         "SHA-1 hash",            False),
    ("HASH_SHA256", re.compile(r"\b([a-fA-F0-9]{64})\b"),                                                         "SHA-256 hash",          False),
    ("HASH_SHA512", re.compile(r"\b([a-fA-F0-9]{128})\b"),                                                        "SHA-512 hash",          False),
    ("HASH_NTLM",   re.compile(r"\b([a-fA-F0-9]{32}):[a-fA-F0-9]{32}\b"),                                        "NTLM hash pair",        False),

    # ── Cloud / SaaS aggiuntivi (v4.8) ───────────────────────────────────────
    ("TWILIO_KEY",  re.compile(r"SK[a-zA-Z0-9]{32}"),                                                             "Twilio API Key",        False),
    ("SENDGRID",    re.compile(r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}"),                                   "SendGrid API Key",      False),
    ("MAILGUN",     re.compile(r"key-[a-zA-Z0-9]{32}"),                                                           "Mailgun API Key",       False),
    ("HEROKU_KEY",  re.compile(r"heroku[_\-]?(?:api[_\-]?)?key\s*[=:]\s*['\"]?([a-f0-9\-]{36})['\"]?", re.I),   "Heroku API key",        True),
    ("DOCKER_PAT",  re.compile(r"dckr_pat_[A-Za-z0-9_\-]{20,}"),                                                 "Docker PAT",            False),
    ("NPM_TOKEN",   re.compile(r"npm_[A-Za-z0-9]{36}"),                                                           "NPM token",             False),
    ("GITLAB_PAT",  re.compile(r"glpat-[A-Za-z0-9_\-]{20}"),                                                     "GitLab PAT",            False),
]


# ══════════════════════════════════════════════════════════════════════════════
#  SECRET SEVERITY MAP (v4.8)
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
#  PII PATTERNS (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

PiiRule = Tuple[str, re.Pattern, str, bool]

PII_RULES: List[PiiRule] = [
    ("EMAIL",       re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
                    "Email address", False),
    ("PHONE_IT",    re.compile(r"(?:\+39|0039)?\s*(?:0\d{1,3}[\s\-]?\d{6,8}|3\d{2}[\s\-]?\d{6,7})"),
                    "Italian phone number", False),
    ("PHONE_EU",    re.compile(r"\+(?:33|34|44|49|31|32|41|43|48|351|353)\s*[\d\s\-]{7,14}"),
                    "EU phone number", False),
    ("PHONE_US",    re.compile(r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b"),
                    "US phone number", False),
    ("IBAN",        re.compile(r"\b[A-Z]{2}\d{2}[\s]?(?:[A-Z0-9]{4}[\s]?){3,7}[A-Z0-9]{1,4}\b"),
                    "IBAN", False),
    ("CF_IT",       re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPRST]\d{2}[A-Z]\d{3}[A-Z]\b", re.I),
                    "Italian fiscal code", False),
    ("CREDIT_CARD", re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
                    "Credit card number", False),
    ("SSN_US",      re.compile(r"\b(?!000|666|9\d{2})\d{3}[\s\-](?!00)\d{2}[\s\-](?!0000)\d{4}\b"),
                    "US SSN", False),
    ("DOB",         re.compile(
        r"\b(?:nato[/\s]?il|birth[_\s]?date|dob|date[_\s]?of[_\s]?birth)\s*[=:\"']?\s*"
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", re.I),
                    "Date of birth", True),
    ("PASSPORT",    re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
                    "Possible passport number", False),
    ("PUBLIC_IP",   re.compile(
        r"\b(?!10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)(?!127\.)(?!0\.)"
        r"(?:\d{1,3}\.){3}\d{1,3}\b"),
                    "Public IP address", False),
]


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS (v4.8)
# ══════════════════════════════════════════════════════════════════════════════

def luhn_check(number: str) -> bool:
    """Valida un numero di carta di credito con l'algoritmo di Luhn."""
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
