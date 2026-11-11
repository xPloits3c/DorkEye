<div align="center">
<img width="1984" height="992" alt="image" src="https://github.com/user-attachments/assets/08252ec0-8164-4e98-b167-0f54e2808ba6" />

</div>

---

<div align="center">

[English](../../../README.md) | [简体中文](../zh-CN/README.md) | [Español](../es/README.md) | [Português](../pt-BR/README.md) | [Русский](../ru/README.md) | **日本語** | [Italiano](../it/README.md)

</div>

> [!NOTE]
> 本書は英語版 README の翻訳です。相違がある場合は[英語の原文](../../../README.md)が優先されます。詳細なドキュメントは現時点では英語のみ提供されています。

# DorkEye – OSINT ドーキングツール

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

## DorkEye とは？
**DorkEye** は、高度な検索クエリを通じて公開された Web 資産を発見する自動化された `OSINT ドーキングツール` です。
- YAML テンプレート駆動のドーク生成器（`soft` / `medium` / `aggressive` モード）、SQL・XSS テストモジュール、13 ステップの自律分析パイプライン、適応型の再帰クローラー、データベースのポートスキャナー、受動的な OSINT グラフを統合し、すべてをタブ付きの単一 HTML レポートにまとめます。

- インデックスされたディレクトリ、機密ファイル、管理パネル、データベース、バックアップ、設定ファイル、認証情報、個人情報（PII）、サブドメイン、技術フィンガープリントを、効率的かつステルス制御のもとで識別できます。

<img width="1186" height="778" alt="startdev4 9 5" src="https://github.com/user-attachments/assets/82056363-5f7a-4fe8-9aa1-df662e09796b" />
<img width="1202" height="832" alt="startdev4 9 5_0" src="https://github.com/user-attachments/assets/1f593af6-5908-4f35-b2b9-fe7f89417589" />

---

## DorkEye を選ぶ理由

- あらゆる環境で動作 — Linux · macOS · Windows · Android（Termux）· iOS（iSH）
- CAPTCHA とレート制限を回避
- 高度でインタラクティブな HTML レポート
- 匿名性を維持し、IP ブロックを回避
- クリーンでフィルタされていない検索結果
- 何時間でもドーキング可能 — DorkEye は BAN されません。

<img width="1437" height="652" alt="564558417-37385827-9112-4efe-aa0a-f8941da0a2d9" src="https://github.com/user-attachments/assets/df21ead3-dd90-4692-9eab-259c6582ae86" />

---

## 新機能 🥇

