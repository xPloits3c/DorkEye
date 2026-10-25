# DorkEye on Windows

> Run DorkEye on Windows 10 or 11, from a double-click or from the command line.

-----

## Requirements

- Windows 10 or higher
- [Python 3.8+](https://www.python.org/downloads/) — during setup, tick **"Add Python to PATH"**
- [Git for Windows](https://git-scm.com/download/win) (optional; you can also download the ZIP)

-----

## Quick install (recommended)

1. Get the code — either clone it:

   ```cmd
   git clone https://github.com/xPloits3c/DorkEye.git
   cd DorkEye
   ```

   or download the ZIP from GitHub (**Code → Download ZIP**) and extract it.

2. **Double-click `install.bat`** in the DorkEye folder.

`install.bat` creates the `dorkeye_env` virtualenv, installs every requirement and keeps the window open so you can read the result. You can also run it from `cmd`:

```cmd
install.bat
```

-----

## Run

```cmd
dorkeye_env\Scripts\activate
python dorkeye.py --wizard
```

Each new terminal needs the `activate` line again before running DorkEye.

-----

## Troubleshooting

**`'python' is not recognized`** — Python isn't on PATH. Reinstall it from
[python.org](https://www.python.org/downloads/) and tick *"Add Python to PATH"*,
or launch with the `py` command.

**`running scripts is disabled on this system`** — only affects PowerShell, not
`install.bat`. Use `cmd`, or allow scripts for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**SmartScreen warning on the `.bat`** — Windows may warn about a downloaded
script. Open the file in Notepad to confirm it's the DorkEye installer, then
*More info → Run anyway*.

**The window closes instantly** — run `install.bat` from an open `cmd` window
instead of double-clicking, so any early error stays visible.

-----

## Notes

- Windows uses the standard install (`requirements.txt`, including `lxml`); the
  iSH lite mode is only for iOS.
- `install.sh` is for Linux/macOS/Termux/iSH — on Windows use `install.bat`.
