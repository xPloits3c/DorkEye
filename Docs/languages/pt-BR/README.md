<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | [简体中文](../zh-CN/README.md) | [Español](../es/README.md) | **Português** | [Русский](../ru/README.md) | [日本語](../ja/README.md) | [Italiano](../it/README.md)

</div>

> [!NOTE]
> Este documento é uma tradução do README em inglês. Em caso de divergência, vale a [versão original em inglês](../../../README.md). Por enquanto, a documentação detalhada está disponível apenas em inglês.

# DorkEye – Ferramenta de OSINT Dorking

<!-- ── Row 1: Project identity ── -->
![Python](https://img.shields.io/badge/Python-3.9%2B-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
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

## O que é o DorkEye?
**DorkEye** é uma `FERRAMENTA DE OSINT DORKING` automatizada que descobre ativos web expostos por meio de consultas de busca inteligentes.
- Ele combina um gerador de dorks baseado em templates YAML (modos `soft` / `medium` / `aggressive`), um módulo de testes SQL e XSS, um pipeline de análise autônoma em 13 etapas, um crawler recursivo adaptativo, um scanner de portas de bancos de dados e um grafo OSINT passivo — tudo reunido em um único relatório HTML com abas.

- Ele pode identificar diretórios indexados, arquivos sensíveis, painéis de administração, bancos de dados, backups, arquivos de configuração, credenciais, dados pessoais (PII), subdomínios e impressões digitais de tecnologia — de forma eficiente e com controles de furtividade.

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Por que o DorkEye

- Roda em qualquer lugar — Linux · macOS · Windows · Android (Termux) · iOS (iSH)
- Contorna CAPTCHA e limites de requisições
- Relatório HTML avançado e interativo
- Mantém o anonimato e evita bloqueio de IP
- Resultados de busca limpos e sem filtro
- Faça dorking por horas — o DorkEye não será banido.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## Novidades 🥇

| Recurso | Detalhes |
|---------|---------|
| 🧙 Assistente | [Sessão guiada interativa — todas as opções](../../wizard.md) |
| ⚙️ Gerador de dorks | [Modos de template YAML: `soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 Todos os sistemas | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) — Python 3.9+ |
| 🎯 SQLi-XSS | [Teste URLs diretamente com `-u` e `-f`](../../sqli.md) |
| 📂 Reprocessamento de arquivos | [Execute novamente SQLi/XSS/análise/crawl em arquivos de resultados salvos com `-f`](../../cli.md) |
| 💉 Injeção SQL | [5 métodos: 105 payloads](../../sqli.md) |
| 💉 Injeção XSS | [4 métodos: 111 payloads](../../xss.md) |
| 🖥️ Console web | [Painel local estilo Matrix no navegador `--ui`](../../webconsole.md) |
| 🚪 Scan de portas de BD | [15 serviços, sondagens sem autenticação, 3 níveis de severidade `--dbscan`](../../dbscan.md) |
| 🕸️ Grafo OSINT | [Grafo de reconhecimento passivo e sem chaves: subdomínios, IPs, CVEs, ASN, contatos `--osint`](../../osint.md) |
| 📑 Relatório unificado | [Um único relatório HTML com abas: Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 Pipeline de agentes | [Análise autônoma em 13 etapas](../../agents.md) |
| 🛡️ HeaderIntelAgent | [Vazamentos de informação, cabeçalhos de segurança ausentes, servidor desatualizado](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 tecnologias detectadas, dorks de CVE gerados](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Coleta e classifica e-mails: admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Telefone, IBAN, código fiscal, cartão de crédito, SSN, data de nascimento](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Extrai subdomínios e gera `queries`](../../agents.md#subdomainharvesteragent) |
| 🔄 Crawl adaptativo | [Dorking recursivo em várias rodadas](../../crawler.md) |
| 🔑 Fingerprinting HTTP | [22 perfis de navegador/SO — Chrome, Firefox, Safari, mobile, etc.](../../fingerprinting.md) |
| 📊 Formatos de saída | [Relatório HTML interativo — tudo salvo em `Dump/`](../../output_formats.md) |
| 🗂️ Categorias de arquivos | [7 categorias detectadas automaticamente — filtro por lista branca / negra](../../file_categories.md) |
| 🖥️ Referência CLI completa | [Todas as 44 flags e todas as combinações possíveis](../../cli.md) |

---

## Instalação rápida
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# Para Debian, Ubuntu ou Kali.
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
Recomendado para **usuários de iOS via [iSH](https://ish.app)** (Alpine Linux) e qualquer sistema baseado em Alpine.<br>
O `install.sh` detecta automaticamente o ambiente e executa a instalação correspondente.
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

🔹 # Modo ASSISTENTE &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # Busca básica &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Gerador de dorks + detecção &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + furtividade &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Scan rápido &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Teste SQLi direto em uma URL &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Reprocessar um arquivo de resultados salvo &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # Grafo OSINT &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Console web &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## Exemplos
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 Estrutura do projeto
```
DorkEye/
│ ├── dorkeye.py                      ← Motor do DorkEye
│ ├── requirements.txt                ← Dependências Python
│ ├── http_fingerprints.json          ← 22 perfis HTTP de navegador/SO
│ ├── install.sh                      ← Detecção de dispositivo + despacho (Linux/macOS/Termux/iSH)
│ ├── install.bat                     ← Instalador para Windows (clique duplo)
│ ├── README.md                       ← README em inglês
│ ├── LICENSE                         ← Licença MIT
│ ├── .gitignore                      ← Regras de exclusão do Git
│ /Devices/                           ← Instaladores por dispositivo
│    /iOS/
│        ├── install_ish.sh           ← Instalador leve para iSH (iOS) — sem lxml
│        └── ddg_lite.py              ← Backend DuckDuckGo sem lxml
│    /Android/
│        └── install_termux.sh        ← Instalador para Termux (libxml2/libxslt + venv)
│    /Linux/
│        └── install_linux.sh         ← Instalador para Linux / macOS (venv)
│ /Tools/
│    ├── __init__.py                  ← Inicializador do pacote
│    ├── dork_generator.py            ← Gerador de consultas dork
│    ├── dorkeye_agents.py            ← Pipeline de agentes
│    ├── dorkeye_patterns.py          ← Biblioteca de padrões compartilhada
│    ├── dorkeye_analyze.py           ← CLI de análise independente
│    ├── db_portscan.py               ← Escaneia portas de bancos de dados expostas
│    ├── osint.py                     ← Grafo OSINT passivo (--osint)
│    ├── report.py                    ← Motor de relatórios HTML compartilhado (relatório com abas)
│    ├── dorkeye_web.py               ← Interface web local
│    ├── sqli.py                      ← Injeção SQL com 5 métodos (105 payloads)
│    └── xss.py                       ← Injeção XSS com 4 métodos (111 payloads)
│ /Templates/
│    ├── dorks_templates.yaml         ← Template padrão
│    ├── example.yaml                 ← Template de exemplo
│    ├── sql.yaml                     ← Template de dorks SQLi
│    └── wp-advanced.yaml             ← Template de exposição do WordPress
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← Diretrizes da comunidade
│    ├── CONTRIBUTING.md              ← Guia de contribuição
│    ├── SECURITY.md                  ← Política de segurança
│    ├── FUNDING.yml                  ← Configuração de patrocínio
│    ├── pull_request_template.md     ← Template de PR
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Template de reporte de bugs
│        └── feature_request.md       ← Template de solicitação de recursos
│     /workflows/
│        └── claude-dorkeye.yml       ← Agente de IA do GitHub Actions
│ /Docs/
│    ├── overview.md                  ← Visão geral do projeto
│    ├── cli.md                       ← Referência CLI completa (44 flags)
│    ├── wizard.md                    ← Guia do assistente interativo
│    ├── sqli.md                      ← Referência de injeção SQL
│    ├── xss.md                       ← Referência de injeção XSS
│    ├── agents.md                    ← Guia do pipeline de agentes
│    ├── crawler.md                   ← Guia do crawler adaptativo
│    ├── dbscan.md                    ← Guia do scan de portas de BD
│    ├── osint.md                     ← Guia do grafo OSINT
│    ├── fingerprinting.md            ← Guia de fingerprinting HTTP
│    ├── http_fingerprints.md         ← Referência de perfis de fingerprint
│    ├── webconsole.md                ← Guia do console web
│     /devices/
│        ├── termux.md                ← Configuração no Termux / Android
│        ├── ish.md                   ← Configuração no iSH / iOS (modo leve)
│        └── windows.md               ← Configuração no Windows (install.bat)
│     /languages/                     ← Traduções do README
│    ├── output_formats.md            ← Guia de formatos de saída
│    ├── file_categories.md           ← Guia de categorias de arquivos
│    ├── dork_generator.md            ← Guia do gerador de dorks
│    ├── INSTALL.md                   ← Guia de instalação
│    ├── REPORT_HTML.md               ← Guia do relatório HTML
│    ├── USAGE.md                     ← Exemplos de uso
│    ├── DDGSEE.md                    ← Notas sobre o motor DuckDuckGo
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← Coleção selecionada de dorks
│        ├── JSON_exposure_dork.txt   ← Dorks de exposição JSON
│        └── sql_dorks.txt            ← Dorks voltados para SQLi
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← saída em tempo de execução, não versionada (ver .gitignore)
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← Bancos de dados do grafo OSINT
│    └── *.graphml                    ← Exportação do grafo OSINT
```
---

## Grafo OSINT

O `--osint` transforma os hosts encontrados pelos seus dorks em um grafo de correlação, usando apenas fontes públicas
e **sem chaves de API**: Certificate Transparency (crt.sh), RDAP, DNS-over-HTTPS, Shodan InternetDB,
DNS reverso, ASN/geolocalização e Wayback Machine. Pelo caminho, e-mails e números de telefone são extraídos.

| Nível | O que coleta | Toca o alvo |
|-------|------------------|--------------------|
| `--osint=1` | Dados do registrador, subdomínios, registros DNS | Não |
| `--osint` / `--osint=2` | Nível 1 + portas abertas, CVEs conhecidos, DNS reverso, ASN / país de cada IP | Não |
| `--osint=3` | Nível 2 + URLs arquivadas, título da página / servidor / `security.txt` de cada host | Sim (uma requisição HTTP por host) |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

A aba **OSINT** mostra o grafo interativo, os achados (IPs com CVEs, hosts chamados `admin`, `dev`,
`staging`…, portas abertas mais frequentes), contatos, cada IP com portas / ASN / país, pivôs por IP compartilhada e
clusters de ASN, e permite baixar tudo em JSON, CSV, TXT, GraphML ou SQLite.
Cada execução gera um grafo novo. Também disponível no assistente e no console web.
Guia completo: [Docs/osint.md](../../osint.md)

---

## Injeção SQL
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## Relatório
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**O DorkEye é fornecido apenas para fins educacionais e de testes de segurança autorizados.**
> - Você é o único responsável por cumprir todas as leis aplicáveis e por obter autorização explícita e por escrito antes de escanear, testar ou sondar qualquer sistema, domínio ou rede que não seja de sua propriedade.
> - Os autores e contribuidores não aceitam qualquer responsabilidade por uso indevido ou por danos resultantes do uso desta ferramenta.

---

## 📞 Contato

- **Autor:** I.C.W.T / xPloits3c  
- **E-mail:** dorkeye@protonmail.com  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Apoio
 - **Contribuições são bem-vindas. Participe!**
 - **Se o DorkEye for útil para você, considere dar uma estrela no repositório 🌟**
 - **Pague um café e mantenha o desenvolvimento cafeinado ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 Licença
[Licença MIT](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## Contribuidores
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
