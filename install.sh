#!/bin/sh
# DorkEye installer - detects the platform and installs the right requirements
#   sh install.sh          auto-detect
#   sh install.sh --ish    force iSH / lite mode
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

is_ish() {
    # iSH: 32-bit x86 Alpine emulated on iOS
    [ -f /etc/alpine-release ] && [ "$(uname -m)" = "i686" ] && return 0
    grep -qi -- "-ish" /proc/version 2>/dev/null && return 0
    return 1
}

if [ "$1" = "--ish" ] || is_ish; then
    echo "[*] iSH / Alpine detected -> lite installation (no lxml)"
    exec sh "$DIR/iOS/install_ish.sh"
fi

PY="$(command -v python3 || command -v python || true)"
[ -z "$PY" ] && { echo "[!] Python 3 not found"; exit 1; }

echo "[*] Installing standard requirements..."
"$PY" -m pip install -r requirements.txt \
    || "$PY" -m pip install --break-system-packages -r requirements.txt

echo "[+] Done. Run: $PY dorkeye.py --wizard"
