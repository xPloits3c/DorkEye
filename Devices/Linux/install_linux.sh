#!/bin/sh
# DorkEye - installer for Linux and macOS
#
# Uses the active virtualenv, or creates dorkeye_env. A virtualenv avoids
# the "externally-managed-environment" error on Debian 12+, Kali, Ubuntu 23+.
set -e

LINUX_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$LINUX_DIR/../.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "[!] Python 3 not found."
    echo "    Debian/Ubuntu/Kali: sudo apt install python3 python3-venv python3-pip"
    echo "    macOS:              brew install python"
    exit 1
fi

if [ -n "$VIRTUAL_ENV" ]; then
    VPY="$VIRTUAL_ENV/bin/python"
    echo "[*] Using active virtualenv: $VIRTUAL_ENV"
else
    echo "[*] Creating virtualenv dorkeye_env..."
    if ! "$PY" -m venv dorkeye_env; then
        echo "[!] Could not create the virtualenv."
        echo "    Debian/Ubuntu/Kali: sudo apt install python3-venv"
        exit 1
    fi
    VPY="$ROOT/dorkeye_env/bin/python"
fi

echo "[*] Python requirements..."
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install -r requirements.txt

echo "[+] Installation complete."
[ -z "$VIRTUAL_ENV" ] && echo "    Activate: source dorkeye_env/bin/activate"
echo "    Run:      python3 dorkeye.py --wizard"
