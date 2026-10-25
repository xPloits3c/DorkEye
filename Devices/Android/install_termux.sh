#!/data/data/com.termux/files/usr/bin/sh
# DorkEye - installer for Termux (Android)
#
# lxml is a C extension: libxml2/libxslt must be installed with pkg before
# pip can build it. Uses the active virtualenv, or creates dorkeye_env.
set -e

ANDROID_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$ANDROID_DIR/../.." && pwd)"
cd "$ROOT"

echo "[*] Termux packages..."
pkg update -y
pkg install -y python git libxml2 libxslt

if [ -n "$VIRTUAL_ENV" ]; then
    PY="$VIRTUAL_ENV/bin/python"
    echo "[*] Using active virtualenv: $VIRTUAL_ENV"
else
    echo "[*] Creating virtualenv dorkeye_env..."
    python -m venv dorkeye_env
    PY="$ROOT/dorkeye_env/bin/python"
fi

echo "[*] Python requirements..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo "[+] Installation complete (Termux)."
[ -z "$VIRTUAL_ENV" ] && echo "    Activate: source dorkeye_env/bin/activate"
echo "    Run:      python dorkeye.py --wizard"
