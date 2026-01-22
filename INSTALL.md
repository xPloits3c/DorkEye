📦 DorkEye v3.1 — Installation Guide

Complete guide to installing DorkEye on Linux, Windows, and macOS.

---

TABLE OF CONTENTS
1. Prerequisites
2. Linux Installation
3. Windows Installation
4. macOS Installation
5. Manual Installation (All Platforms)
6. Verification
7. Troubleshooting
8. Updating DorkEye
9. Uninstallation
10. Getting Help
11. Post-Installation Checklist

---

PREREQUISITES

Required Software:
- Python 3.8+
- pip (latest)
- git

System Requirements:
- Linux / Windows 10+ / macOS 10.14+
- 512 MB RAM minimum
- 100 MB free disk
- Internet connection

---

LINUX INSTALLATION

Automatic Setup (Recommended)

sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
chmod +x setup.sh
./setup.sh

Test:
source dorkeye_env/bin/activate
python3 dorkeye.py --help

---

WINDOWS INSTALLATION

Automatic Setup

- Install Python (check "Add to PATH")
- Install Git (optional)

git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
setup.bat

Run:
run_dorkeye.bat -d "site:example.com" -o test

---

MACOS INSTALLATION

brew install python3 git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
chmod +x setup.sh
./setup.sh

---

VERIFICATION

python3 dorkeye.py --create-config
python3 dorkeye.py -d "python programming" -c 5 -o test

---

UPDATING

git pull origin main
pip install --upgrade -r requirements.txt

---

UNINSTALL

rm -rf DorkEye  (Linux/macOS)
rmdir /s /q DorkEye  (Windows)

---

Getting Help:
https://github.com/xPloits3c/DorkEye/issues
whitehat.report@onionmail.org
