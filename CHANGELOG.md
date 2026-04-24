# Changelog

## 2.0.0 — 2026-04-24

### Added
- **Inputs**: Excel (`.xlsx`), CSV (`.csv`) parsers with column auto-detection
- **Question types**: 判断 (true/false), 填空 (fill-in-blank), 简答 (short-answer); options A–F
- **Explanation field**: optional 解析/Explanation captured per question
- **Answer pattern coverage**: matches 答案/正确答案/参考答案/【答案】/Answer/Ans:
- **Marker coverage**: ①②③④, (1)(2), 甲乙丙丁, 一二三四 markers and Q numbers
- **Patterns externalized**: `config/patterns.yaml` — user-overridable
- **CLI modes**: `--strict` / `--lenient`, `--yes` for last-config replay
- **Multi-file merge**: `scripts/merge.py` merges N files (mixed formats)
- **Dedup**: `--dedup` flag warns and optionally removes duplicates
- **Image support**: extracts embedded images from `.docx` and base64-embeds; markdown `![](…)` syntax
- **LaTeX**: KaTeX rendering for `$…$` and `$$…$$`
- **Multiple themes**: Material 3, Neumorphism, Terminal, Paper (in addition to Fluent + Sketch)
- **i18n**: zh-CN / en-US / ja-JP UI strings via `--lang`
- **PWA**: manifest + service worker for "Install as app"
- **Cloud sync**: optional GitHub Gist sync of progress (client-side PAT)
- **Personal notes**: per-question textarea persisted to LocalStorage and exportable
- **Wrong-answer auto-practice**: after Mode 3, "用错题继续练习" seeds Mode 1
- **Custom test**: `--test-single N --test-multi M --test-chapters …`
- **Multi-target export**: Anki CSV, Quizlet TSV, printable PDF, Word `.docx`
- **HTML preview**: `scripts/preview.py` renders parsed questions for visual confirmation
- **Build manifest**: `build.json` per output (hashes, source files, version)
- **Self-update + self-test**: `scripts/update.py --check` / `--self-test`
- **Unit tests**: `tests/fixtures/` + `tests/test_parse.py` (pytest)

### Changed
- Parser refactor: shared core + format adapters
- Build flags: `--theme {fluent,sketch,material,neumorphism,terminal,paper}`, `--lang …`, `--pwa`, `--cloud-sync`

## 1.0.0 — 2026-04-24

Initial release: docx/pdf/txt/md → 3-mode HTML (Fluent + Sketch).
