<img width="1536" height="1024" alt="dorkeye-install" src="https://github.com/user-attachments/assets/a0983dc1-2c2e-4cbd-9ab9-7ae1a3743f29" />

# 📦 DorkEye v4.2.6 — Installation Guide

Official installation guide for **DorkEye v4.2.6**  
OSINT & Security Dorking Framework

---

## 🔗 Direct Download

You can download the latest version directly from GitHub:

👉 https://github.com/xPloits3c/DorkEye/archive/refs/tags/DorkEye_v4.2.6.zip  

Or clone the repository:

```bash
git clone https://github.com/xPloits3c/DorkEye.git

========================================

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Quick Installation (recommended)](#-Quick Installation)
5. [CLI Command Mode (optional)](#-CLI)
6. [Verification](#-verification)
7. [Troubleshooting](#-troubleshooting)
8. [Updating DorkEye](#-updating-dorkeye)
9. [Uninstallation](#-uninstallation)
10. [Support](#-support)

========================================

## 🔧 PREREQUISITES
----------------------------------------
Required Software: |   Check Command:  |
----------------------------------------
- Python 3.9+      | python3 --version
- pip (latest)     | pip3 --version
- git (latest)     | git --version

System Requirements:
- Linux / Windows 10+ / macOS 10.14+
- 512 MB RAM minimum
- 100 MB free disk
- Internet connection

========================================

## 🐧 Quick Installation (Recommended)
This method works on Linux, macOS, and Windows.

git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

# Create virtual environment
python3 -m venv dorkeye_env

# Activate virtual environment
# Linux / macOS:
source dorkeye_env/bin/activate
# Windows:
dorkeye_env\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run DorkEye:
python dorkeye.py -h
========================================

## 💻 CLI Command Mode (Optional)
To install DorkEye as a system command:
pip install -e .

Then you can use:
dorkeye --help

This mode is recommended for advanced users.
========================================

## ✅ Verification
Test basic functionality:
python dorkeye.py --create-config
python dorkeye.py -d "python programming" -c 5 -o test

If using CLI mode:
dorkeye --dg=all
========================================

## 🐛 Troubleshooting
ModuleNotFoundError: ddgs
pip uninstall duckduckgo-search -y
pip install ddgs

Externally Managed Environment (Kali Linux)
Always use a virtual environment:
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate

Permission Errors:
Avoid using sudo pip install.
Use a virtual environment instead.
========================================

## 🔄 Updating DorkEye
cd DorkEye
git pull origin main
pip install --upgrade -r requirements.txt

If installed in CLI mode:
pip install -e . --upgrade
========================================

## 🗑️ Uninstallation
Linux / macOS:
rm -rf DorkEye

Windows:
rmdir /s /q DorkEye

To remove only the virtual environment:
rm -rf dorkeye_env
========================================

## 📞 Support
If you encounter issues.
Open an issue on GitHub:
https://github.com/xPloits3c/DorkEye/issues

Please include:
Operating system + version
Python version
Full error message
Steps to reproduce the issue

## ✅ Post-Installation Checklist

- ✔ Python 3.9+
- ✔ Virtual environment active
- ✔ Dependencies installed
- ✔ Test search works
- ✔ Filetype generated
- ✔ --help works
- ✔ Config file created

## 🎯 Installation Complete
DorkEye is now ready to use. Happy hunting. 🔍
