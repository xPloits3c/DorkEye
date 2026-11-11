<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | [简体中文](../zh-CN/README.md) | [Español](../es/README.md) | [Português](../pt-BR/README.md) | **Русский** | [日本語](../ja/README.md) | [Italiano](../it/README.md)

</div>

> [!NOTE]
> Этот документ — перевод английского README. В случае расхождений приоритет имеет [оригинальная английская версия](../../../README.md). Подробная документация пока доступна только на английском.

# DorkEye – инструмент OSINT-дорkинга

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

## Что такое DorkEye?
**DorkEye** — это автоматизированный `OSINT DORKING TOOL`, который находит открытые веб-ресурсы с помощью продуманных поисковых запросов.
- Он объединяет генератор дорков на YAML-шаблонах (режимы `soft` / `medium` / `aggressive`), модуль тестирования SQL и XSS, автономный конвейер анализа из 13 шагов, адаптивный рекурсивный краулер, сканер портов баз данных и пассивный OSINT-граф — всё собрано в едином HTML-отчёте со вкладками.

- Он способен выявлять проиндексированные каталоги, чувствительные файлы, админ-панели, базы данных, резервные копии, конфигурационные файлы, учётные данные, персональные данные (PII), поддомены и технологические отпечатки — эффективно и с контролем скрытности.

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## Почему DorkEye

- Работает везде — Linux · macOS · Windows · Android (Termux) · iOS (iSH)
- Обходит CAPTCHA и ограничения по частоте запросов
- Продвинутый интерактивный HTML-отчёт
- Сохраняет анонимность и избегает блокировки IP
- Чистые, нефильтрованные результаты поиска
- Дорчите часами — DorkEye не забанят.

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## Что нового 🥇

