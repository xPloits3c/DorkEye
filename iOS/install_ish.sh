#!/bin/sh
# DorkEye - installer for iSH (Alpine Linux on iOS)
#
# lxml cannot be built on iSH, and ddgs depends on it. This script installs
# every requirement except lxml/ddgs and copies the ddg_lite backend into the
# DorkEye root, where dorkeye.py loads it automatically.
set -e

IOS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$IOS_DIR")"
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
python3 -m pip install -r "$REQ_TMP" \
    || python3 -m pip install --break-system-packages -r "$REQ_TMP"

echo "[*] Installing lite search backend in $ROOT"
cp "$IOS_DIR/ddg_lite.py" "$ROOT/ddg_lite.py"

echo "[+] Installation complete (lite mode)."
echo "    Run: cd \"$ROOT\" && python3 dorkeye.py --wizard"
