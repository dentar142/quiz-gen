# quiz-gen v2 Data Contract (locked)

All scripts (parsers, builders, exporters, templates) MUST conform to this schema.
Changes to this file are breaking and require a major-version bump.

## questions.json

```jsonc
{
  "version": "2.0.0",                      // schema version
  "generator": "quiz-gen",
  "created_at": "2026-04-24T11:00:00Z",
  "sources": [                             // for merge / traceability
    {"id": "s1", "path": "abs/path/to/file.docx", "sha256": "..."}
  ],
  "chapters": ["导论", "第一章 …", ...],
  "questions": [
    {
      "id": 1,                             // 1-based, unique within file
      "source_id": "s1",                   // back-reference into sources[]
      "chapter": "第一章 …",
      "type": "single",                    // single|multi|tf|fill|short
      "question": "题目文本（含 LaTeX $x^2$ 与 ![](images/q1.png) 语法）",
      "options": {                         // empty for fill/short
        "A": "选项 A 文本",
        "B": "选项 B 文本",
        "C": "...",
        "D": "...",
        "E": "...",                        // optional
        "F": "..."                         // optional
      },
      "answer": "C",                       // single: "A"; multi: "ABC"; tf: "A"|"B"; fill/short: array of strings
      "explanation": "解析文本（可空）",
      "images": [                          // extracted/embedded images, optional
        {"id": "img1", "data_url": "data:image/png;base64,..."}
      ],
      "qhash": "sha1-of-normalized-question"
    }
  ]
}
```

### Type-specific notes

| type   | options        | answer format                             |
|--------|----------------|-------------------------------------------|
| single | A–F            | one letter, e.g. `"C"`                    |
| multi  | A–F            | concatenated letters, e.g. `"ABC"`        |
| tf     | A=对/B=错       | `"A"` or `"B"`                            |
| fill   | (empty)        | array of acceptable strings, e.g. `["北京","Beijing"]` |
| short  | (empty)        | array (suggested keywords); never auto-judged |

For `fill`, answer comparison is exact-match against any element after normalize
(strip + lowercase + collapse whitespace).
For `short`, the HTML never auto-grades; it always shows the model answer.

## build.json

Emitted alongside every built HTML.

```jsonc
{
  "version": "2.0.0",
  "built_at": "2026-04-24T11:30:00Z",
  "template": "fluent",                    // fluent|sketch|material|neumorphism|terminal|paper
  "lang": "zh-CN",
  "modes": [1, 2, 3],
  "scoring": {"single": 5, "multi": 3, "tf": 2, "fill": 4, "short": 6},
  "test_config": {"single": 20, "multi": 10, "tf": 0, "fill": 0, "short": 0, "chapters": null},
  "features": {
    "dark_mode": true,
    "pwa": false,
    "cloud_sync": false,
    "notes": true,
    "wrong_practice": true,
    "latex": false
  },
  "data": {
    "questions": 270,
    "chapters": 18,
    "sha256": "...",
    "source_files": ["..."]
  },
  "output_size_bytes": 130809
}
```

## patterns.yaml

Lives in `config/patterns.yaml`. Loader merges:
1. Skill default at `config/patterns.yaml`
2. User project override at `./.quiz-gen/patterns.yaml`
3. User global override at `~/.quiz-gen/patterns.yaml`

## CLI flags (parser + builder)

Common:
- `--strict` — exit 1 on dropped or empty-option questions
- `--lenient` (default) — only warn
- `--yes` — replay last config from `~/.quiz-gen/last.json`
- `--source-id <id>` — tag for the sources[] entry (default: `s1`)

Builder extra:
- `--theme {fluent|sketch|material|neumorphism|terminal|paper}`
- `--lang {zh-CN|en-US|ja-JP}`
- `--modes 1,2,3`
- `--single-score N` `--multi-score N` `--tf-score N` `--fill-score N` `--short-score N`
- `--test-single N` `--test-multi M` `--test-tf K` `--test-fill J` `--test-short L`
- `--test-chapters "ch1,ch2"`
- `--no-dark` — dark-mode default off
- `--pwa` — embed manifest + service worker
- `--cloud-sync` — show cloud-sync UI
- `--no-notes` — hide per-question notes
- `--no-wrong-practice` — disable Mode 3 → Mode 1 wrong-list seeding

Exporter:
- `--format {anki|quizlet|pdf|docx}` `--output <file>`
