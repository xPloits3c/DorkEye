#!/bin/sh
# DorkEye installer - detects the device and runs the matching script
# in Devices/<platform>/.
#
#   sh install.sh               auto-detect
#   sh install.sh --ish         force iSH (iOS) lite mode
#   sh install.sh --termux      force Termux (Android)
#   sh install.sh --linux       force Linux / macOS
#
# Windows: double-click install.bat instead.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
DEV="$DIR/Devices"

is_ish() {
    # iSH: 32-bit x86 Alpine emulated on iOS
    [ -f /etc/alpine-release ] && [ "$(uname -m)" = "i686" ] && return 0
    grep -qi -- "-ish" /proc/version 2>/dev/null && return 0
    return 1
}

is_termux() {
    [ -n "$TERMUX_VERSION" ] && return 0
    case "${PREFIX:-}" in *com.termux*) return 0 ;; esac
    return 1
}

is_windows_shell() {
    case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; esac
    return 1
}

case "${1:-}" in
    --ish)    PLATFORM=ios ;;
    --termux) PLATFORM=android ;;
    --linux)  PLATFORM=linux ;;
    "")
        if   is_ish;           then PLATFORM=ios
        elif is_termux;        then PLATFORM=android
        elif is_windows_shell; then PLATFORM=windows
        else                        PLATFORM=linux
        fi ;;
    *) echo "[!] Unknown option: $1"; sed -n '5,9p' "$0"; exit 1 ;;
esac

case "$PLATFORM" in
    ios)
        echo "[*] iSH (iOS) detected -> lite installation (no lxml)"
        exec sh "$DEV/iOS/install_ish.sh" ;;
    android)
        echo "[*] Termux (Android) detected"
        exec sh "$DEV/Android/install_termux.sh" ;;
    windows)
        echo "[!] Windows shell detected: run install.bat (double-click it or run it from cmd)."
        exit 1 ;;
    linux)
        echo "[*] $(uname -s) detected"
        exec sh "$DEV/Linux/install_linux.sh" ;;
esac
