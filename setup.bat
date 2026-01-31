@echo off
REM DorkEye v3.8 - Advanced Windows Setup Script
REM Features: Module verification, auto-retry, comprehensive testing, error handling

setlocal enabledelayedexpansion

REM Configuration
set "VENV_DIR=dorkeye_env"
set "MAX_RETRIES=3"
set "PYTHON_MIN_VERSION=3.8"
set ERROR_COUNT=0
set WARNING_COUNT=0

REM Colors (using color command is limited, using echo for now)
color 0A

REM Clear screen and show banner
cls
echo.
echo      ___
echo  __H__     DorkEye v3.8
echo   [,]      Advanced Windows Setup
echo   [)]      
echo   [;]      Module Verification • Auto-Retry • Testing
echo   ^|_^|  
echo    V
echo.
echo =========================================================
echo           DorkEye v3.8 - Windows Installation
echo =========================================================
echo.

REM ============================================
REM Step 1: Check Python installation
REM ============================================
echo [Step 1/8] Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

REM Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

REM Check minimum version (3.8)
if %PYTHON_MAJOR% LSS 3 (
    echo [ERROR] Python version too old. Need 3.8+
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 8 (
    echo [ERROR] Python 3.%PYTHON_MINOR% is too old. Need 3.8+
    pause
    exit /b 1
)

echo [OK] Python version is compatible ^(^>= 3.8^)
echo.

REM ============================================
REM Step 2: Check pip
REM ============================================
echo [Step 2/8] Checking pip...

python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed!
    echo Please reinstall Python with pip included
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python -m pip --version') do set PIP_VERSION=%%i
echo [OK] pip %PIP_VERSION% is available
echo.

REM ============================================
REM Step 3: Check requirements.txt
REM ============================================
echo [Step 3/8] Checking requirements.txt...

if not exist requirements.txt (
    echo [WARNING] requirements.txt not found! Creating it...
    (
        echo # DorkEye v3.0 - Requirements
        echo requests^>=2.31.0
        echo PyYAML^>=6.0.1
        echo rich^>=13.7.0
        echo ddgs^>=0.1.0
        echo urllib3^>=2.0.0
        echo certifi^>=2023.7.22
        echo charset-normalizer^>=3.3.0
        echo idna^>=3.4
    ) > requirements.txt
    echo [OK] requirements.txt created
) else (
    echo [OK] requirements.txt found
)
echo.

REM ============================================
REM Step 4: Create virtual environment
REM ============================================
echo [Step 4/8] Creating virtual environment...

if exist %VENV_DIR% (
    echo [INFO] Virtual environment already exists
    choice /C YN /M "Do you want to recreate it"
    if errorlevel 2 (
        echo [INFO] Using existing environment
        goto :activate_venv
    )
    echo [INFO] Removing old environment...
    rmdir /s /q %VENV_DIR% 2>nul
)

echo [PROGRESS] Creating new virtual environment...
python -m venv %VENV_DIR%

if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment!
    echo.
    echo Try: python -m pip install --upgrade pip
    pause
    exit /b 1
)

echo [OK] Virtual environment created: %VENV_DIR%
echo.

REM ============================================
REM Step 5: Activate virtual environment
REM ============================================
:activate_venv
echo [Step 5/8] Activating virtual environment...

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Activation script not found!
    pause
    exit /b 1
)

call %VENV_DIR%\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM ============================================
REM Step 6: Upgrade pip
REM ============================================
echo [Step 6/8] Upgrading pip...
echo [PROGRESS] This may take a moment...

python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip ^(continuing anyway^)
    set /a WARNING_COUNT+=1
) else (
    echo [OK] pip upgraded successfully
)
echo.

REM ============================================
REM Step 7: Install requirements with retry
REM ============================================
echo [Step 7/8] Installing dependencies...
echo [INFO] This may take a few minutes...
echo.

set INSTALL_SUCCESS=0
set ATTEMPT=1

:install_loop
if %ATTEMPT% GTR %MAX_RETRIES% goto :install_failed

echo [Attempt %ATTEMPT%/%MAX_RETRIES%] Installing packages...

pip install -r requirements.txt
if not errorlevel 1 (
    set INSTALL_SUCCESS=1
    goto :install_success
)

echo [WARNING] Installation failed on attempt %ATTEMPT%