| Функция | Подробности |
|---------|---------|
| 🧙 Мастер | [Интерактивная пошаговая сессия — все опции](../../wizard.md) |
| ⚙️ Генератор дорков | [Режимы YAML-шаблонов: `soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 Все системы | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) — Python 3.9+ |
| 🎯 SQLi-XSS | [Тестирование URL напрямую через `-u` и `-f`](../../sqli.md) |
| 📂 Повторная обработка файлов | [Повторный запуск SQLi/XSS/анализа/краула по сохранённым файлам результатов через `-f`](../../cli.md) |
| 💉 SQL-инъекции | [5 методов: 105 полезных нагрузок](../../sqli.md) |
| 💉 XSS-инъекции | [4 метода: 111 полезных нагрузок](../../xss.md) |
| 🖥️ Веб-консоль | [Локальная панель в стиле Matrix в браузере `--ui`](../../webconsole.md) |
| 🚪 Скан портов БД | [15 сервисов, проверки без аутентификации, 3 уровня критичности `--dbscan`](../../dbscan.md) |
| 🕸️ OSINT-граф | [Пассивный граф разведки без ключей: поддомены, IP, CVE, ASN, контакты `--osint`](../../osint.md) |
| 📑 Единый отчёт | [Один HTML-отчёт со вкладками: Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 Конвейер агентов | [Автономный анализ из 13 шагов](../../agents.md) |
| 🛡️ HeaderIntelAgent | [Утечки информации, отсутствующие заголовки безопасности, устаревший сервер](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [Определяет 35 технологий, генерирует CVE-дорки](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [Собирает и классифицирует email: admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [Телефон, IBAN, налоговый код, банковская карта, SSN, дата рождения](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [Извлекает поддомены и генерирует `queries`](../../agents.md#subdomainharvesteragent) |
| 🔄 Адаптивный краул | [Рекурсивный многораундовый дорkинг](../../crawler.md) |
| 🔑 HTTP-фингерпринтинг | [22 профиля браузера/ОС — Chrome, Firefox, Safari, мобильные и др.](../../fingerprinting.md) |
| 📊 Форматы вывода | [Интерактивный HTML-отчёт — всё сохраняется в `Dump/`](../../output_formats.md) |
| 🗂️ Категории файлов | [7 автоопределяемых категорий — фильтрация по белому / чёрному списку](../../file_categories.md) |
| 🖥️ Полный справочник CLI | [Все 44 флага и все возможные комбинации](../../cli.md) |

---

## Быстрая установка
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# Для Debian, Ubuntu или Kali.
## Автоматическая
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py --wizard
```
## Ручная
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
```
# Alpine / iOS (iSH)
Рекомендуется для **пользователей iOS через [iSH](https://ish.app)** (Alpine Linux) и любых систем на базе Alpine.<br>
`install.sh` автоматически определяет окружение и запускает подходящую установку.
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

## Использование

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # Режим МАСТЕРА &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # Базовый поиск &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Генератор дорков + детект &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + скрытность &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # Быстрое сканирование &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # Прямой тест SQLi по URL &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # Повторная обработка сохранённого файла результатов &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # OSINT-граф &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Веб-консоль &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## Примеры
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 Структура проекта
```
DorkEye/
│ ├── dorkeye.py                      ← Движок DorkEye
│ ├── requirements.txt                ← Зависимости Python
│ ├── http_fingerprints.json          ← 22 HTTP-профиля браузера/ОС
│ ├── install.sh                      ← Определение устройства + запуск (Linux/macOS/Termux/iSH)
│ ├── install.bat                     ← Установщик для Windows (двойной клик)
│ ├── README.md                       ← Английский README
│ ├── LICENSE                         ← Лицензия MIT
│ ├── .gitignore                      ← Правила игнорирования Git
│ /Devices/                           ← Установщики по устройствам
│    /iOS/
│        ├── install_ish.sh           ← Лёгкий установщик для iSH (iOS) — без lxml
│        └── ddg_lite.py              ← Бэкенд DuckDuckGo без lxml
│    /Android/
│        └── install_termux.sh        ← Установщик для Termux (libxml2/libxslt + venv)
│    /Linux/
│        └── install_linux.sh         ← Установщик для Linux / macOS (venv)
│ /Tools/
│    ├── __init__.py                  ← Инициализатор пакета
│    ├── dork_generator.py            ← Генератор дорк-запросов
│    ├── dorkeye_agents.py            ← Конвейер агентов
│    ├── dorkeye_patterns.py          ← Общая библиотека паттернов
│    ├── dorkeye_analyze.py           ← Отдельный CLI анализа
│    ├── db_portscan.py               ← Сканирует открытые порты баз данных
│    ├── osint.py                     ← Пассивный OSINT-граф (--osint)
│    ├── report.py                    ← Общий движок HTML-отчётов (отчёт со вкладками)
│    ├── dorkeye_web.py               ← Локальный веб-интерфейс
│    ├── sqli.py                      ← SQL-инъекции, 5 методов (105 нагрузок)
│    └── xss.py                       ← XSS-инъекции, 4 метода (111 нагрузок)
│ /Templates/
│    ├── dorks_templates.yaml         ← Шаблон по умолчанию
│    ├── example.yaml                 ← Пример шаблона
│    ├── sql.yaml                     ← Шаблон SQLi-дорков
│    └── wp-advanced.yaml             ← Шаблон экспозиции WordPress
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← Правила сообщества
│    ├── CONTRIBUTING.md              ← Руководство по вкладу
│    ├── SECURITY.md                  ← Политика безопасности
│    ├── FUNDING.yml                  ← Конфигурация спонсорства
│    ├── pull_request_template.md     ← Шаблон PR
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Шаблон отчёта об ошибке
│        └── feature_request.md       ← Шаблон запроса функции
│     /workflows/
│        └── claude-dorkeye.yml       ← ИИ-агент GitHub Actions
│ /Docs/
│    ├── overview.md                  ← Обзор проекта
│    ├── cli.md                       ← Полный справочник CLI (44 флага)
│    ├── wizard.md                    ← Руководство по интерактивному мастеру
│    ├── sqli.md                      ← Справочник по SQL-инъекциям
│    ├── xss.md                       ← Справочник по XSS-инъекциям
│    ├── agents.md                    ← Руководство по конвейеру агентов
│    ├── crawler.md                   ← Руководство по адаптивному краулеру
│    ├── dbscan.md                    ← Руководство по сканированию портов БД
│    ├── osint.md                     ← Руководство по OSINT-графу
│    ├── fingerprinting.md            ← Руководство по HTTP-фингерпринтингу
│    ├── http_fingerprints.md         ← Справочник профилей фингерпринтов
│    ├── webconsole.md                ← Руководство по веб-консоли
│     /devices/
│        ├── termux.md                ← Настройка Termux / Android
│        ├── ish.md                   ← Настройка iSH / iOS (лёгкий режим)
│        └── windows.md               ← Настройка Windows (install.bat)
│     /languages/                     ← Переводы README
│    ├── output_formats.md            ← Руководство по форматам вывода
│    ├── file_categories.md           ← Руководство по категориям файлов
│    ├── dork_generator.md            ← Руководство по генератору дорков
│    ├── INSTALL.md                   ← Руководство по установке
│    ├── REPORT_HTML.md               ← Руководство по HTML-отчёту
│    ├── USAGE.md                     ← Примеры использования
│    ├── DDGSEE.md                    ← Заметки о движке DuckDuckGo
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← Подобранная коллекция дорков
│        ├── JSON_exposure_dork.txt   ← Дорки экспозиции JSON
│        └── sql_dorks.txt            ← Дорки, ориентированные на SQLi
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← вывод во время выполнения, не версионируется (см. .gitignore)
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← Базы данных OSINT-графа
│    └── *.graphml                    ← Экспорт OSINT-графа
```
---

## OSINT-граф

`--osint` превращает хосты, найденные вашими дорками, в граф корреляций, используя только публичные источники
и **без API-ключей**: Certificate Transparency (crt.sh), RDAP, DNS-over-HTTPS, Shodan InternetDB,
обратный DNS, ASN/геолокацию и Wayback Machine. По пути извлекаются email и номера телефонов.

| Уровень | Что собирает | Контактирует с целью |
|-------|------------------|--------------------|
| `--osint=1` | Данные регистратора, поддомены, DNS-записи | Нет |
| `--osint` / `--osint=2` | Уровень 1 + открытые порты, известные CVE, обратный DNS, ASN / страна для каждого IP | Нет |
| `--osint=3` | Уровень 2 + архивные URL, заголовок страницы / сервер / `security.txt` каждого хоста | Да (один HTTP-запрос на хост) |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

Вкладка **OSINT** показывает интерактивный граф, находки (IP с CVE, хосты с именами `admin`, `dev`,
`staging`…, самые частые открытые порты), контакты, каждый IP с портами / ASN / страной, пивоты по общим IP и
кластеры ASN, и позволяет скачать всё в JSON, CSV, TXT, GraphML или SQLite.
Каждый запуск строит новый граф. Также доступно из мастера и веб-консоли.
Полное руководство: [Docs/osint.md](../../osint.md)

---

## SQL-инъекции
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## Отчёт
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**DorkEye предоставляется исключительно в образовательных целях и для авторизованного тестирования безопасности.**
> - Вы несёте полную ответственность за соблюдение всех применимых законов и за получение явного письменного разрешения перед сканированием, тестированием или зондированием любой системы, домена или сети, которые вам не принадлежат.
> - Авторы и участники не несут ответственности за неправомерное использование или любой ущерб, возникший в результате использования этого инструмента.

---

## 📞 Контакты

- **Автор:** I.C.W.T / xPloits3c  
- **Email:** dorkeye@protonmail.com  
- **Telegram:** https://t.me/DorkEye  
---

## ⭐ Поддержка
 - **Вклад приветствуется, присоединяйтесь.**
 - **Если DorkEye вам полезен, пожалуйста, поставьте звезду репозиторию 🌟**
 - **Угостите кофе и поддержите разработку ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 Лицензия
[Лицензия MIT](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## Участники
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
