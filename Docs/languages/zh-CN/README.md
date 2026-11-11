<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | **简体中文** | [Español](../es/README.md) | [Português](../pt-BR/README.md) | [Русский](../ru/README.md) | [日本語](../ja/README.md) | [Italiano](../it/README.md)

</div>

> [!NOTE]
> 本文为英文版 README 的翻译。如有差异，以[英文原版](../../../README.md)为准。详细文档目前仅提供英文版。

# DorkEye – OSINT Dorking 工具

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

## 什么是 DorkEye？
**DorkEye** 是一款自动化的 `OSINT DORKING 工具`，通过智能搜索查询发现暴露在互联网上的 Web 资产。
- 它集成了基于 YAML 模板的 Dork 生成器（`soft` / `medium` / `aggressive` 三种模式）、SQL 注入与 XSS 测试模块、13 步自动化分析流水线、自适应递归爬虫、数据库端口扫描器以及被动式 OSINT 关系图 —— 所有结果汇总在一份带选项卡的 HTML 报告中。

- 它可以高效且隐蔽地识别被索引的目录、敏感文件、管理后台、数据库、备份、配置文件、凭据、个人身份信息（PII）、子域名以及技术指纹。

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## 为什么选择 DorkEye

- 全平台运行 —— Linux · macOS · Windows · Android（Termux）· iOS（iSH）
- 绕过 CAPTCHA 与频率限制
- 高级交互式 HTML 报告
- 保持匿名，避免 IP 被封锁
- 干净、未经过滤的搜索结果
- 连续数小时 Dorking —— DorkEye 不会被封禁。

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## 新功能 🥇