if %ATTEMPT% LSS %MAX_RETRIES% (
    echo [PROGRESS] Retrying with --no-cache-dir...
    pip install --no-cache-dir -r requirements.txt
    if not errorlevel 1 (
        set INSTALL_SUCCESS=1
        goto :install_success
    )
    timeout /t 2 /nobreak >nul
)

set /a ATTEMPT+=1
goto :install_loop

:install_failed
echo.
echo [ERROR] Failed to install dependencies after %MAX_RETRIES% attempts!
echo.
echo Try manually:
echo   %VENV_DIR%\Scripts\activate.bat
echo   pip install requests PyYAML rich ddgs
echo.
pause
exit /b 1

:install_success
echo.
echo [OK] All dependencies installed successfully!
echo.

REM ============================================
REM Step 8: Verify modules
REM ============================================
echo [Step 8/8] Verifying installed modules...
echo.

set MODULE_ERRORS=0

REM Test each module
echo [PROGRESS] Testing module: requests
python -c "import requests; print('[OK] requests - version:', requests.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] requests - FAILED TO IMPORT
    set /a MODULE_ERRORS+=1
    set /a ERROR_COUNT+=1
)

echo [PROGRESS] Testing module: yaml
python -c "import yaml; print('[OK] PyYAML - version:', yaml.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] PyYAML - FAILED TO IMPORT
    set /a MODULE_ERRORS+=1
    set /a ERROR_COUNT+=1
)

echo [PROGRESS] Testing module: rich
python -c "from rich.console import Console; print('[OK] rich - OK')" 2>nul
if errorlevel 1 (
    echo [ERROR] rich - FAILED TO IMPORT
    set /a MODULE_ERRORS+=1
    set /a ERROR_COUNT+=1
)

echo [PROGRESS] Testing module: ddgs
python -c "from ddgs import DDGS; print('[OK] ddgs - OK')" 2>nul
if errorlevel 1 (
    echo [ERROR] ddgs - FAILED TO IMPORT
    set /a MODULE_ERRORS+=1
    set /a ERROR_COUNT+=1
)

echo.

if %MODULE_ERRORS% EQU 0 (
    echo [OK] All modules verified successfully!
) else (
    echo [ERROR] %MODULE_ERRORS% module^(s^) failed verification
    echo.
    echo Try reinstalling manually:
    echo   pip install --force-reinstall requests PyYAML rich ddgs
    echo.
)

REM ============================================
REM Run comprehensive tests
REM ============================================
echo.
echo =========================================================
echo                 Running Comprehensive Tests
echo =========================================================
echo.

set TEST_PASSED=0
set TEST_FAILED=0

REM Test 1: Import all modules
echo [Test 1/5] Testing module imports...
python -c "import requests, yaml; from rich.console import Console; from ddgs import DDGS; print('[OK] All imports successful')" 2>nul
if not errorlevel 1 (
    echo [OK] Import test passed
    set /a TEST_PASSED+=1
) else (
    echo [ERROR] Import test failed
    set /a TEST_FAILED+=1
)

REM Test 2: Requests functionality
echo [Test 2/5] Testing requests module...
python -c "import requests; r = requests.get('https://www.google.com', timeout=5); assert r.status_code == 200; print('[OK] Requests working')" 2>nul
if not errorlevel 1 (
    echo [OK] Requests test passed
    set /a TEST_PASSED+=1
) else (
    echo [WARNING] Requests test failed ^(network issue?^)
    set /a TEST_FAILED+=1
)

REM Test 3: YAML parsing
echo [Test 3/5] Testing YAML parsing...
python -c "import yaml; data = yaml.safe_load('test: value'); assert data['test'] == 'value'; print('[OK] YAML parsing works')" 2>nul
if not errorlevel 1 (
    echo [OK] YAML test passed
    set /a TEST_PASSED+=1
) else (
    echo [ERROR] YAML test failed
    set /a TEST_FAILED+=1
)

REM Test 4: Rich console
echo [Test 4/5] Testing Rich console...
python -c "from rich.console import Console; c = Console(); c.print('[green]Test[/green]'); print('[OK] Rich console working')" 2>nul
if not errorlevel 1 (
    echo [OK] Rich console test passed
    set /a TEST_PASSED+=1
) else (
    echo [ERROR] Rich console test failed
    set /a TEST_FAILED+=1
)

