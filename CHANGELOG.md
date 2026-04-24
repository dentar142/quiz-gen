# Changelog

## 2.0.2 — 2026-04-24

### Added
- **Number-row 1-6 → A-F option keys** in all six templates (was A-F letters
  only). Pressing `1` now picks option A, `2` picks B, etc. Letter keys still
  work; both methods coexist.
- **Cold-start view restore**: on page load, if the user was last in mode 1
  or mode 2, they're auto-resumed there (mode 3 is intentionally excluded —
  half-finished tests are brittle). Implemented via a single
  `localStorage["quiz-last-view"]` key written on every `go()` call.
  Sketch (mode-1 only) restores the last question index via `sketch-idx`
  with a bounds check so a shrunken bank doesn't crash.

### Notes
- Both behaviors are fail-soft: a `try { ... } catch {}` shell means private
  browsing / disabled-storage browsers don't break.

## 2.0.1 — 2026-04-24

### Fixed
- **Answer-line bleed**: lines like `答案A` / `答案ABC` (no separator between
  `答案` and the letters) silently fell through the previous `[\s:：\.\-]+`
  regex, causing the parser to never close that question. The buffer would
  swallow every subsequent paragraph — including the next several questions
  — into the previous question's last option, dropping those questions and
  corrupting one option's text. New strict letter-only patterns
  (`^\s*答案[\s:：\.\-]*([ABCDabcd]+)\s*$`) match before the fallback
  free-form patterns. On the reference fixture this recovered 6 previously
  dropped questions (264 → 270) and reduced suspect-option count from 5 → 0.
- **Section keyword false-match**: `单选题` / `多选题` etc. patterns were
  unanchored, so a question containing the word ("...本节单选题占多数...")
  would falsely flip the type context and reset the buffer. All section
  patterns are now anchored at line start (`^\s*[一二三四五六七]?\s*[、.]?
  \s*单选题\s*$`) so only paragraphs that are themselves headings trigger
  type changes.

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