| 機能 | 詳細 |
|---------|---------|
| 🧙 ウィザード | [対話型ガイドセッション — 全オプション対応](../../wizard.md) |
| ⚙️ ドーク生成器 | [YAML テンプレートモード：`soft` / `medium` / `aggressive`](../../dork_generator.md) |
| 📱 全システム対応 | [Android/Termux](../../devices/termux.md) · [iOS/iSH](../../devices/ish.md) · [macOS](../../INSTALL.md) · [Linux](../../INSTALL.md) · [Windows](../../devices/windows.md) — Python 3.7+ |
| 🎯 SQLi-XSS | [`-u` と `-f` で URL を直接テスト](../../sqli.md) |
| 📂 ファイル再処理 | [`-f` で保存済み結果ファイルに対し SQLi/XSS/分析/クロールを再実行](../../cli.md) |
| 💉 SQL インジェクション | [5 手法：105 ペイロード](../../sqli.md) |
| 💉 XSS インジェクション | [4 手法：111 ペイロード](../../xss.md) |
| 🖥️ Web コンソール | [ブラウザで動く Matrix 風ローカルダッシュボード `--ui`](../../webconsole.md) |
| 🚪 DB ポートスキャン | [15 サービス、認証なしプローブ、3 段階の深刻度 `--dbscan`](../../dbscan.md) |
| 🕸️ OSINT グラフ | [受動的でキー不要の偵察グラフ：サブドメイン、IP、CVE、ASN、連絡先 `--osint`](../../osint.md) |
| 📑 統合レポート | [タブ付きの単一 HTML レポート：Dorks · Analyze · DBScan · Crawl · OSINT](../../output_formats.md#tabbed-report) |
| 🤖 エージェントパイプライン | [13 ステップの自律分析](../../agents.md) |
| 🛡️ HeaderIntelAgent | [情報漏洩、欠落したセキュリティヘッダー、古いサーバー](../../agents.md#headerintelagent) |
| 🧬 TechFingerprintAgent | [35 の技術を検出し、CVE ドークを生成](../../agents.md#techfingerprintagent) |
| 📧 EmailHarvesterAgent | [メールを収集・分類：admin / security / info..](../../agents.md#emailharvesteragent) |
| 🔐 PiiDetectorAgent | [電話番号、IBAN、納税者番号、クレジットカード、SSN、生年月日](../../agents.md#piidetectoragent) |
| 🌐 SubdomainAgent | [サブドメインを抽出し `queries` を生成](../../agents.md#subdomainharvesteragent) |
| 🔄 適応型クロール | [再帰的なマルチラウンドドーキング](../../crawler.md) |
| 🔑 HTTP フィンガープリント | [22 のブラウザ/OS プロファイル — Chrome、Firefox、Safari、モバイルなど](../../fingerprinting.md) |
| 📊 出力形式 | [インタラクティブな HTML レポート — すべて `Dump/` に保存](../../output_formats.md) |
| 🗂️ ファイルカテゴリ | [7 種類の自動検出カテゴリ — ホワイトリスト / ブラックリストフィルタ](../../file_categories.md) |
| 🖥️ CLI 完全リファレンス | [44 のフラグとすべての組み合わせ](../../cli.md) |

---

## クイックインストール
```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv git
```
# Debian、Ubuntu、Kali 向け。
## 自動
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  sh install.sh
  source dorkeye_env/bin/activate
  python dorkeye.py --wizard
```
## 手動
```bash
  git clone https://github.com/xPloits3c/DorkEye.git
  cd DorkEye
  python3 -m venv dorkeye_env
  source dorkeye_env/bin/activate
  pip install -r requirements.txt
  python dorkeye.py --wizard
```
# Alpine / iOS（iSH）
**[iSH](https://ish.app) 経由の iOS ユーザー**（Alpine Linux）や Alpine ベースのシステムに推奨です。<br>
`install.sh` が環境を自動検出し、対応するセットアップを実行します。
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

## 使い方

<img width="727" height="805" alt="dev5 0usage" src="https://github.com/user-attachments/assets/99927171-0c7f-4659-9608-ae554aec518e" />

---

🔹 # ウィザードモード &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../wizard.md)
```bash
  python3 dorkeye.py --wizard
```
🔹 # 基本検索 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d "inurl:admin" -o results.txt
```
🔹 # ドーク生成器 + 検出 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../dork_generator.md)
```bash
  python3 dorkeye.py --dg=sqli --mode=aggressive --sqli --stealth -o report.json
```
🔹 # SQLi + ステルス &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -d "site:example.com .php?id=" --sqli --stealth -o scan.html
```
🔹 # 高速スキャン &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -d dorks.txt --no-analyze -c 200 -o fast_results.csv
```
🔹 # URL への直接 SQLi テスト &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../sqli.md)
```bash
  python3 dorkeye.py -u "https://target.com/page.php?id=1" --sqli --stealth -o result.json
```
🔹 # 保存済み結果ファイルの再処理 &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../cli.md)
```bash
  python3 dorkeye.py -f Dump/results.json --sqli --xss --dbscan --analyze -o retest.html
```
🔹 # OSINT グラフ &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../osint.md)
```bash
  python3 dorkeye.py -d "site:example.com" --osint -o recon.html
  python3 dorkeye.py --osint-seed example.com --osint=1
```
🔹 # Web コンソール &nbsp;[![Docs](https://img.shields.io/badge/📖_Docs-2088FF?style=flat-square)](../../webconsole.md)
```bash
  python3 dorkeye.py --ui
```

<img width="1549" height="609" alt="image" src="https://github.com/user-attachments/assets/aae464c0-3320-4050-b11b-d83c4e3f9c54" />


## 例
<img width="938" height="832" alt="de-hex" src="https://github.com/user-attachments/assets/da253967-45a7-4249-aed2-9726eaa37b79" />

---

## 📁 プロジェクト構成
```
DorkEye/
│ ├── dorkeye.py                      ← DorkEye エンジン
│ ├── requirements.txt                ← Python 依存関係
│ ├── http_fingerprints.json          ← 22 のブラウザ/OS HTTP プロファイル
│ ├── install.sh                      ← デバイス検出 + ディスパッチ（Linux/macOS/Termux/iSH）
│ ├── install.bat                     ← Windows インストーラー（ダブルクリック）
│ ├── README.md                       ← 英語版 README
│ ├── LICENSE                         ← MIT ライセンス
│ ├── .gitignore                      ← Git 除外ルール
│ /Devices/                           ← デバイス別インストーラー
│    /iOS/
│        ├── install_ish.sh           ← iSH（iOS）軽量インストーラー — lxml 不要
│        └── ddg_lite.py              ← lxml 不要の DuckDuckGo バックエンド
│    /Android/
│        └── install_termux.sh        ← Termux インストーラー（libxml2/libxslt + venv）
│    /Linux/
│        └── install_linux.sh         ← Linux / macOS インストーラー（venv）
│ /Tools/
│    ├── __init__.py                  ← パッケージ初期化
│    ├── dork_generator.py            ← ドーククエリ生成器
│    ├── dorkeye_agents.py            ← エージェントパイプライン
│    ├── dorkeye_patterns.py          ← 共有パターンライブラリ
│    ├── dorkeye_analyze.py           ← スタンドアロン分析 CLI
│    ├── db_portscan.py               ← 公開されたデータベースポートをスキャン
│    ├── osint.py                     ← 受動的 OSINT グラフ（--osint）
│    ├── report.py                    ← 共有 HTML レポートエンジン（タブ付きレポート）
│    ├── dorkeye_web.py               ← ローカル Web インターフェース
│    ├── sqli.py                      ← 5 手法の SQL インジェクション（105 ペイロード）
│    └── xss.py                       ← 4 手法の XSS インジェクション（111 ペイロード）
│ /Templates/
│    ├── dorks_templates.yaml         ← デフォルトテンプレート
│    ├── example.yaml                 ← サンプルテンプレート
│    ├── sql.yaml                     ← SQLi ドークテンプレート
│    └── wp-advanced.yaml             ← WordPress 露出テンプレート
│ /.github/
│    ├── CODE_OF_CONDUCT.md           ← コミュニティガイドライン
│    ├── CONTRIBUTING.md              ← コントリビューションガイド
│    ├── SECURITY.md                  ← セキュリティポリシー
│    ├── FUNDING.yml                  ← スポンサー設定
│    ├── pull_request_template.md     ← PR テンプレート
│     /ISSUE_TEMPLATE/
│        ├── bug_report.md            ← バグ報告テンプレート
│        └── feature_request.md       ← 機能要望テンプレート
│     /workflows/
│        └── claude-dorkeye.yml       ← GitHub Actions AI エージェント
│ /Docs/
│    ├── overview.md                  ← プロジェクト概要
│    ├── cli.md                       ← CLI 完全リファレンス（44 フラグ）
│    ├── wizard.md                    ← 対話型ウィザードガイド
│    ├── sqli.md                      ← SQL インジェクションリファレンス
│    ├── xss.md                       ← XSS インジェクションリファレンス
│    ├── agents.md                    ← エージェントパイプラインガイド
│    ├── crawler.md                   ← 適応型クローラーガイド
│    ├── dbscan.md                    ← DB ポートスキャンガイド
│    ├── osint.md                     ← OSINT グラフガイド
│    ├── fingerprinting.md            ← HTTP フィンガープリントガイド
│    ├── http_fingerprints.md         ← フィンガープリントプロファイルリファレンス
│    ├── webconsole.md                ← Web コンソールガイド
│     /devices/
│        ├── termux.md                ← Termux / Android セットアップ
│        ├── ish.md                   ← iSH / iOS セットアップ（軽量モード）
│        └── windows.md               ← Windows セットアップ（install.bat）
│     /languages/                     ← README の翻訳
│    ├── output_formats.md            ← 出力形式ガイド
│    ├── file_categories.md           ← ファイルカテゴリガイド
│    ├── dork_generator.md            ← ドーク生成器ガイド
│    ├── INSTALL.md                   ← インストールガイド
│    ├── REPORT_HTML.md               ← HTML レポートガイド
│    ├── USAGE.md                     ← 使用例
│    ├── DDGSEE.md                    ← DuckDuckGo エンジンのメモ
│     /Dorks/
│        ├── Dorks_Collection_List.txt ← 厳選ドークコレクション
│        ├── JSON_exposure_dork.txt   ← JSON 露出ドーク
│        └── sql_dorks.txt            ← SQLi 向けドーク
│ /Screenshots/
│    ├── dev_logo_0.png
│    ├── dev_logo_1.png
│    ├── dev5_menu_h0.png
│    ├── dev5_menu_h1.png
│    ├── directsqltest.png
│    ├── directsqltesthtml.png
│    ├── sqlmultipletestfromfile.png
│    └── sqlmultipletestfromfilehtml.png
│ /Dump/                              ← 実行時の出力、バージョン管理対象外（.gitignore 参照）
│    ├── *.csv
│    ├── *.json
│    ├── *.txt
│    ├── *.html
│    ├── *_osint.sqlite / osint_*.sqlite ← OSINT グラフデータベース
│    └── *.graphml                    ← OSINT グラフエクスポート
```
---

## OSINT グラフ

`--osint` は、ドークで見つかったホストを相関グラフに変換します。公開ソースのみを使用し、
**API キーは不要**です：Certificate Transparency（crt.sh）、RDAP、DNS-over-HTTPS、Shodan InternetDB、
逆引き DNS、ASN/地理情報、Wayback Machine。その過程でメールアドレスと電話番号も抽出されます。

| レベル | 収集内容 | ターゲットへの接触 |
|-------|------------------|--------------------|
| `--osint=1` | レジストラ情報、サブドメイン、DNS レコード | なし |
| `--osint` / `--osint=2` | レベル 1 + 各 IP の開放ポート、既知の CVE、逆引き DNS、ASN / 国 | なし |
| `--osint=3` | レベル 2 + アーカイブ URL、各ホストのページタイトル / サーバー / `security.txt` | あり（ホストごとに 1 回の HTTP リクエスト） |

```bash
# Dorks + OSINT → one report with Dorks and OSINT tabs
python3 dorkeye.py -d "site:example.com" --osint -o recon.html

# OSINT only, from known domains / IPs
python3 dorkeye.py --osint-seed example.com --osint-seed 203.0.113.10

# Full pass with exports for Gephi / spreadsheets
python3 dorkeye.py -d dorks.txt --osint=3 --osint-export csv,graphml,txt -o target.html
```

**OSINT** タブには、インタラクティブなグラフ、発見内容（CVE のある IP、`admin`、`dev`、
`staging`… という名前のホスト、上位の開放ポート）、連絡先、ポート / ASN / 国を含む各 IP、共有 IP のピボット、
ASN クラスターが表示され、すべてを JSON、CSV、TXT、GraphML、SQLite としてダウンロードできます。
実行ごとに新しいグラフが構築されます。ウィザードや Web コンソールからも利用可能です。
完全ガイド：[Docs/osint.md](../../osint.md)

---

## SQL インジェクション
<img width="2048" height="1564" alt="image" src="https://github.com/user-attachments/assets/17dc0710-c057-4485-8c25-805e2dda0a0b" />


## レポート
![image](https://github.com/user-attachments/assets/28b71d4e-0cb2-478d-a1f2-f49c98f9f8aa)
<img width="1142" height="730" alt="image" src="https://github.com/user-attachments/assets/1f694bbc-af46-4bec-8654-6ff0b762f199" />

---

> [!WARNING] 
**DorkEye は、教育および認可されたセキュリティテストの目的でのみ提供されます。**
> - 適用されるすべての法律を遵守すること、および自身が所有しないシステム・ドメイン・ネットワークをスキャン、テスト、プローブする前に明示的な書面による許可を得ることについて、あなた自身が全責任を負います。
> - 作者および貢献者は、誤用や本ツールの使用に起因するいかなる損害についても責任を負いません。

---

## 📞 連絡先

- **作者：** I.C.W.T / xPloits3c  
- **メール：** dorkeye@protonmail.com  
- **Telegram：** https://t.me/DorkEye  
---

## ⭐ サポート
 - **ぜひコントリビュートしてください。歓迎します。**
 - **DorkEye が役に立ったら、リポジトリにスターをお願いします 🌟**
 - **コーヒーをおごって、開発をカフェイン漬けに保ってください ☕**

<div align="center">

[![Sponsor DorkEye](https://img.shields.io/badge/Sponsor-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/DorkEyeProject)

</div>

---

## 📜 ライセンス
[MIT ライセンス](../../../LICENSE) © 2026 I.C.W.T xPloits3c



## コントリビューター
<a href="https://github.com/xPloits3c/DorkEye/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xPloits3c/DorkEye" />
</a>
<div align="center">

![Typing SVG](https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=22&pause=1200&color=39FF14&background=000000&center=true&vCenter=true&width=600&lines=DorkEye+%7C+OSINT+Dorking+Tool;I+don%27t+hack+systems%2C+I+expose+their+secrets)

</div>