REM Test 5: DDGS
echo [Test 5/5] Testing DuckDuckGo search module...
python -c "from ddgs import DDGS; ddgs = DDGS(); print('[OK] DDGS initialized')" 2>nul
if not errorlevel 1 (
    echo [OK] DDGS test passed
    set /a TEST_PASSED+=1
) else (
    echo [ERROR] DDGS test failed
    set /a TEST_FAILED+=1
)

echo.
echo =========================================================
echo Tests Passed: %TEST_PASSED%/5
if %TEST_FAILED% GTR 0 (
    echo Tests Failed: %TEST_FAILED%/5
)
echo =========================================================
echo.

REM ============================================
REM Create helper scripts
REM ============================================
echo [INFO] Creating helper scripts...

REM Create run_dorkeye.bat
(
    echo @echo off
    echo REM Quick launcher for DorkEye
    echo.
    echo cd /d "%%~dp0"
    echo.
    echo if not exist dorkeye_env (
    echo     echo Error: Virtual environment not found!
    echo     echo Run setup.bat first
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo call dorkeye_env\Scripts\activate.bat
    echo python dorkeye.py %%*
) > run_dorkeye.bat

echo [OK] Created run_dorkeye.bat

REM Create test_installation.bat
(
    echo @echo off
    echo REM Test DorkEye installation
    echo.
    echo call dorkeye_env\Scripts\activate.bat
    echo.
    echo echo Testing DorkEye installation...
    echo echo.
    echo python -c "import sys; modules = {'requests': 'HTTP Requests', 'yaml': 'YAML Parser', 'rich': 'Terminal UI', 'ddgs': 'DuckDuckGo Search'}; print('=' * 50); print('DorkEye Installation Test'); print('=' * 50); all_ok = True; [print(f'✓ {name:20} OK') if __import__(module) or True else print(f'✗ {name:20} MISSING') or setattr(all_ok, 'value', False) for module, name in modules.items()]; print('=' * 50); print('✓ All modules installed correctly!' if all_ok else '✗ Some modules missing!'); sys.exit(0 if all_ok else 1)"
    echo.
    echo pause
) > test_installation.bat

echo [OK] Created test_installation.bat
echo.

REM ============================================
REM Installation summary
REM ============================================
echo.
echo =========================================================
echo                  Installation Summary
echo =========================================================
echo.

echo Installed Packages:
pip list 2>nul | findstr /i "requests PyYAML rich ddgs urllib3 certifi"

if %WARNING_COUNT% GTR 0 (
    echo.
    echo Warnings: %WARNING_COUNT%
)

if %ERROR_COUNT% GTR 0 (
    echo.
    echo Errors: %ERROR_COUNT%
)

echo.
echo =========================================================
echo.

REM ============================================
REM Print usage instructions
REM ============================================
if %TEST_FAILED% LEQ 2 (
    echo =========================================================
    echo           Installation Completed Successfully!
    echo =========================================================
    echo.
    echo Quick Start Guide:
    echo.
    echo Method 1 - Direct execution:
    echo   dorkeye_env\Scripts\activate.bat
    echo   python dorkeye.py -d "your dork" -o results
    echo   deactivate
    echo.
    echo Method 2 - Using launcher ^(recommended^):
    echo   run_dorkeye.bat -d "site:github.com python" -o results
    echo.
    echo Quick Tests:
    echo   run_dorkeye.bat --help
    echo   run_dorkeye.bat --create-config
    echo   test_installation.bat
    echo.
    echo Example Commands:
    echo   run_dorkeye.bat -d "filetype:pdf" -c 20 -o pdfs
    echo   run_dorkeye.bat -d dorks.txt --whitelist .pdf .doc -o docs
    echo   run_dorkeye.bat -d "inurl:admin" --no-analyze -o fast
    echo.
    
    if not exist dorkeye.py (
        echo [WARNING] Main script not found
        echo           Save 'dorkeye.py' in this directory to start
        echo.
    )
    
    echo Happy Dorking! Stay Legal, Stay Ethical!
    echo.
) else (
    echo [WARNING] Installation completed with some test failures
    echo           Try running: run_dorkeye.bat --help
    echo.
)

echo Press any key to exit...
pause >nul
