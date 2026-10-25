# DorkEye on iSH (iOS)

> Run DorkEye on iPhone / iPad through [iSH](https://ish.app), an Alpine Linux shell for iOS.

-----

## Why a lite mode?

iSH emulates a 32-bit x86 CPU, and `lxml` cannot be compiled there. The `ddgs`
search library depends on `lxml`, so a normal `pip install -r requirements.txt`
fails.

On iSH DorkEye uses **`ddg_lite`** instead: a small backend that queries
DuckDuckGo's HTML endpoint with only `requests` + `beautifulsoup4` (stdlib
`html.parser`). It exposes the same `DDGS().text()` interface, so the rest of
DorkEye works unchanged.

-----

## Installation

```bash
apk add git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
sh install.sh
```

`install.sh` detects iSH automatically and hands over to `Devices/iOS/install_ish.sh`, which:

1. installs `python3` and `py3-pip` with `apk`
2. creates the `dorkeye_env` virtualenv automatically (falls back to a system-wide install if venv isn't available on that Alpine)
3. installs every entry of `requirements.txt` **except** `lxml` and `ddgs`
4. copies `Devices/iOS/ddg_lite.py` into the DorkEye root

No need to create the virtualenv by hand. If you already have one active, the installer uses it instead.

To force lite mode manually:

```bash
sh install.sh --ish
```

-----

## Run

```bash
source dorkeye_env/bin/activate   # only if the installer created a venv
python3 dorkeye.py --wizard
```

The installer prints an `Activate:` line when it creates `dorkeye_env`; if it
installed system-wide instead, skip the `activate` step. `dorkeye.py` tries
`ddgs` first and falls back to `ddg_lite` automatically when `ddgs` is not
installed.

-----

## Limitations

- `ddg_lite` scrapes the HTML version of DuckDuckGo: it is more sensitive to
  rate limiting and to layout changes than `ddgs`.
- Keep the number of results per dork moderate and leave delays enabled.
- iSH is an emulator: searches and analysis are noticeably slower than on a PC
  or on Termux.

-----

## Files

```
DorkEye/
├── install.sh                 # device detection + dispatch
├── ddg_lite.py                # created by the installer (git-ignored)
└── Devices/
    └── iOS/
        ├── install_ish.sh     # iSH installer
        └── ddg_lite.py        # lite backend source
```
