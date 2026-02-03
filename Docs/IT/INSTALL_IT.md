## 📦 DorkEye v3.8 — Guida all’Installazione
- Guida completa all’installazione di DorkEye su Linux, Windows e macOS.

========================================

## 📋 Indice

1. [Prerequisiti](#-prerequisiti)
2. [Installazione Linux](#-installazione-linux)
3. [Installazione Windows](#-installazione-windows)
4. [Installazione macOS](#-installazione-macos)
5. [Installazione Manuale (Tutte le Piattaforme)](#-installazione-manuale-tutte-le-piattaforme)
6. [Verifica](#-verifica)
7. [Risoluzione dei Problemi](#-risoluzione-dei-problemi)
8. [Aggiornamento di DorkEye](#-aggiornamento-di-dorkeye)
9. [Disinstallazione](#-disinstallazione)
10. [Ottenere Supporto](#-ottenere-supporto)
11. [Checklist Post-Installazione](#-checklist-post-installazione)

========================================

## 🔧 PREREQUISITI
----------------------------------------
Software Richiesto: |   Comando di Verifica:  |
----------------------------------------
- Python 3.8+      | python3 --version
- pip (ultima versione) | pip3 --version
- git              | git --version

Requisiti di Sistema:
- Linux / Windows 10+ / macOS 10.14+
- Minimo 512 MB di RAM
- 100 MB di spazio libero su disco
- Connessione Internet

========================================

## 🐧 INSTALLAZIONE LINUX (Kali, Ubuntu, Debian)

Metodo 1: Setup Automatico (Consigliato)

-     sudo apt update
-     sudo apt install -y python3 python3-pip python3-venv git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     sudo chmod +x setup.sh
-     ./setup.sh

Test:
-     source dorkeye_env/bin/activate
-     python dorkeye.py --help

Metodo 2: Setup Avanzato / Manuale

-     sudo apt update
-     sudo apt install -y python3 python3-pip python3-venv git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate
-     pip install --upgrade pip
-     pip install -r requirements.txt
-     python3 dorkeye.py --help

Metodo 3: Quick Launcher (Opzionale)
-     sudo nano /usr/local/bin/dorkeye
-     #!/bin/bash
-     cd /path/to/DorkEye
-     source dorkeye_env/bin/activate
-     python3 dorkeye.py "$@"
-     sudo chmod +x /usr/local/bin/dorkeye

Utilizzo:
-     dorkeye -d "your dork" -o results
========================================

## 🪟 INSTALLAZIONE WINDOWS

## Metodo 1: Setup Automatico (Consigliato)

- Installare Python (spuntare "Add to PATH")
Download: https://www.python.org/downloads/
✔ Spuntare “Add Python to PATH”
-     python --version

Metodo 2: Installare Git (opzionale)
Download: https://git-scm.com/download/win
-     git --version

Metodo 3: Installare DorkEye
- Opzione A: Git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     setup.bat

- Opzione B: ZIP
-     cd C:\DorkEye
-     setup.bat

4 Avvio:
-     run_dorkeye.bat -d "site:example.com" -o test

## Metodo 2: Setup Manuale (CMD)
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python -m venv dorkeye_env
-     dorkeye_env\Scripts\activate.bat
-     python -m pip install --upgrade pip
-     pip install -r requirements.txt
-     python dorkeye.py --help

## Metodo 3: PowerShell (Admin)
- Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python -m venv dorkeye_env-
-     .\dorkeye_env\Scripts\Activate.ps1
-     pip install -r requirements.txt
-     python dorkeye.py --help

========================================

## 🍎 INSTALLAZIONE MACOS
- Metodo 1: Automatico
-     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
-     brew install python3 git
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     chmod +x setup.sh
-     ./setup.sh

- Metodo 2: Manuale
-     xcode-select --install
-     brew install python3
-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate
-     pip install -r requirements.txt
-     python3 dorkeye.py --help

## 🔧 Installazione Manuale (Tutte le Piattaforme)

-     git clone https://github.com/xPloits3c/DorkEye.git
-     cd DorkEye

- Creare venv:
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate   # Linux/macOS
-     python -m venv dorkeye_env
-     dorkeye_env\Scripts\activate.bat  # Windows

- Installare dipendenze:
-     pip install --upgrade pip
-     pip install -r requirements.txt
========================================

## ✅ VERIFICA

-     python3 dorkeye.py --create-config
-     python3 dorkeye.py -d "python programming" -c 5 -o test
========================================

## 🐛 Risoluzione dei Problemi

- Problemi Comuni
-   ''ModuleNotFoundError: ddgs''
-     pip uninstall duckduckgo-search -y
-     pip install ddgs

- Kali: externally-managed-environment
-     python3 -m venv dorkeye_env
-     source dorkeye_env/bin/activate

- Script Windows disabilitati
-     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
========================================

## 🔄 Aggiornamento di DorkEye

-     cd DorkEye
-     git pull origin main
-     source dorkeye_env/bin/activate
-     pip install --upgrade -r requirements.txt
========================================

## 🗑️ Disinstallazione

- (Linux/macOS)
-     rm -rf DorkEye
- (Windows)
-     rmdir /s /q DorkEye
========================================

## 📞 Ottenere Supporto
-     https://github.com/xPloits3c/DorkEye/issues
-     whitehat.report@onionmail.org

Includere:
- Sistema operativo + versione
- Versione Python
- Output completo dell’errore
- Passaggi per riprodurre il problema

## ✅ Checklist Post-Installazione

- ✔ Python 3.8+
- ✔ Ambiente virtuale attivo
- ✔ Dipendenze installate
- ✔ Ricerca di test funzionante
- ✔ CSV / JSON / HTML generati
- ✔ --help funzionante
- ✔ File di configurazione creato

## 🔍 Installazione completata — pronto per iniziare il dorking!
