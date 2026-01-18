📦 DorkEye v3.0 - Installation Guide
Complete installation instructions for all platforms.

📋 Table of Contents
- Prerequisites
- Linux Installation
- Windows Installation
- macOS Installation
-Manual Installation
-Verification
-Troubleshooting
-Prerequisites
--Required Software

Software	Minimum  Version	Check Command
- Python	3.8+	-   python3 --version
- pip	Latest	-   pip3 --version
- git	Any	-   git --version

System Requirements
- OS: Linux, Windows 10+, macOS 10.14+
- RAM: 512 MB minimum
- Disk: 100 MB free space
- Network: Internet connection for searches

🐧 Linux Installation (Kali, Ubuntu, Debian)
Method 1: Automatic Setup (Recommended)

1. Install prerequisites
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

2. Clone repository
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

3. Run automatic setup
chmod +x setup.sh
./setup.sh

4. Test installation
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
python3 dorkeye.py --help


-- ADVANCED --
1. Install Python and dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

2. Create virtual environment
python3 -m venv dorkeye_env

3. Activate environment
source dorkeye_env/bin/activate

4. Upgrade pip
pip install --upgrade pip

5. Install requirements
pip install -r requirements.txt

6. Verify installation
python3 dorkeye.py --help

Method 3: Quick Launcher Setup
After installation, create a system-wide launcher:

Create launcher script
sudo nano /usr/local/bin/dorkeye

Paste this content:
#!/bin/bash
cd /path/to/DorkEye
source dorkeye_env/bin/activate
python3 dorkeye.py "$@"

Save and make executable
sudo chmod +x /usr/local/bin/dorkeye
Now use from anywhere:
dorkeye -d "your dork" -o results

  🪟 Windows Installation
    -  Method 1: Automatic Setup (Recommended)
    -  Step 1: Install Python
    -  Download Python from https://www.python.org/downloads/
    -  Run installer

  ⚠️ IMPORTANT: Check "Add Python to PATH"
    -  Click "Install Now"
    -  Verify installation:
    -    cmd
    -    python --version

    - Step 2: Install Git (Optional)
    - Download from https://git-scm.com/download/win
    - Run installer with default settings
    - Verify:
    -    cmd
    -    git --version

    - Step 3: Install DorkEye
    - Option A: With Git
    -    cmd
    -    git clone https://github.com/xPloits3c/DorkEye.git
    -    cd DorkEye
    -    setup.bat
    - Option B: Manual Download
    -    Download ZIP from GitHub
    -    Extract to C:\DorkEye
    -    Open Command Prompt:
    -    cmd
    -    cd C:\DorkEye
    -    setup.bat

    - Step 4: Run DorkEye
    -    cmd
    -    run_dorkeye.bat -d "site:example.com" -o test
 Method 2: Manual Setup (Windows)
    -    cmd

REM 1. Clone or download repository
-  git clone https://github.com/xPloits3c/DorkEye.git
-  cd DorkEye

REM 2. Create virtual environment
-  python -m venv dorkeye_env

REM 3. Activate environment
-  dorkeye_env\Scripts\activate.bat

REM 4. Upgrade pip
-  python -m pip install --upgrade pip

REM 5. Install requirements
-  pip install -r requirements.txt

REM 6. Test
-  python dorkeye.py --help

Method 3: PowerShell Installation

Run as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Clone repository
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye

Create and activate environment
python -m venv dorkeye_env
.\dorkeye_env\Scripts\Activate.ps1

Install dependencies
pip install -r requirements.txt

TEST
python dorkeye.py --help

🍎 macOS Installation
Method 1: Automatic Setup

1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

2. Install Python
  brew install python3 git

3. Clone repository
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye

4. Run setup
  chmod +x setup.sh
  ./setup.sh

5. Test
  source dorkeye_env/bin/activate
  python3 dorkeye.py --help
  Method 2: Manual Setup
  bash

1. Install Xcode Command Line Tools
  xcode-select --install

2. Install Python (if needed)
  brew install python3

3. Clone repository
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye

4. Create virtual environment
  python3 -m venv dorkeye_env

5. Activate
  source dorkeye_env/bin/activate

6. Install dependencies
  pip install -r requirements.txt

7. Verify
  python3 dorkeye.py --help

🔧 Manual Installation (All Platforms) Step-by-Step Process
  Download Files
Option A: Using Git
  bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye

Option B: Manual Download
Visit https://github.com/xPloits3c/DorkEye
Click "Code" → "Download ZIP"
Extract archive
Open terminal/cmd in extracted folder

2. Create Virtual Environment
Linux/macOS:
  bash
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate

Windows:
  cmd
  python -m venv dorkeye_env
  dorkeye_env\Scripts\activate.bat

3. Install Dependencies
Upgrade pip first
  pip install --upgrade pip
  Install from requirements.txt
  pip install -r requirements.txt

OR install manually:
  pip install requests PyYAML rich ddgs

4. Verify Installation
Check Python packages
  pip list | grep -E "(requests|PyYAML|rich|ddgs)"

Test imports
  python3 -c "from ddgs import DDGS; print('✓ All modules OK')"

