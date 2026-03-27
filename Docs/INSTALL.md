<img width="1536" height="1024" alt="dorkeye-install" src="https://github.com/user-attachments/assets/a0983dc1-2c2e-4cbd-9ab9-7ae1a3743f29" />

# 📦 DorkEye — Installation Guide

Official installation guide for **DorkEye Project**.

-----

## ⚡ Quickest Install (PyPI)

```bash
pip install dorkeye
```

No virtual environment needed. Works on Linux, macOS, and Windows.

-----

## 🔗 Download

Clone the repository:

```bash
git clone https://github.com/xPloits3c/DorkEye.git
```

Or download the latest release:
👉 [github.com/xPloits3c/DorkEye/releases](https://github.com/xPloits3c/DorkEye/releases/)

-----

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
1. [Quick Installation (Recommended)](#-quick-installation-recommended)
1. [Termux / Android Installation](#-termux--android-installation)
1. [CLI Command Mode (Optional)](#-cli-command-mode-optional)
1. [Verification](#-verification)
1. [Project Structure](#-project-structure)
1. [Troubleshooting](#-troubleshooting)
1. [Updating DorkEye](#-updating-dorkeye)
1. [Uninstallation](#-uninstallation)
1. [Support](#-support)

-----

## 🔧 Prerequisites

|Required Software|Check Command      |
|-----------------|-------------------|
|Python 3.9+      |`python3 --version`|
|pip (latest)     |`pip3 --version`   |
|git              |`git --version`    |

**System Requirements:**

- Linux / Windows 10+ / macOS 10.14+ / Android (Termux)
- 512 MB RAM minimum
- 100 MB free disk space
- Internet connection

**Key Python Dependencies** (installed automatically via `requirements.txt`):

- `ddgs` — DuckDuckGo search engine
- `requests` — HTTP client
- `rich` — Terminal formatting and progress bars
- `pyyaml` — Configuration and template parsing
- `urllib3` — Low-level HTTP

**Optional Dependencies** (for full feature support):

- `dorkeye_agents.py` in `Tools/` — Enables `--analyze` and `--crawl` features
- `dork_generator.py` in `Tools/` — Enables `--dg` dork generator
- `http_fingerprints.json` — Enables HTTP fingerprint rotation

-----

## 🐧 Quick Installation (Recommended)

This method works on **Linux**, **macOS**, and **Windows**.

```bash
# Clone the repository
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

# Create virtual environment
python3 -m venv dorkeye_env

# Activate virtual environment
# Linux / macOS:
source dorkeye_env/bin/activate

# Windows:
# dorkeye_env\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python dorkeye.py -h
```

-----

## 📱 Termux / Android Installation

DorkEye auto-detects Termux and activates battery-saver mode (reduced timeouts, fewer probe samples). No additional flags needed.

```bash
# Install Python and git
pkg update && pkg upgrade
pkg install python git

# Clone and install
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

# Create virtual environment (recommended to avoid Termux package conflicts)
python -m venv dorkeye_env
source dorkeye_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run
python dorkeye.py --wizard
```

💡 On Termux, DorkEye automatically:

- Reduces connect timeouts (3s vs 4s)
- Lowers SQLi probe/boolean/time-based sample counts
- Displays a `Platform: Android / Termux ⚡ battery-saver active` badge in the banner

-----

## 💻 CLI Command Mode (Optional)

Install DorkEye as a system command for direct access from anywhere:

```bash
pip install -e .
```

Then use:

```bash
dorkeye --help
dorkeye --wizard
dorkeye -d "inurl:admin" -o results.html
```

This mode is recommended for advanced users who want `dorkeye` available globally.

-----

## ✅ Verification

Run these commands to verify everything works:

```bash
# Show help and all available flags
python dorkeye.py -h

# Create a sample config file
python dorkeye.py --create-config

# Quick test search
python dorkeye.py -d "python programming" -c 5 -o test.html

# Test dork generator (if templates are present)
python dorkeye.py --dg=all --mode=soft -c 5 -o dg_test.html

# Launch the interactive wizard
python dorkeye.py --wizard
```

If using CLI mode:

```bash
dorkeye --dg=all -c 5 -o test.html
```

-----

## 📁 Project Structure

```
DorkEye/
├── dorkeye.py                  # Main script
├── requirements.txt            # Python dependencies
├── setup.py                    # CLI install config
├── dorkeye_config.yaml         # Config (generated with --create-config)
├── http_fingerprints.json      # Browser fingerprint profiles
├── Tools/
│   ├── dork_generator.py       # Dork Generator engine (--dg)
│   ├── dorkeye_agents.py       # Analysis + Crawl agents (--analyze, --crawl)
│   ├── dorkeye_analyze.py      # Standalone analysis script
│   └── dorkeye_patterns.py     # Pattern matching utilities
├── Templates/
│   ├── dorks_templates.yaml    # Default dork templates
│   └── *.yaml                  # Additional template files
└── Dump/                       # Output folder (auto-created)
    ├── results.json
    ├── report.html
    └── ...
```

-----

## 🐛 Troubleshooting

### `ModuleNotFoundError: ddgs`

The search engine module has been renamed. Fix:

```bash
pip uninstall duckduckgo-search -y
pip install ddgs
```

### `Externally Managed Environment` (Kali Linux / Debian 12+)

Modern Debian-based systems block global pip installs. Always use a virtual environment:

```bash
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
pip install -r requirements.txt
```

### Permission Errors

**Never** use `sudo pip install`. Use a virtual environment instead.

### `--templates=filename.yaml` syntax error

The `--templates` flag requires `=` syntax (no space):

```bash
# ✅ Correct
python dorkeye.py --dg=sqli --templates=dorks_templates.yaml

# ❌ Wrong
python dorkeye.py --dg=sqli --templates dorks_templates.yaml
```

### `dorkeye_agents.py not found` warning

The `--analyze` and `--crawl` features require `dorkeye_agents.py` in the `Tools/` directory. If missing, DorkEye runs normally but these features are disabled. Ensure your clone is up to date:

```bash
git pull origin main
```

### HTTP Fingerprinting disabled warning

If `http_fingerprints.json` is missing or malformed, DorkEye falls back to basic User-Agent rotation. Re-download the file from the repository.

### SSL/TLS warnings

DorkEye disables SSL verification for maximum compatibility during OSINT scanning. `InsecureRequestWarning` messages are suppressed automatically.

-----

## 🔄 Updating DorkEye

```bash
cd DorkEye
git pull origin main
pip install --upgrade -r requirements.txt
```

If installed in CLI mode:

```bash
pip install -e . --upgrade
```

-----

## 🗑️ Uninstallation

**Linux / macOS:**

```bash
rm -rf DorkEye
```

**Windows:**

```bash
rmdir /s /q DorkEye
```

**Remove only the virtual environment:**

```bash
rm -rf dorkeye_env
```

**If installed in CLI mode:**

```bash
pip uninstall dorkeye
```

-----

## 📞 Support

If you encounter issues, open an issue on GitHub:
👉 [github.com/xPloits3c/DorkEye/issues](https://github.com/xPloits3c/DorkEye/issues)

Please include:

- Operating system + version
- Python version (`python3 --version`)
- Full error message / traceback
- Steps to reproduce the issue
- Whether you’re using a virtual environment

-----

## ✅ Post-Installation Checklist

- ✔ Python 3.9+
- ✔ Virtual environment active
- ✔ Dependencies installed (`pip install -r requirements.txt`)
- ✔ `python dorkeye.py -h` shows help
- ✔ `python dorkeye.py --create-config` creates config
- ✔ Test search works (`-d "test" -c 5 -o test.html`)
- ✔ Dork generator works (`--dg=all -c 5 -o dg_test.html`)
- ✔ Wizard launches (`--wizard`)

-----

## 🎯 Installation Complete

DorkEye v4.8 is ready. Happy hunting. 🔍
