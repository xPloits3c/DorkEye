<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | [简体中文](../zh-CN/README.md) | [Español](../es/README.md) | [Português](../pt-BR/README.md) | [Русский](../ru/README.md) | [日本語](../ja/README.md) | **Italiano**

</div>

> [!NOTE]
> Questo documento è una traduzione del README in inglese. In caso di discrepanze fa fede la [versione originale in inglese](../../../README.md). La documentazione dettagliata è per ora disponibile solo in inglese.

# DorkEye – Strumento di OSINT Dorking

<!-- ── Row 1: Project identity ── -->
![Python](https://img.shields.io/badge/Python-3.7%2B-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)
![Search](https://img.shields.io/badge/Search-DuckDuckGo-FF6600?style=flat-square&logo=duckduckgo&logoColor=white)
![Version](https://img.shields.io/badge/Version-5.2-brightgreen?style=flat-square)

<!-- ── Row 2: Live stats ── -->
![Repo views](https://komarev.com/ghpvc/?username=xPloits3c&label=DorkEye%20views&color=blue)
![Stars](https://img.shields.io/github/stars/xPloits3c/DorkEye?style=flat-square)
![Forks](https://img.shields.io/github/forks/xPloits3c/DorkEye?style=flat-square)
![Issues](https://img.shields.io/github/issues/xPloits3c/DorkEye?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/xPloits3c/DorkEye?style=flat-square&logo=github)

<!-- ── Row 3: Community ── -->

[![Telegram](https://img.shields.io/badge/Join-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/DorkEye) 

<img width="980" height="640" alt="image" src="https://github.com/user-attachments/assets/13dea163-578c-41ad-9e2b-497bb373ab77" />

---

## Cos'è DorkEye?
**DorkEye** è uno `STRUMENTO DI OSINT DORKING` automatizzato che individua asset web esposti tramite query di ricerca intelligenti.
- Combina un generatore di dork guidato da template YAML (modalità `soft` / `medium` / `aggressive`), un modulo di test SQL e XSS, una pipeline di analisi autonoma in 13 step, un crawler ricorsivo adattivo, uno scanner di porte di database e un grafo OSINT passivo — tutto raccolto in un unico report HTML a schede.

- Può identificare directory indicizzate, file sensibili, pannelli di amministrazione, database, backup, file di configurazione, credenziali, dati personali (PII), sottodomini e fingerprint tecnologici — in modo efficiente e con controlli di stealth.

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Perché DorkEye

- Funziona ovunque — Linux · macOS · Windows · Android (Termux) · iOS (iSH)
- Aggira CAPTCHA e rate limiting
- Report HTML avanzato e interattivo
- Mantiene l'anonimato ed evita il blocco dell'IP
- Risultati di ricerca puliti e non filtrati
- Dorking per ore — DorkEye non viene bannato.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## Novità 🥇

| Funzione | Dettagli |
|---------|---------|
| 🧙 Wizard | [Sessione guidata interattiva — tutte le opzioni](../../wizard.md) |
| ⚙️ Generatore di dork | [Modalità template YAML: `soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 Tutti i sistemi | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) — Python 3.7+ |
| 🎯 SQLi-XSS | [Testa gli URL direttamente con `-u` e `-f`](../../sqli.md) |
| 📂 Ri-elaborazione file | [Riesegui SQLi/XSS/analisi/crawl sui file di risultati salvati con `-f`](../../cli.md) |
| 💉 SQL Injection | [5 metodi: 105 payload](../../sqli.md) |
| 💉 XSS Injection | [4 metodi: 111 payload](../../xss.md) |
| 🖥️ Web Console | [Dashboard locale stile Matrix nel browser `--ui`](../../webconsole.md) |
| 🚪 DB Port Scan | [15 servizi, probe senza autenticazione, 3 livelli di severità `--dbscan`](../../dbscan.md) |
| 🕸️ Grafo OSINT | [Grafo di ricognizione passivo e senza chiavi: sottodomini, IP, CVE, ASN, contatti `--osint`](../../osint.md) |
| 📑 Report unificato | [Un unico report HTML a schede: Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 Pipeline di agenti | [Analisi autonoma in 13 step](../../agents.md) |
| 🛡️ HeaderIntelAgent | [Fughe di informazioni, header di sicurezza mancanti, server obsoleto](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 tecnologie rilevate, dork CVE generati](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Raccoglie e categorizza le email: admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Telefono, IBAN, codice fiscale, carta di credito, SSN, data di nascita](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Estrae i sottodomini e genera `queries`](../../agents.md#subdomainharvesteragent) |
| 🔄 Crawl adattivo | [Dorking ricorsivo multi-round](../../crawler.md) |
| 🔑 HTTP Fingerprinting | [22 profili browser/OS — Chrome, Firefox, Safari, mobile, ecc.](../../fingerprinting.md) |
| 📊 Formati di output | [Report HTML interattivo — tutto salvato in `Dump/`](../../output_formats.md) |
| 🗂️ Categorie di file | [7 categorie rilevate automaticamente — filtraggio whitelist / blacklist](../../file_categories.md) |
| 🖥️ Riferimento CLI completo | [Tutti i 44 flag e ogni combinazione possibile](../../cli.md) |

---

## Installazione rapida
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# Per Debian, Ubuntu o Kali.
## Automatica
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py --wizard
```
## Manuale
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
```
# Alpine / iOS (iSH)
Consigliato per **gli utenti iOS tramite [iSH](https://ish.app)** (Alpine Linux) e qualsiasi sistema basato su Alpine.<br>
`install.sh` rileva automaticamente l'ambiente ed esegue la configurazione corrispondente.
[![Docs](https://img.shields.io/badge/📖_Docs-blue)](../../devices/ish.md)

```sh
apk add git
git clone https://github.com/xPloits3c/DorkEye.git
cd DorkEye
sh install.sh
source dorkeye_env/bin/activate
python dorkeye.py --wizard
```

<img width="1175" height="982" alt="dev5 0wiz" src="https://github.com/user-attachments/assets/79253966-b2ed-431e-9d46-aaa8d8297c82" />

---

## Utilizzo

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # Modalità WIZARD &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # Ricerca base &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Generatore di dork + rilevamento &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + stealth &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Scansione veloce &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Test SQLi diretto su un URL &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Ri-elabora un file di risultati salvato &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # Grafo OSINT &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Web Console &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## Esempi
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 Struttura del progetto
```
DorkEye/
│ ├── dorkeye.py                      ← Motore di DorkEye
│ ├── requirements.txt                ← Dipendenze Python
│ ├── http_fingerprints.json          ← 22 profili HTTP browser/OS
│ ├── install.sh                      ← Rilevamento dispositivo + dispatch (Linux/macOS/Termux/iSH)
│ ├── install.bat                     ← Installer per Windows (doppio clic)
│ ├── README.md                       ← README in inglese
│ ├── LICENSE                         ← Licenza MIT
│ ├── .gitignore                      ← Regole di esclusione Git
│ /Devices/                           ← Installer per dispositivo
│    /iOS/
│        ├── install_ish.sh           ← Installer leggero per iSH (iOS) — senza lxml
│        └── ddg_lite.py              ← Backend DuckDuckGo senza lxml
│    /Android/
│        └── install_termux.sh        ← Installer per Termux (libxml2/libxslt + venv)
│    /Linux/
│        └── install_linux.sh         ← Installer per Linux / macOS (venv)
│ /Tools/
│    ├── __init__.py                  ← Inizializzatore del pacchetto
│    ├── dork_generator.py            ← Generatore di query dork
│    ├── dorkeye_agents.py            ← Pipeline di agenti
│    ├── dorkeye_patterns.py          ← Libreria di pattern condivisa
│    ├── dorkeye_analyze.py           ← CLI di analisi standalone
│    ├── db_portscan.py               ← Scansiona le porte di database esposte
│    ├── osint.py                     ← Grafo OSINT passivo (--osint)
│    ├── report.py                    ← Motore di report HTML condiviso (report a schede)
│    ├── dorkeye_web.py               ← Interfaccia web locale
│    ├── sqli.py                      ← SQL injection con 5 metodi (105 payload)
│    └── xss.py                       ← XSS injection con 4 metodi (111 payload)
│ /Templates/
│    ├── dorks_templates.yaml         ← Template predefinito
│    ├── example.yaml                 ← Template di esempio
│    ├── sql.yaml                     ← Template di dork SQLi
│    └── wp-advanced.yaml             ← Template di esposizione WordPress
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← Linee guida della community
│    ├── CONTRIBUTING.md              ← Guida ai contributi
│    ├── SECURITY.md                  ← Politica di sicurezza
│    ├── FUNDING.yml                  ← Configurazione sponsor
│    ├── pull_request_template.md     ← Template PR
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Template segnalazione bug
│        └── feature_request.md       ← Template richiesta funzionalità
│     /workflows/
│        └── claude-dorkeye.yml       ← Agente IA di GitHub Actions
│ /Docs/
│    ├── overview.md                  ← Panoramica del progetto
│    ├── cli.md                       ← Riferimento CLI completo (44 flag)
│    ├── wizard.md                    ← Guida al wizard interattivo
│    ├── sqli.md                      ← Riferimento SQL injection
│    ├── xss.md                       ← Riferimento XSS injection
│    ├── agents.md                    ← Guida alla pipeline di agenti
│    ├── crawler.md                   ← Guida al crawler adattivo
│    ├── dbscan.md                    ← Guida alla scansione porte DB
│    ├── osint.md                     ← Guida al grafo OSINT
│    ├── fingerprinting.md            ← Guida al fingerprinting HTTP
│    ├── http_fingerprints.md         ← Riferimento profili fingerprint
│    ├── webconsole.md                ← Guida alla Web Console
│     /devices/
│        ├── termux.md                ← Configurazione Termux / Android
│        ├── ish.md                   ← Configurazione iSH / iOS (modalità leggera)
│        └── windows.md               ← Configurazione Windows (install.bat)
│     /languages/                     ← Traduzioni del README
│    ├── output_formats.md            ← Guida ai formati di output
│    ├── file_categories.md           ← Guida alle categorie di file
│    ├── dork_generator.md            ← Guida al generatore di dork
│    ├── INSTALL.md                   ← Guida all'installazione
│    ├── REPORT_HTML.md               ← Guida al report HTML
│    ├── USAGE.md                     ← Esempi di utilizzo
│    ├── DDGSEE.md                    ← Note sul motore DuckDuckGo
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← Raccolta di dork selezionati
│        ├── JSON_exposure_dork.txt   ← Dork di esposizione JSON
│        └── sql_dorks.txt            ← Dork orientati a SQLi
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← output a runtime, non versionato (vedi .gitignore)
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← Database del grafo OSINT
│    └── *.graphml                    ← Esportazione del grafo OSINT
```
---

## Grafo OSINT

`--osint` trasforma gli host trovati dai tuoi dork in un grafo di correlazione, usando solo fonti pubbliche
e **senza chiavi API**: Certificate Transparency (crt.sh), RDAP, DNS-over-HTTPS, Shodan InternetDB,
reverse DNS, ASN/geo e la Wayback Machine. Lungo il percorso vengono estratti email e numeri di telefono.

| Livello | Cosa raccoglie | Contatta il bersaglio |
|-------|------------------|--------------------|
| `--osint=1` | Dati del registrar, sottodomini, record DNS | No |
| `--osint` / `--osint=2` | Livello 1 + porte aperte, CVE note, reverse DNS, ASN / paese per ogni IP | No |
| `--osint=3` | Livello 2 + URL archiviati, titolo pagina / server / `security.txt` di ogni host | Sì (una richiesta HTTP per host) |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

La scheda **OSINT** mostra il grafo interattivo, i risultati (IP con CVE, host chiamati `admin`, `dev`,
`staging`…, porte aperte più frequenti), i contatti, ogni IP con porte / ASN / paese, i pivot su IP condivisi e
i cluster ASN, e permette di scaricare tutto in JSON, CSV, TXT, GraphML o SQLite.
Ogni esecuzione costruisce un grafo nuovo. Disponibile anche dal wizard e dalla Web Console.
Guida completa: [Docs/osint.md](../../osint.md)

---

## SQL Injection
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## Report
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**DorkEye è fornito esclusivamente per scopi educativi e di security testing autorizzato.**
> - Sei l'unico responsabile del rispetto di tutte le leggi applicabili e dell'ottenimento di un'autorizzazione esplicita e scritta prima di scansionare, testare o sondare qualsiasi sistema, dominio o rete che non ti appartiene.
> - Gli autori e i contributori non si assumono alcuna responsabilità per usi impropri o per qualsiasi danno derivante dall'uso di questo strumento.

---

## 📞 Contatti

- **Autore:** I.C.W.T / xPloits3c  
- **Email:** dorkeye@protonmail.com  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Supporto
 - **I contributi sono benvenuti. Partecipa pure.**
 - **Se trovi DorkEye utile, metti una stella al repository 🌟**
 - **Offrimi un caffè e mantieni lo sviluppo pieno di caffeina ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 Licenza
[Licenza MIT](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## Contributori
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
