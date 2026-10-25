@echo off
REM DorkEye installer for Windows - double-click or run from cmd.
setlocal
cd /d "%~dp0"

echo [*] Windows detected

where py >nul 2>&1 && (set "PY=py") || (
    where python >nul 2>&1 && (set "PY=python") || (
        echo [!] Python not found. Install it from https://www.python.org/downloads/
        echo     During setup, tick "Add Python to PATH".
        goto :end
    )
)

if defined VIRTUAL_ENV (
    echo [*] Using active virtualenv: %VIRTUAL_ENV%
    set "VPY=%VIRTUAL_ENV%\Scripts\python.exe"
) else (
    echo [*] Creating virtualenv dorkeye_env...
    %PY% -m venv dorkeye_env || ( echo [!] Could not create the virtualenv. & goto :end )
    set "VPY=%CD%\dorkeye_env\Scripts\python.exe"
)

echo [*] Python requirements...
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements.txt || ( echo [!] Requirements installation failed. & goto :end )

echo.
echo [+] Installation complete.
echo     Activate: dorkeye_env\Scripts\activate
echo     Run:      python dorkeye.py --wizard

:end
echo.
pause
endlocal
