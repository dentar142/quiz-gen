# quiz-gen

> Turn any multiple-choice question bank — Word, PDF, Excel, CSV, Markdown,
> plain text — into a self-contained, single-file HTML study app.
> Guided by Claude Code, runs fully offline, six visual themes, three study modes.

![version](https://img.shields.io/badge/version-2.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![claude code skill](https://img.shields.io/badge/Claude%20Code-skill-7C3AED)
![python](https://img.shields.io/badge/python-3.9%2B-yellow)

---

## What it does

You drop in a multiple-choice file. Claude Code walks you through six numbered
stages — dependency check, file intake, parse confirmation, style / mode
interview, generation, verification — and you walk away with a `.html` file
that you can double-click to study from.

- Embedded data, no server, no build step
- Works on phone / tablet / desktop
- Dark mode, keyboard shortcuts, optional PWA install
- Spaced-repetition memory algorithm built in

```
docx / pdf / xlsx / csv / txt / md
              │
              ▼
       quiz-gen skill
              │
              ▼
   single-file HTML study app
   (offline · responsive · themed)
```

---

## Highlights

| Area | What you get |
|------|---|
| Question types | single · multi · true/false · fill-in-blank · short-answer (A–F options) |
| Visual themes | **Fluent** · **Sketch** · **Material 3** · **Neumorphism** · **Terminal** · **Paper** |
| Study modes | sequential by chapter · random with spaced-repetition · timed test (configurable mix) |
| UI languages | zh-CN · en-US · ja-JP (or add your own JSON) |
| Inputs | `.docx` `.pdf` `.txt` `.md` `.xlsx` `.csv` + multi-file merge |
| Exports | Anki CSV/apkg · Quizlet TSV · printable PDF · editable Word |
| Power features | LaTeX rendering · image extraction · PWA install · GitHub Gist cloud sync · per-question notes · auto wrong-answer practice · build manifest · dedup · strict/lenient · externalized regex |

---

## Install

Clone into your Claude Code skills directory:

```bash
# Windows (PowerShell)
git clone https://github.com/dentar142/quiz-gen.git "$env:USERPROFILE\.claude\skills\quiz-gen"

# macOS / Linux
git clone https://github.com/dentar142/quiz-gen.git ~/.claude/skills/quiz-gen
```

Install Python dependencies (one-time):

```bash
pip install python-docx PyMuPDF openpyxl pyyaml
# Optional richer exports
pip install genanki reportlab
```

Restart Claude Code. The skill appears as **`quiz-gen`** and can be triggered by:

- typing `/quiz-gen`
- saying anything like "把这份 docx 题库做成网页测试" / "convert this question bank to an HTML quiz"

---

## Guided workflow (6 stages)

```
[0] Pre-flight     — dependency check + plugin recommendations
[1] File intake    — paste path(s); auto-detects format
[2] Parse + preview — opens _preview.html with first N questions
[3] Style / mode   — pick theme, modes, scoring, language, features
[4] Generate       — runs build_html.py; emits .html + build.json
[5] Verify         — placeholder check, JS syntax, tag balance
[6] Wrap-up        — keyboard shortcuts, file paths
```

Each stage pauses for confirmation. Pass `--yes` to replay last config from
`~/.quiz-gen/last.json`.

---

## Direct CLI usage

If you want to script without Claude:

```bash
SKILL=~/.claude/skills/quiz-gen

# Parse → JSON (DOCX/PDF/TXT/MD)
python "$SKILL/scripts/parse_questions.py" --input mybank.docx --output q.json

# Parse → JSON (XLSX/CSV)
python "$SKILL/scripts/parse_xlsx.py" --input mybank.xlsx --output q.json

# Merge multiple sources + dedup
python "$SKILL/scripts/merge.py" --inputs a.json b.json --output merged.json --dedup

# Visual preview before committing to a full build
python "$SKILL/scripts/preview.py" --data q.json --output _preview.html --limit 8 --open

# Build HTML (Fluent theme, all 3 modes, Chinese UI, PWA + cloud sync)
python "$SKILL/scripts/build_html.py" \
    --data q.json \
    --template "$SKILL/templates/fluent.html" \
    --output study.html \
    --lang zh-CN --pwa --cloud-sync

# Verify
python "$SKILL/scripts/build_html.py" --check study.html

# Export to other formats
python "$SKILL/scripts/export.py" --data q.json --format anki    --output cards.csv
python "$SKILL/scripts/export.py" --data q.json --format quizlet --output cards.tsv
python "$SKILL/scripts/export.py" --data q.json --format pdf     --output exam.pdf
python "$SKILL/scripts/export.py" --data q.json --format docx    --output exam.docx
```

---

## Question types

| type   | options          | answer JSON                  | UI                                  |
|--------|------------------|------------------------------|-------------------------------------|
| single | A–F              | `"C"`                        | radio · click = submit              |
| multi  | A–F              | `"ABC"`                      | checkbox · "Submit" button          |
| tf     | A=对 / B=错      | `"A"` or `"B"`               | two large buttons                   |
| fill   | (none)           | `["北京","Beijing"]`         | text input · normalized exact match |
| short  | (none)           | `["要点1","要点2"]`          | textarea · never auto-graded        |

Full schema in [`SCHEMA.md`](./SCHEMA.md).

---

## Themes

| theme         | feel                                            |
|---------------|-------------------------------------------------|
| `fluent`      | Microsoft Fluent UI 2 — acrylic, blue accent    |
| `sketch`      | hand-drawn paper sketch — mode 1 only           |
| `material`    | Material 3 / Material You dynamic colors        |
| `neumorphism` | soft UI, single-color base, shadow depth        |
| `terminal`    | retro CRT phosphor (green / amber toggle)       |
| `paper`       | real exam paper layout, print-friendly           |

Want a 7th? Copy any `templates/<name>.html`, hack the CSS, drop it back. The
build script picks new templates up by stem name.

---

## Customizing

- **Regex / markers**: copy `config/patterns.yaml` to
  `~/.quiz-gen/patterns.yaml` (global) or `./.quiz-gen/patterns.yaml` (project)
  and override any block. Loader deep-merges your overrides on top.
- **i18n**: drop a new file in `lang/<locale>.json` mirroring the existing
  keys, then `--lang <locale>` at build time.
- **Scoring + test composition**: every type has its own score and target
  count flag — see `SCHEMA.md`.
- **Cloud sync**: enable with `--cloud-sync`. Generated HTML shows an
  Export / Import / Gist Sync toolbar; user supplies their own GitHub PAT.

---

## Tests

```bash
pip install pytest
cd quiz-gen/

pytest tests/ -v                              # 77 cases on 10 fixtures
python scripts/update.py --self-test          # end-to-end on each fixture
python scripts/update.py --validate-config    # patterns + lang + templates sanity
```

---

## Repo layout

```
quiz-gen/
├── SKILL.md / SCHEMA.md / CHANGELOG.md / VERSION
├── config/patterns.yaml
├── lang/{zh-CN, en-US, ja-JP}.json
├── pwa/{manifest.json, service-worker.js}
├── scripts/
│   ├── common.py                # shared helpers (yaml, hashing, last-config)
│   ├── parse_questions.py       # docx/pdf/txt/md → JSON
│   ├── parse_xlsx.py            # xlsx/csv → JSON
│   ├── merge.py / dedupe.py     # combine multiple sources
│   ├── preview.py               # render first N questions to HTML
│   ├── build_html.py            # JSON → HTML + build.json
│   ├── export.py                # Anki / Quizlet / PDF / Word
│   ├── last_config.py           # ~/.quiz-gen/last.json helper
│   └── update.py                # --check / --self-test / --validate-config
├── templates/
│   └── fluent / sketch / material / neumorphism / terminal / paper .html
└── tests/
    ├── conftest.py / test_parse.py / README.md
    └── fixtures/                # 10 small original fixtures
```

---

## Contributing

Issues and pull requests welcome. Common touch points:

- New input adapter → `scripts/parse_<format>.py` + add fixture in `tests/fixtures/`
- New theme → `templates/<name>.html` using placeholder tokens from `SCHEMA.md`
- New language → `lang/<locale>.json` mirroring the existing keys
- New question type → coordinate through `SCHEMA.md`; affects parser, builder, all six templates, and exporter

Keep `SCHEMA.md` and `tests/fixtures/` truth-aligned.

---

## License

MIT © 2026 [dentar142](https://github.com/dentar142). See [LICENSE](./LICENSE).
