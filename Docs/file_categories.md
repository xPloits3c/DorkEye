# File Categories — DorkEye v4.8

DorkEye automatically categorizes every URL it finds by examining the file extension. Categories drive filtering in the HTML report, export scopes, and the file analysis pipeline.

---

## The 7 Categories

| Category | Extensions | Typical findings |
|----------|-----------|-----------------|
| 📄 **Documents** | `.pdf .doc .docx .xls .xlsx .ppt .pptx .odt .ods` | Reports, contracts, internal presentations, leaked documents |
| 📦 **Archives** | `.zip .rar .tar .gz .7z .bz2` | Source code archives, backup bundles, data exports |
| 🗄️ **Databases** | `.sql .db .sqlite .mdb` | Full database dumps, SQLite databases, Access databases |
| 💾 **Backups** | `.bak .backup .old .tmp` | CMS backups, configuration backups, temporary files left on server |
| ⚙️ **Configs** | `.conf .config .ini .yaml .yml .json .xml` | Web server configs, application settings, CI/CD pipelines |
| 📜 **Scripts** | `.php .asp .aspx .jsp .sh .bat .ps1` | Server-side scripts (often contain DB credentials or business logic) |
| 🔑 **Credentials** | `.env .git .svn .htpasswd` | Environment files, exposed git repos, Apache password files |

URLs with no recognized extension are categorized as **webpage**.

---

## Filter by Category — CLI

### Whitelist (include only)

```bash
# Only scripts
python dorkeye.py -d "site:example.com" --whitelist .php .asp .aspx .jsp -o scripts.json

# Only documents
python dorkeye.py -d "site:example.com" --whitelist .pdf .doc .docx .xls .xlsx -o docs.json

# Only credentials and configs
python dorkeye.py -d "site:example.com" --whitelist .env .git .htpasswd .yaml .conf -o sensitive.json
```

### Blacklist (exclude)

```bash
# Exclude images and media
python dorkeye.py -d "site:example.com" --blacklist .jpg .jpeg .png .gif .svg .mp4 .mp3

# Exclude large archive files
python dorkeye.py -d "site:example.com" --blacklist .zip .rar .tar .gz .7z
```

### Combine

```bash
# Only PHP files, excluding known framework paths
python dorkeye.py -d "site:example.com" --whitelist .php --blacklist .svg .css .js -o php_only.json
```

---

## Filter by Category — HTML Report

The report's filter bar gives one-click access to categories and sub-filters:

| Filter button | Shows |
|--------------|-------|
| `ALL` | Every result |
| `DOC ▼` | Documents + Archives + Backups — sub-filters: PDF / DOCX / XLSX / PPT / Archives |
| `SQLi ▼` | Results with SQLi tests — sub-filters: CRITICAL / VULN / SAFE |
| `SCRIPTS ▼` | Scripts + Configs + Credentials — sub-filters: PHP / ASP / SH-BAT / CONFIGS / CREDS |
| `PAGES` | Webpages only |

The `📁 FILES` export panel lists all non-webpage results and lets you select and download them individually.

---

## Customize Extensions

Edit `dorkeye_config.yaml` to add or remove extensions from any category:

```yaml
extensions:
  documents:
    - ".pdf"
    - ".doc"
    - ".docx"
    - ".xls"
    - ".xlsx"
    - ".ppt"
    - ".pptx"
    - ".odt"
    - ".ods"
    - ".rtf"        # ← add custom extension
  archives:
    - ".zip"
    - ".rar"
    - ".tar"
    - ".gz"
    - ".7z"
    - ".bz2"
  databases:
    - ".sql"
    - ".db"
    - ".sqlite"
    - ".mdb"
  backups:
    - ".bak"
    - ".backup"
    - ".old"
    - ".tmp"
  configs:
    - ".conf"
    - ".config"
    - ".ini"
    - ".yaml"
    - ".yml"
    - ".json"
    - ".xml"
  scripts:
    - ".php"
    - ".asp"
    - ".aspx"
    - ".jsp"
    - ".sh"
    - ".bat"
    - ".ps1"
  credentials:
    - ".env"
    - ".git"
    - ".svn"
    - ".htpasswd"
```

Load the custom config:

```bash
python dorkeye.py -d "site:example.com" --config dorkeye_config.yaml -o results.html
```

Generate the default config as a starting point:

```bash
python dorkeye.py --create-config
```
