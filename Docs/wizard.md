# Wizard — DorkEye v4.8

The wizard is an interactive guided session that walks through every option without requiring any CLI knowledge. Recommended for first use or exploratory sessions.

---

## Launch

```bash
python dorkeye.py --wizard
```

No other flags are needed — the wizard ignores them all.

---

## Main Menu

```
┌─[ DorkEye Wizard ]
│  1) Dork Search         — search with a dork or dork file
│  2) Dork Generator      — generate dorks from YAML templates
│  0) Exit
└─>
```

---

## Choice 1 — Dork Search

The wizard asks for each option in sequence:

| Prompt | What to enter | Example |
|--------|--------------|---------|
| Dork string or file | A dork or path to `.txt` file | `site:example.com filetype:pdf` |
| Result count | Number of results per dork | `50` |
| Enable SQLi? | `y` / `n` | `y` |
| Enable stealth? | `y` / `n` | `n` |
| Output file | Filename with extension | `results.json` |
| Run analysis? | `y` / `n` (shown if output is `.json`) | `y` |
| Run crawl? | `y` / `n` | `n` |

All prompts have sensible defaults — press Enter to accept.

---

## Choice 2 — Dork Generator

| Prompt | Options |
|--------|---------|
| Template source | Default / All templates / Specific file |
| Category | All categories, or pick one by number |
| Generation mode | `soft` / `medium` / `aggressive` |
| Output file | Filename with extension |
| Run analysis? | `y` / `n` |
| Run crawl? | `y` / `n` |

---

## Keyboard Shortcuts During Search

| Key | Action |
|-----|--------|
| `Ctrl+C` (once) | Skip current dork and move to next |
| `Ctrl+C` (twice, within 1.5s) | Stop the session entirely |

These work at any point during the search — mid-delay, mid-dork, or during SQLi testing.

---

## When to Use the Wizard vs CLI

| Situation | Use |
|-----------|-----|
| First time running DorkEye | Wizard |
| Exploring options interactively | Wizard |
| Repeatable / scriptable tasks | CLI flags |
| CI/CD or automation | CLI flags |
| All options known in advance | CLI flags |
