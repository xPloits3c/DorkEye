<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | [简体中文](../zh-CN/README.md) | **Español** | [Português](../pt-BR/README.md) | [Русский](../ru/README.md) | [日本語](../ja/README.md) | [Italiano](../it/README.md)

</div>

> [!NOTE]
> Este documento es una traducción del README en inglés. En caso de diferencias, prevalece la [versión original en inglés](../../../README.md). La documentación detallada está disponible por ahora solo en inglés.

# DorkEye – Herramienta de OSINT Dorking

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

## ¿Qué es DorkEye?
**DorkEye** es una `HERRAMIENTA DE OSINT DORKING` automatizada que descubre activos web expuestos mediante consultas de búsqueda inteligentes.
- Combina un generador de dorks basado en plantillas YAML (modos `soft` / `medium` / `aggressive`), un módulo de pruebas SQL y XSS, un pipeline de análisis autónomo de 13 pasos, un crawler recursivo adaptativo, un escáner de puertos de bases de datos y un grafo OSINT pasivo — todo reunido en un único informe HTML con pestañas.

- Puede identificar directorios indexados, archivos sensibles, paneles de administración, bases de datos, copias de seguridad, archivos de configuración, credenciales, datos personales (PII), subdominios y huellas tecnológicas — de forma eficiente y con controles de sigilo.

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Por qué DorkEye

- Funciona en todas partes — Linux · macOS · Windows · Android (Termux) · iOS (iSH)
- Evita CAPTCHA y límites de peticiones
- Informe HTML avanzado e interactivo
- Mantiene el anonimato y evita bloqueos de IP
- Resultados de búsqueda limpios y sin filtrar
- Haz dorking durante horas — DorkEye no será bloqueado.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## Novedades 🥇