| 功能 | 说明 |
|---------|---------|
| 🧙 向导 | [交互式引导会话 —— 涵盖所有选项](../../wizard.md) |
| ⚙️ Dork 生成器 | [YAML 模板模式：`soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 全平台 | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) —— Python 3.9+ |
| 🎯 SQLi-XSS | [使用 `-u` 和 `-f` 直接测试 URL](../../sqli.md) |
| 📂 文件再处理 | [使用 `-f` 对已保存的结果文件重新运行 SQLi/XSS/分析/爬取](../../cli.md) |
| 💉 SQL 注入 | [5 种方法：105 个载荷](../../sqli.md) |
| 💉 XSS 注入 | [4 种方法：111 个载荷](../../xss.md) |
| 🖥️ Web 控制台 | [Matrix 风格的本地浏览器仪表盘 `--ui`](../../webconsole.md) |
| 🚪 数据库端口扫描 | [15 种服务，免认证探测，3 个严重级别 `--dbscan`](../../dbscan.md) |
| 🕸️ OSINT 关系图 | [被动、无需 API 密钥的侦察图：子域名、IP、CVE、ASN、联系人 `--osint`](../../osint.md) |
| 📑 统一报告 | [一份带选项卡的 HTML 报告：Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 Agent 流水线 | [13 步自动化分析](../../agents.md) |
| 🛡️ HeaderIntelAgent | [信息泄露、缺失的安全响应头、过时的服务器版本](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [可识别 35 种技术，并生成 CVE Dork](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [收集并分类邮箱：admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [电话、IBAN、税号、信用卡、SSN、出生日期](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [提取子域名并生成 `queries`](../../agents.md#subdomainharvesteragent) |
| 🔄 自适应爬取 | [多轮递归 Dorking](../../crawler.md) |
| 🔑 HTTP 指纹 | [22 种浏览器/操作系统配置 —— Chrome、Firefox、Safari、移动端等](../../fingerprinting.md) |
| 📊 输出格式 | [交互式 HTML 报告 —— 全部保存在 `Dump/`](../../output_formats.md) |
| 🗂️ 文件分类 | [7 种自动识别的分类 —— 白名单 / 黑名单过滤](../../file_categories.md) |
| 🖥️ 完整 CLI 参考 | [全部 44 个参数及所有可能的组合](../../cli.md) |

---

## 快速安装
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# 适用于 Debian、Ubuntu 或 Kali。
## 自动安装
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py --wizard
```
## 手动安装
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
```
# Alpine / iOS（iSH）
推荐 **通过 [iSH](https://ish.app) 使用的 iOS 用户**（Alpine Linux）以及任何基于 Alpine 的系统使用。<br>
`install.sh` 会自动检测运行环境并执行对应的安装流程。
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

## 使用方法

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # 向导模式 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # 基础搜索 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # Dork 生成器 + 检测 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + 隐蔽模式 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # 快速扫描 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # 对单个 URL 直接进行 SQLi 测试 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # 重新处理已保存的结果文件 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # OSINT 关系图 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Web 控制台 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## 示例
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 项目结构
```
DorkEye/
│ ├── dorkeye.py                      ← DorkEye 引擎
│ ├── requirements.txt                ← Python 依赖
│ ├── http_fingerprints.json          ← 22 种浏览器/操作系统 HTTP 配置
│ ├── install.sh                      ← 设备检测与分发（Linux/macOS/Termux/iSH）
│ ├── install.bat                     ← Windows 安装程序（双击运行）
│ ├── README.md                       ← 英文版 README
│ ├── LICENSE                         ← MIT 许可证
│ ├── .gitignore                      ← Git 忽略规则
│ /Devices/                           ← 各设备安装脚本
│    /iOS/
│        ├── install_ish.sh           ← iSH（iOS）精简安装脚本 —— 无需 lxml
│        └── ddg_lite.py              ← 不依赖 lxml 的 DuckDuckGo 后端
│    /Android/
│        └── install_termux.sh        ← Termux 安装脚本（libxml2/libxslt + venv）
│    /Linux/
│        └── install_linux.sh         ← Linux / macOS 安装脚本（venv）
│ /Tools/
│    ├── __init__.py                  ← 包初始化
│    ├── dork_generator.py            ← Dork 查询生成器
│    ├── dorkeye_agents.py            ← Agent 流水线
│    ├── dorkeye_patterns.py          ← 共享模式库
│    ├── dorkeye_analyze.py           ← 独立分析 CLI
│    ├── db_portscan.py               ← 扫描暴露的数据库端口
│    ├── osint.py                     ← 被动 OSINT 关系图（--osint）
│    ├── report.py                    ← 共享 HTML 报告引擎（选项卡报告）
│    ├── dorkeye_web.py               ← 本地 Web 界面
│    ├── sqli.py                      ← 5 种 SQL 注入方法（105 个载荷）
│    └── xss.py                       ← 4 种 XSS 注入方法（111 个载荷）
│ /Templates/
│    ├── dorks_templates.yaml         ← 默认模板
│    ├── example.yaml                 ← 示例模板
│    ├── sql.yaml                     ← SQLi Dork 模板
│    └── wp-advanced.yaml             ← WordPress 暴露面模板
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← 社区准则
│    ├── CONTRIBUTING.md              ← 贡献指南
│    ├── SECURITY.md                  ← 安全策略
│    ├── FUNDING.yml                  ← 赞助配置
│    ├── pull_request_template.md     ← PR 模板
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← Bug 报告模板
│        └── feature_request.md       ← 功能请求模板
│     /workflows/
│        └── claude-dorkeye.yml       ← GitHub Actions AI Agent
│ /Docs/
│    ├── overview.md                  ← 项目概览
│    ├── cli.md                       ← 完整 CLI 参考（44 个参数）
│    ├── wizard.md                    ← 交互式向导指南
│    ├── sqli.md                      ← SQL 注入参考
│    ├── xss.md                       ← XSS 注入参考
│    ├── agents.md                    ← Agent 流水线指南
│    ├── crawler.md                   ← 自适应爬虫指南
│    ├── dbscan.md                    ← 数据库端口扫描指南
│    ├── osint.md                     ← OSINT 关系图指南
│    ├── fingerprinting.md            ← HTTP 指纹指南
│    ├── http_fingerprints.md         ← 指纹配置参考
│    ├── webconsole.md                ← Web 控制台指南
│     /devices/
│        ├── termux.md                ← Termux / Android 安装
│        ├── ish.md                   ← iSH / iOS 安装（精简模式）
│        └── windows.md               ← Windows 安装（install.bat）
│     /languages/                     ← README 翻译版本
│    ├── output_formats.md            ← 输出格式指南
│    ├── file_categories.md           ← 文件分类指南
│    ├── dork_generator.md            ← Dork 生成器指南
│    ├── INSTALL.md                   ← 安装指南
│    ├── REPORT_HTML.md               ← HTML 报告指南
│    ├── USAGE.md                     ← 使用示例
│    ├── DDGSEE.md                    ← DuckDuckGo 引擎说明
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← 精选 Dork 合集
│        ├── JSON_exposure_dork.txt   ← JSON 暴露 Dork
│        └── sql_dorks.txt            ← 面向 SQLi 的 Dork
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← 运行时输出，不纳入版本控制（见 .gitignore）
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← OSINT 关系图数据库
│    └── *.graphml                    ← OSINT 关系图导出
```
---

## OSINT 关系图

`--osint` 仅使用公开数据源、**无需任何 API 密钥**，将 Dork 发现的主机转化为关联关系图：
证书透明度（crt.sh）、RDAP、DNS-over-HTTPS、Shodan InternetDB、反向 DNS、ASN/地理位置以及 Wayback Machine。
过程中还会提取邮箱和电话号码。

| 级别 | 收集内容 | 是否接触目标 |
|-------|------------------|--------------------|
| `--osint=1` | 注册商数据、子域名、DNS 记录 | 否 |
| `--osint` / `--osint=2` | 级别 1 + 每个 IP 的开放端口、已知 CVE、反向 DNS、ASN / 国家 | 否 |
| `--osint=3` | 级别 2 + 历史存档 URL、每个主机的页面标题 / 服务器 / `security.txt` | 是（每个主机一次 HTTP 请求） |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

**OSINT** 选项卡展示交互式关系图、发现项（带 CVE 的 IP、名为 `admin`、`dev`、`staging`… 的主机、最常见的开放端口）、
联系人、每个 IP 的端口 / ASN / 国家、共享 IP 关联以及 ASN 聚类，并可将全部数据下载为 JSON、CSV、TXT、GraphML 或 SQLite。
每次运行都会生成全新的关系图。向导和 Web 控制台中同样可用。
完整指南：[Docs/osint.md](../../osint.md)

---

## SQL 注入
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## 报告
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**DorkEye 仅供教育用途及经授权的安全测试使用。**
> - 您须自行负责遵守所有适用法律，并在扫描、测试或探测任何不属于您的系统、域名或网络之前，获得明确的书面授权。
> - 作者及贡献者对任何滥用行为或因使用本工具造成的任何损害概不负责。

---

## 📞 联系方式

- **作者：** I.C.W.T / xPloits3c  
- **邮箱：** dorkeye@protonmail.com  
- **Telegram：** https://t.me/DorkEye  
---

## ⭐ 支持
 - **欢迎贡献代码，非常期待你的参与。**
 - **如果你觉得 DorkEye 有用，请考虑为仓库点个 Star 🌟**
 - **请我喝杯咖啡，让开发保持满满动力 ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 许可证
[MIT 许可证](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## 贡献者
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
