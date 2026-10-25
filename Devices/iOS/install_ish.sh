#!/bin/sh
# DorkEye - installer for iSH (Alpine Linux on iOS)
#
# lxml cannot be built on iSH, and ddgs depends on it. This script installs
# every requirement except lxml/ddgs and copies the ddg_lite backend into the
# DorkEye root, where dorkeye.py loads it automatically.
#
# A virtualenv (dorkeye_env) is created automatically when possible. On a
# minimal Alpine where venv/pip isn't available, it falls back to a
# system-wide install so the setup still completes.
set -e

IOS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$IOS_DIR/../.." && pwd)"
# Unique temp file (no fixed, predictable path in a world-writable dir)
REQ_TMP="$(mktemp "${TMPDIR:-/tmp}/dorkeye-req-ish.XXXXXX")"
trap 'rm -f "$REQ_TMP"' EXIT
trap 'exit 1' HUP INT TERM

echo "[*] System packages..."
apk update
apk add --no-cache python3 py3-pip

echo "[*] Python requirements (without lxml / ddgs)..."
# Filter from the main requirements.txt so the two lists never drift apart
grep -v -i -E '^[[:space:]]*(lxml|ddgs)([<>=!~ ]|$)' "$ROOT/requirements.txt" > "$REQ_TMP"

# Pick a Python environment: active venv > a fresh dorkeye_env > system
PY=""
if [ -n "$VIRTUAL_ENV" ]; then
    PY="$VIRTUAL_ENV/bin/python"
    echo "[*] Using active virtualenv: $VIRTUAL_ENV"
else
    echo "[*] Creating virtualenv dorkeye_env..."
    if python3 -m venv "$ROOT/dorkeye_env" 2>/dev/null \
       && "$ROOT/dorkeye_env/bin/python" -m pip --version >/dev/null 2>&1; then
        PY="$ROOT/dorkeye_env/bin/python"
        VENV_CREATED=1
    else
        rm -rf "$ROOT/dorkeye_env"
        echo "[*] venv not available on this Alpine -> installing system-wide"
    fi
fi

if [ -n "$PY" ]; then
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install -r "$REQ_TMP"
else
    python3 -m pip install -r "$REQ_TMP" \
        || python3 -m pip install --break-system-packages -r "$REQ_TMP"
fi

echo "[*] Installing lite search backend in $ROOT"
cp "$IOS_DIR/ddg_lite.py" "$ROOT/ddg_lite.py"

echo "[+] Installation complete (lite mode)."
[ -n "$VENV_CREATED" ] && echo "    Activate: source \"$ROOT/dorkeye_env/bin/activate\""
echo "    Run: cd \"$ROOT\" && python3 dorkeye.py --wizard"