| Función | Detalles |
|---------|---------|
| 🧙 Asistente | [Sesión guiada interactiva — todas las opciones](../../wizard.md) |
| ⚙️ Generador de dorks | [Modos de plantilla YAML: `soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 Todos los sistemas | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) — Python 3.7+ |
| 🎯 SQLi-XSS | [Prueba URLs directamente con `-u` y `-f`](../../sqli.md) |
| 📂 Reprocesado de archivos | [Vuelve a ejecutar SQLi/XSS/análisis/crawl sobre archivos de resultados guardados con `-f`](../../cli.md) |
| 💉 Inyección SQL | [5 métodos: 105 payloads](../../sqli.md) |
| 💉 Inyección XSS | [4 métodos: 111 payloads](../../xss.md) |
| 🖥️ Consola web | [Panel local estilo Matrix en el navegador `--ui`](../../webconsole.md) |
| 🚪 Escaneo de puertos BD | [15 servicios, sondeos sin autenticación, 3 niveles de severidad `--dbscan`](../../dbscan.md) |
| 🕸️ Grafo OSINT | [Grafo de reconocimiento pasivo y sin claves: subdominios, IPs, CVEs, ASN, contactos `--osint`](../../osint.md) |
| 📑 Informe unificado | [Un único informe HTML con pestañas: Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 Pipeline de agentes | [Análisis autónomo en 13 pasos](../../agents.md) |
| 🛡️ HeaderIntelAgent | [Fugas de información, cabeceras de seguridad ausentes, servidor desactualizado](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 tecnologías detectadas, dorks de CVE generados](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Recopila y clasifica correos: admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Teléfono, IBAN, código fiscal, tarjeta de crédito, SSN, fecha de nacimiento](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Extrae subdominios y genera `queries`](../../agents.md#subdomainharvesteragent) |
| 🔄 Crawl adaptativo | [Dorking recursivo en varias rondas](../../crawler.md) |
| 🔑 Fingerprinting HTTP | [22 perfiles de navegador/SO — Chrome, Firefox, Safari, móvil, etc.](../../fingerprinting.md) |
| 📊 Formatos de salida | [Informe HTML interactivo — todo se guarda en `Dump/`](../../output_formats.md) |
| 🗂️ Categorías de archivos | [7 categorías detectadas automáticamente — filtrado por lista blanca / negra](../../file_categories.md) |
| 🖥️ Referencia CLI completa | [Los 44 flags y todas las combinaciones posibles](../../cli.md) |

---

## Instalación rápida
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# Para Debian, Ubuntu o Kali.
## Automática
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py --wizard
```
## Manual
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
```
# Alpine / iOS (iSH)
Recomendado para **usuarios de iOS mediante [iSH](https://ish.app)** (Alpine Linux) y cualquier sistema basado en Alpine.<br>
`install.sh` detecta automáticamente el entorno y ejecuta la instalación correspondiente.
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

## Uso

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # Modo ASISTENTE &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # Búsqueda básica &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Generador de dorks + detección &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + sigilo &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Escaneo rápido &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Prueba SQLi directa sobre una URL &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Reprocesar un archivo de resultados guardado &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # Grafo OSINT &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Consola web &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## Ejemplos
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 Estructura del proyecto
```
DorkEye/
│ ├── dorkeye.py                      ← Motor de DorkEye
│ ├── requirements.txt                ← Dependencias de Python
│ ├── http_fingerprints.json          ← 22 perfiles HTTP de navegador/SO
│ ├── install.sh                      ← Detección de dispositivo + despacho (Linux/macOS/Termux/iSH)
│ ├── install.bat                     ← Instalador para Windows (doble clic)
│ ├── README.md                       ← README en inglés
│ ├── LICENSE                         ← Licencia MIT
│ ├── .gitignore                      ← Reglas de exclusión de Git
│ /Devices/                           ← Instaladores por dispositivo
│    /iOS/
│        ├── install_ish.sh           ← Instalador ligero para iSH (iOS) — sin lxml
│        └── ddg_lite.py              ← Backend de DuckDuckGo sin lxml
│    /Android/
│        └── install_termux.sh        ← Instalador para Termux (libxml2/libxslt + venv)
│    /Linux/
│        └── install_linux.sh         ← Instalador para Linux / macOS (venv)
│ /Tools/
│    ├── __init__.py                  ← Inicializador del paquete
│    ├── dork_generator.py            ← Generador de consultas dork
│    ├── dorkeye_agents.py            ← Pipeline de agentes
│    ├── dorkeye_patterns.py          ← Biblioteca de patrones compartida
│    ├── dorkeye_analyze.py           ← CLI de análisis independiente
│    ├── db_portscan.py               ← Escanea puertos de bases de datos expuestos
│    ├── osint.py                     ← Grafo OSINT pasivo (--osint)
│    ├── report.py                    ← Motor de informes HTML compartido (informe con pestañas)
│    ├── dorkeye_web.py               ← Interfaz web local
│    ├── sqli.py                      ← Inyección SQL con 5 métodos (105 payloads)
│    └── xss.py                       ← Inyección XSS con 4 métodos (111 payloads)
│ /Templates/
│    ├── dorks_templates.yaml         ← Plantilla por defecto
│    ├── example.yaml                 ← Plantilla de ejemplo
│    ├── sql.yaml                     ← Plantilla de dorks SQLi
│    └── wp-advanced.yaml             ← Plantilla de exposición de WordPress
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← Normas de la comunidad
│    ├── CONTRIBUTING.md              ← Guía de contribución
│    ├── SECURITY.md                  ← Política de seguridad
│    ├── FUNDING.yml                  ← Configuración de patrocinio
│    ├── pull_request_template.md     ← Plantilla de PR
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Plantilla de reporte de bugs
│        └── feature_request.md       ← Plantilla de solicitud de funciones
│     /workflows/
│        └── claude-dorkeye.yml       ← Agente IA de GitHub Actions
│ /Docs/
│    ├── overview.md                  ← Visión general del proyecto
│    ├── cli.md                       ← Referencia CLI completa (44 flags)
│    ├── wizard.md                    ← Guía del asistente interactivo
│    ├── sqli.md                      ← Referencia de inyección SQL
│    ├── xss.md                       ← Referencia de inyección XSS
│    ├── agents.md                    ← Guía del pipeline de agentes
│    ├── crawler.md                   ← Guía del crawler adaptativo
│    ├── dbscan.md                    ← Guía del escaneo de puertos BD
│    ├── osint.md                     ← Guía del grafo OSINT
│    ├── fingerprinting.md            ← Guía de fingerprinting HTTP
│    ├── http_fingerprints.md         ← Referencia de perfiles de fingerprint
│    ├── webconsole.md                ← Guía de la consola web
│     /devices/
│        ├── termux.md                ← Configuración en Termux / Android
│        ├── ish.md                   ← Configuración en iSH / iOS (modo ligero)
│        └── windows.md               ← Configuración en Windows (install.bat)
│     /languages/                     ← Traducciones del README
│    ├── output_formats.md            ← Guía de formatos de salida
│    ├── file_categories.md           ← Guía de categorías de archivos
│    ├── dork_generator.md            ← Guía del generador de dorks
│    ├── INSTALL.md                   ← Guía de instalación
│    ├── REPORT_HTML.md               ← Guía del informe HTML
│    ├── USAGE.md                     ← Ejemplos de uso
│    ├── DDGSEE.md                    ← Notas sobre el motor DuckDuckGo
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← Colección seleccionada de dorks
│        ├── JSON_exposure_dork.txt   ← Dorks de exposición JSON
│        └── sql_dorks.txt            ← Dorks orientados a SQLi
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← salida en tiempo de ejecución, no versionada (ver .gitignore)
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← Bases de datos del grafo OSINT
│    └── *.graphml                    ← Exportación del grafo OSINT
```
---

## Grafo OSINT

`--osint` convierte los hosts encontrados por tus dorks en un grafo de correlación, usando solo fuentes públicas
y **sin claves de API**: Certificate Transparency (crt.sh), RDAP, DNS-over-HTTPS, Shodan InternetDB,
DNS inverso, ASN/geolocalización y Wayback Machine. Por el camino se extraen correos y números de teléfono.

| Nivel | Qué recopila | Contacta con el objetivo |
|-------|------------------|--------------------|
| `--osint=1` | Datos del registrador, subdominios, registros DNS | No |
| `--osint` / `--osint=2` | Nivel 1 + puertos abiertos, CVEs conocidos, DNS inverso, ASN / país de cada IP | No |
| `--osint=3` | Nivel 2 + URLs archivadas, título de página / servidor / `security.txt` de cada host | Sí (una petición HTTP por host) |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

La pestaña **OSINT** muestra el grafo interactivo, los hallazgos (IPs con CVEs, hosts llamados `admin`, `dev`,
`staging`…, puertos abiertos más frecuentes), contactos, cada IP con puertos / ASN / país, pivotes por IP compartida y
clústeres de ASN, y permite descargarlo todo en JSON, CSV, TXT, GraphML o SQLite.
Cada ejecución genera un grafo nuevo. También disponible desde el asistente y la consola web.
Guía completa: [Docs/osint.md](../../osint.md)

---

## Inyección SQL
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## Informe
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**DorkEye se proporciona únicamente con fines educativos y para pruebas de seguridad autorizadas.**
> - Eres el único responsable de cumplir todas las leyes aplicables y de obtener una autorización explícita y por escrito antes de escanear, probar o sondear cualquier sistema, dominio o red que no sea de tu propiedad.
> - Los autores y colaboradores no aceptan ninguna responsabilidad por el mal uso ni por los daños derivados del uso de esta herramienta.

---

## 📞 Contacto

- **Autor:** I.C.W.T / xPloits3c  
- **Email:** dorkeye@protonmail.com  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Apoyo
 - **Las contribuciones son bienvenidas. ¡Anímate!**
 - **Si DorkEye te resulta útil, considera darle una estrella al repositorio 🌟**
 - **Invítame a un café y mantén el desarrollo con cafeína ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 Licencia
[Licencia MIT](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## Colaboradores
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
