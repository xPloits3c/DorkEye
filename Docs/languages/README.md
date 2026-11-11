# Translations / 翻译 / Traducciones / Traduções / Переводы / 翻訳 / Traduzioni

Translated versions of the main project [README](../../README.md).
The **English README in the repository root is the source of truth** — if a translation falls behind or conflicts, the English version wins.

| Language | File |
|----------|------|
| 🇬🇧 English (source) | [../../README.md](../../README.md) |
| 🇨🇳 简体中文 (Simplified Chinese) | [zh-CN/README.md](zh-CN/README.md) |
| 🇪🇸 Español (Spanish) | [es/README.md](es/README.md) |
| 🇧🇷 Português (Portuguese) | [pt-BR/README.md](pt-BR/README.md) |
| 🇷🇺 Русский (Russian) | [ru/README.md](ru/README.md) |
| 🇯🇵 日本語 (Japanese) | [ja/README.md](ja/README.md) |
| 🇮🇹 Italiano (Italian) | [it/README.md](it/README.md) |

Only the README is translated for now. The detailed guides under [`Docs/`](../) remain English-only.

---

## Adding or updating a translation

1. **Folder name = language code.** Use the BCP-47 / ISO code: `zh-CN` (Simplified Chinese), `zh-TW` (Traditional), `es`, `pt-BR`, `ru`, `ja`, `fr`, `de`, …
2. **Copy the structure of an existing translation** (e.g. `it/README.md`) so headings, images and tables line up with the English source.
3. **Do not translate** command lines, flags, file names, option names (`--osint`, `-u`, `--stealth`…) or anything inside ``` code blocks. Translate only prose, table text and comments.
4. **Keep the images as-is** — they are referenced by absolute GitHub URLs, so no copies are needed.
5. **Fix the relative links.** Translation files live two levels below the root, so links point back with `../../`:
   - Root files → `../../../README.md`, `../../../LICENSE`
   - Docs guides → `../../osint.md`, `../../cli.md`, `../../devices/ish.md`, …
6. **Update the language switch bar** at the top of every README so the new language appears in all of them, and mark the current file in **bold** (no link).
7. Add a row to the table above.

### Language switch bar (copy/paste)

Put this near the top of each translated README, with the current language in **bold** and its link removed:

```markdown
[English](../../../README.md) | [简体中文](../zh-CN/README.md) | [Español](../es/README.md) | [Português](../pt-BR/README.md) | [Русский](../ru/README.md) | [日本語](../ja/README.md) | [Italiano](../it/README.md)
```

The bar in the root `README.md` uses a different prefix (no `../`):

```markdown
**English** | [简体中文](Docs/languages/zh-CN/README.md) | [Español](Docs/languages/es/README.md) | [Português](Docs/languages/pt-BR/README.md) | [Русский](Docs/languages/ru/README.md) | [日本語](Docs/languages/ja/README.md) | [Italiano](Docs/languages/it/README.md)
```
