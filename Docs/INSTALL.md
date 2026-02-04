<img width="1536" height="1024" alt="dorkeye-install" src="https://github.com/user-attachments/assets/a0983dc1-2c2e-4cbd-9ab9-7ae1a3743f29" />

## 📦 DorkEye v3.8 — Installation Guide
- Complete guide to installing DorkEye on Linux, Windows, and macOS.

========================================

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Linux Installation](#-linux-installation)
3. [Windows Installation](#-windows-installation)
4. [macOS Installation](#-macos-installation)
5. [Manual Installation (All Platforms)](#-manual-installation-all-platforms)
6. [Verification](#-verification)
7. [Troubleshooting](#-troubleshooting)
8. [Updating DorkEye](#-updating-dorkeye)
9. [Uninstallation](#-uninstallation)
10. [Getting Help](#-getting-help)
11. [Post-Installation Checklist](#-post-installation-checklist)

========================================

## 🔧 PREREQUISITES
----------------------------------------
Required Software: |   Check Command:  |
----------------------------------------
- Python 3.8+      | python3 --version
- pip (latest)     | pip3 --version
- git              | git --version

System Requirements:
- Linux / Windows 10+ / macOS 10.14+
- 512 MB RAM minimum
- 100 MB free disk
- Internet connection

========================================

## 🐧 LINUX INSTALLATION (Kali, Ubuntu, Debian)

Method 1: Automatic Setup (Recommended)

-     sudo apt update
-     sudo apt install -y python3 python3-pip python3-venv git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     sudo chmod +x setup.sh
-     ./setup.sh

Test:
-     source dorkeye_env/bin/activate
-     python dorkeye.py --help

Method 2: Advanced / Manual Setup

-     sudo apt update
-     sudo apt install -y python3 python3-pip python3-venv git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate
-     pip install --upgrade pip
-     pip install -r requirements.txt
-     python3 dorkeye.py --help

Method 3: Quick Launcher (Optional)
-     sudo nano /usr/local/bin/dorkeye
-     #!/bin/bash
-     cd /path/to/DorkEye
-     source dorkeye_env/bin/activate
-     python3 dorkeye.py "$@"
-     sudo chmod +x /usr/local/bin/dorkeye

Usage:
-     dorkeye -d "your dork" -o results
========================================

## 🪟 WINDOWS INSTALLATION

## Method 1: Automatic Setup (Recommended)

- Install Python (check "Add to PATH")
Download: https://www.python.org/downloads/
✔ Check “Add Python to PATH”
-     python --version

Method 2: Install Git (optional)
Download: https://git-scm.com/download/win
-     git --version

Method 3: Install DorkEye
- Option A: Git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     setup.bat

- Option B: ZIP
-     cd C:\DorkEye
-     setup.bat

4 Run:
-     run_dorkeye.bat -d "site:example.com" -o test

## Method 2: Manual Setup (CMD)
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python -m venv dorkeye_env
-     dorkeye_env\Scripts\activate.bat
-     python -m pip install --upgrade pip
-     pip install -r requirements.txt
-     python dorkeye.py --help

## Method 3: PowerShell (Admin)
- Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python -m venv dorkeye_env-
-     .\dorkeye_env\Scripts\Activate.ps1
-     pip install -r requirements.txt
-     python dorkeye.py --help

========================================

## 🍎 MACOS INSTALLATION
- Method 1: Automatic
-     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
-     brew install python3 git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     chmod +x setup.sh
-     ./setup.sh

- Method 2: Manual
-     xcode-select --install
-     brew install python3
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate
-     pip install -r requirements.txt
-     python3 dorkeye.py --help

## 🔧 Manual Installation (All Platforms)

-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye

- Create venv:
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate   # Linux/macOS
-     python -m venv dorkeye_env
-     dorkeye_env\Scripts\activate.bat  # Windows

- Install deps:
-     pip install --upgrade pip
-     pip install -r requirements.txt
========================================

## ✅ VERIFICATION

-     python3 dorkeye.py --create-config
-     python3 dorkeye.py -d "python programming" -c 5 -o test
========================================

## 🐛 Troubleshooting

- Common Issues
-   ''ModuleNotFoundError: ddgs''
-     pip uninstall duckduckgo-search -y
-     pip install ddgs

- Kali: externally-managed-environment
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate

- Windows scripts disabled
-     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
========================================

## 🔄 Updating DorkEye

-     cd DorkEye
-     git pull origin main
-     source dorkeye_env/bin/activate
-     pip install --upgrade -r requirements.txt
========================================

## 🗑️ Uninstall

- (Linux/macOS)
-     rm -rf DorkEye
- (Windows)
-     rmdir /s /q DorkEye
========================================

## 📞 Getting Help
-     https://github.com/xPloits3c/DorkEye/issues
-     whitehat.report@onionmail.org

Include:
- OS + version
- Python version
- Full error output
- Steps to reproduce

## ✅ Post-Installation Checklist

- ✔ Python 3.8+
- ✔ Virtual environment active
- ✔ Dependencies installed
- ✔ Test search works
- ✔ CSV / JSON / HTML generated
- ✔ --help works
- ✔ Config file created

## 🔍 Installation complete — ready to start dorking!