Run help
  python3 dorkeye.py --help

✅ Verification
Test Basic Functionality

1. Activate environment (if not active)
  source dorkeye_env/bin/activate  # Linux/macOS
OR
  dorkeye_env\Scripts\activate.bat  # Windows

2. Generate sample config
  python3 dorkeye.py --create-config

3. Run test search
  python3 dorkeye.py -d "python programming" -c 5 -o test

4. Check output files
  ls -la test.*  # Linux/macOS
  dir test.*     # Windows

Expected Output
✓ dorkeye_config.yaml created
✓ test.csv created
✓ test.json created
✓ test.html created
Verify Modules
bash
python3 << 'EOF'
import sys
print("Python version:", sys.version)
print("\nChecking modules...")
modules = {
'requests': 'HTTP requests',
'yaml': 'YAML config',
'rich': 'Terminal UI',
'ddgs': 'DuckDuckGo search'
}

for module, desc in modules.items():
try:
import(module)
print(f"✓ {module:15} - {desc}")
except ImportError:
print(f"✗ {module:15} - MISSING!")
EOF

🐛 Troubleshooting
Common Issues & Solutions
Issue: "python3: command not found"
Linux/macOS:

Install Python
  sudo apt install python3 python3-pip  # Debian/Ubuntu
  brew install python3                  # macOS

Windows:
Reinstall Python with "Add to PATH" checked Or add manually to PATH environment variable

Issue: "No module named 'ddgs'"
Make sure you're in virtual environment
   source dorkeye_env/bin/activate

Uninstall old package
  pip uninstall duckduckgo-search -y

Install correct package
  pip install ddgs

Verify
  python3 -c "from ddgs import DDGS; print('OK')"

Issue: "externally-managed-environment" (Kali Linux)
Solution 1: Use Virtual Environment (Recommended)
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate
pip install -r requirements.txt

Solution 2: User Install
pip install --user -r requirements.txt

Solution 3: System Packages
sudo apt install python3-requests python3-yaml python3-rich
pip install --user ddgs
   Issue: Virtual environment won't activate

Linux/macOS:
Recreate environment
rm -rf dorkeye_env
python3 -m venv dorkeye_env
source dorkeye_env/bin/activate

Windows:
    cmd
REM Delete old environment
  rmdir /s /q dorkeye_env

REM Recreate
  python -m venv dorkeye_env
  dorkeye_env\Scripts\activate.bat
Issue: "ModuleNotFoundError: No module named 'yaml'"

Activate environment first
  source dorkeye_env/bin/activate

Install PyYAML (note the capital letters)
  pip install PyYAML

Verify
  python3 -c "import yaml; print(yaml.version)"

Issue: 0 results returned
Possible causes:
Rate limiting - Wait 5-10 minutes between searches
Network issues - Check internet connection
Dork too specific - Try simpler queries
Test:
Simple test
  python3 dorkeye.py -d "python" -c 5 -o test
If still 0, test DDGS directly:
  python3 -c "from ddgs import DDGS; results = list(DDGS().text('test', max_results=3)); print(f'Found: {len(results)}')"

Issue: Permission denied on setup.sh
bash
Make script executable
    chmod +x setup.sh
Run again
  ./setup.sh
Issue: Windows "scripts disabled"
powershell
Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Try again
.\setup.bat

Platform-Specific Issues
Kali Linux / Debian
bash
Install all prerequisites
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

If still issues with pip
python3 -m pip install --upgrade pip

Windows 11
cmd
REM Enable long paths (as Administrator)
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f

REM Restart terminal and retry
macOS (M1/M2 ARM)
bash

Use native Python
arch -arm64 brew install python3

Create environment with native Python
arch -arm64 python3 -m venv dorkeye_env

🔄 Updating DorkEye
Update from Git
bash
cd DorkEye
git pull origin main

Reinstall dependencies (in case of changes)
source dorkeye_env/bin/activate
pip install --upgrade -r requirements.txt

Manual Update
Download latest version
Replace old files (keep dorkeye_env/ folder)
Reinstall requirements:
source dorkeye_env/bin/activate
pip install --upgrade -r requirements.txt

🗑️ Uninstallation
Complete Removal

Linux/macOS:
cd DorkEye
deactivate  # if environment is active
cd 
rm -rf DorkEye

Windows:
cmd
cd DorkEye
deactivate
cd ..
rmdir /s /q DorkEye

Backup results
cp -r DorkEye/results ~/dorkeye_backup
Remove program
rm -rf DorkEye

📞 Getting Help
If you encounter issues not covered here:
Check existing issues: https://github.com/xPloits3c/DorkEye/issues
Open new issue: Include:
Operating system and version
Python version (python3 --version)
Error messages (full output)
Steps to reproduce
Contact: whitehat.report@onionmail.org
✅ Post-Installation Checklist
Python 3.8+ installed
Virtual environment created and activated
All dependencies installed
Test search completed successfully
Output files generated (CSV, JSON, HTML)
Help command works (--help)
Config file generated (--create-config)
Installation complete! Ready to start dorking! 🔍
Return to README.md for usage instructions.
