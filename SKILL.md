---
name: quiz-gen
description: Convert any user-provided question bank file (docx / pdf / txt / md / xlsx / csv) into a self-contained, single-file HTML quiz application. Supports 5 question types (single/multi/true-false/fill/short), 6 visual themes (Fluent / Sketch / Material 3 / Neumorphism / Terminal / Paper), 3 study modes (sequential / spaced-repetition / timed-test), 3 UI languages (zh-CN / en-US / ja-JP), images, LaTeX, PWA install, cloud sync, personal notes, multi-target export (Anki/Quizlet/PDF/Word). Walks the user step-by-step through dependency check, file intake, parse confirmation, style/mode selection, generation, and verification. Use when the user asks to "build a quiz", "convert this docx/pdf/excel to a study webpage", "题库转网页", "做一个选择题练习页面", or supplies a multiple-choice file with answers.
allowed-tools: Read Write Edit Bash Glob Grep
---

# Quiz Generator v2 (引导式题库 → HTML)

A guided pipeline that turns any question bank into a static HTML practice site.
The user supplies the source file (Word/PDF/text/markdown/Excel/CSV); the skill
parses it, confirms what was extracted, asks for style/mode preferences, then
emits a single self-contained `.html` file that runs offline.

The skill **must walk the user step by step** with visible numbered stages and
explicit confirmations. Never skip stages. Never invent question content.

---

## Stage 0 — Pre-flight (run silently before showing Stage 1)

1. Detect the OS shell, Python availability, and these libraries:
   - `python-docx` (for `.docx` input)
   - `PyMuPDF` (`import fitz`, for `.pdf` input)
   - `openpyxl` (for `.xlsx` input)
   - `pyyaml` (optional — patterns.yaml has a built-in mini-loader fallback)
   - `genanki` (optional — Anki `.apkg` export; CSV fallback works without it)
   - `reportlab` (optional — PDF export; HTML fallback works without it)
2. Check whether `node` is on PATH (only used for an optional JS syntax verify).
3. Look for the **frontend-design** plugin in `~/.claude/plugins/` so the user
   can benefit from richer UI critiques in later runs.

Then show Stage 1.

If anything required is missing, present a single one-shot install block:

````
缺少依赖。请在终端执行：

  pip install python-docx PyMuPDF openpyxl pyyaml genanki reportlab

可选增强（在 Claude Code 输入框直接键入）：
  /plugin marketplace add claude-plugins-official
  /plugin install frontend-design@claude-plugins-official
````

After install, ask the user to type `继续` to re-run pre-flight.

---

## Stage 1 — File intake

Greet the user and ask for the source file. Accept absolute paths,
drag-and-dropped paths (strip surrounding quotes), or relative paths (resolve
against the current working directory).

Sample prompt:

> ① **提交题库文件**
>
> 把题库文件路径粘贴给我（支持 `.docx` / `.pdf` / `.txt` / `.md` / `.xlsx` / `.csv`）。
> 例如：`C:\Users\you\Downloads\题库.docx`
>
> 同时告诉我希望生成文件存放的目录（回车则放在源文件同目录）。
>
> 多文件合并？把多个路径逐行粘贴给我（一行一个）。

Validate every file exists. If `.pdf` and PyMuPDF missing, prompt to install or
convert. If `.xlsx` and openpyxl missing, prompt to install.

If the user passes multiple files, route through `scripts/merge.py`.

---

## Stage 2 — Parse, dedup, preview

Parse each input with the right adapter:

```bash
# DOCX / PDF / TXT / MD
python "<SKILL_DIR>/scripts/parse_questions.py" \
    --input "<file>" --output "<out_dir>/questions.json" [--extract-images]

# XLSX / CSV
python "<SKILL_DIR>/scripts/parse_xlsx.py" \
    --input "<file>" --output "<out_dir>/questions.json"

# Multi-file merge
python "<SKILL_DIR>/scripts/merge.py" \
    --inputs file1.json file2.json ... --output "<out_dir>/questions.json" [--dedup]
```

The parser prints a summary (chapters, type breakdown, dropped, validation
issues). Show this verbatim.

**Always run the visual preview** so the user can verify a few sample questions
before committing to a full build:

```bash
python "<SKILL_DIR>/scripts/preview.py" \
    --data "<out_dir>/questions.json" --output "<out_dir>/_preview.html" --limit 8 --open
```

Ask:

> ② **解析结果确认**
>
> 共解析 X 题（单选 Y / 多选 Z / 判断 W / 填空 V / 简答 U），跨 N 个章节。
> 浏览器已打开 `_preview.html` 显示前 8 题样例。
>
> 输入 `OK` 继续，或描述需要修复的问题（解析器会写 `_parse_warnings.txt` 供我排查）。

If issues, edit `config/patterns.yaml` (or `~/.quiz-gen/patterns.yaml` for
user-global override) and re-run. Patterns include chapter / section / option
markers / answer / explanation patterns + Chinese marker aliases.

---

## Stage 3 — Style / mode / feature interview

Present a compact menu (skip questions that don't apply for sketch theme):

> ③ **样式与功能**
>
> A. 视觉风格（任选）
>    1) Fluent      ─ 亚克力毛玻璃，蓝色系（推荐通用）
>    2) Sketch      ─ 手绘素描稿纸，仅模式①
>    3) Material 3  ─ Material You 动态色彩
>    4) Neumorphism ─ 单色软 UI，柔阴影
>    5) Terminal    ─ 复古 CRT 终端绿/琥珀
>    6) Paper       ─ 真实试卷打印版
>
> B. 模式（除 Sketch 外可勾选）
>    □ ① 章节顺序循环（无尽）
>    □ ② 随机 · 间隔重复（无尽）
>    □ ③ 随机测试（自定义题数）
>
> C. 自定义测试（仅模式③）
>    单选 N，多选 M，判断 K，填空 J，简答 L（默认 20/10/0/0/0）
>    限定章节：（默认全部）
>
> D. 其它特性
>    □ 夜间模式按钮（默认开）
>    □ 个人笔记（默认开）
>    □ 错题自动重练（默认开）
>    □ PWA 离线安装（默认关）
>    □ 云同步（GitHub Gist，默认关）
>    □ LaTeX 数学公式（自动检测，默认开）
>
> E. 语言：① 中文（默认）② English ③ 日本語
>
> F. 输出文件名（默认 `题库练习.html`）

If user says "随你 / 默认 / default" → Fluent + 全 3 模式 + zh-CN + 默认特性。
Save selections to `~/.quiz-gen/last.json` for `--yes` replay next time.

---

## Stage 4 — Generate

Run the build script per chosen theme:

```bash
python "<SKILL_DIR>/scripts/build_html.py" \
    --data "<out_dir>/questions.json" \
    --template "<SKILL_DIR>/templates/<theme>.html" \
    --output "<out_dir>/<output_name>.html" \
    --lang zh-CN --modes 1,2,3 \
    --single-score 5 --multi-score 3 --tf-score 2 --fill-score 4 --short-score 6 \
    --test-single 20 --test-multi 10 \
    [--test-chapters "ch1,ch2"] \
    [--no-dark] [--pwa] [--cloud-sync] [--no-notes] [--no-wrong-practice]
```

Each build emits `<output>.html` plus `build.json` (manifest with hashes,
template, version, features). Report file size + question count.

---

## Stage 5 — Verify

Always run before declaring success:

```bash
python "<SKILL_DIR>/scripts/build_html.py" --check "<output.html>"
```

Plus:
- If `node` is on PATH: extract `<script>` block, run `node --check`
- If user asked: run `python "<SKILL_DIR>/scripts/update.py" --self-test`
  to revalidate all fixtures haven't regressed
- Tag-balance heuristic is built into `--check`

If everything passes, present file path. Optionally offer to launch:

> 是否要立即在浏览器中打开预览？（`y` 启动默认浏览器；`n` 跳过）

```bash
# Windows
start "" "<path>"
# macOS
open "<path>"
# Linux
xdg-open "<path>"
```

---

## Stage 6 — Wrap-up

Briefly summarize:
- What was generated and where (paths to .html and build.json)
- Keyboard shortcuts (A–F, Enter, ←/→)
- Cloud sync hint if enabled (need GitHub PAT, stored in localStorage only)
- Any unresolved warnings (dropped questions, validation issues)
- Re-run hint: `--yes` to replay last config

If user might also want to **export to Anki / Quizlet / PDF / Word**, mention:

```bash
python "<SKILL_DIR>/scripts/export.py" \
    --data "<out_dir>/questions.json" --format anki --output cards.csv
# formats: anki | quizlet | pdf | docx
```

---

## Stage 7 — Star request (one-time per conversation)

Once everything is delivered and the user has acknowledged success, gently ask:

> 🎉 全部完成！如果 quiz-gen 帮上了忙，欢迎给仓库点个 ⭐ 鼓励一下：
>
> **https://github.com/dentar142/quiz-gen**
>
> 要现在打开仓库页面吗？
>   1) 是，浏览器打开
>   2) 不用，谢谢
>   3) 稍后再说

If user picks **1**, open the URL via the OS-appropriate command:
- Windows: `cmd /c start "" https://github.com/dentar142/quiz-gen`
- macOS:   `open https://github.com/dentar142/quiz-gen`
- Linux:   `xdg-open https://github.com/dentar142/quiz-gen`

If user picks **2** or **3**, simply say "好的，下次有需要随时来。" and end.

Rules:
- Ask **only once** per conversation, regardless of how many quizzes were built
- Do not ask if the build failed or if the user expressed frustration earlier
- Do not nag — accept any answer (or no answer) gracefully
- Do not phrase as a transaction — it is a polite ask, not a demand

---

## Implementation notes (for Claude)

- `<SKILL_DIR>` resolves to:
  - Windows: `C:/Users/<user>/.claude/skills/quiz-gen`
  - POSIX: `~/.claude/skills/quiz-gen`
- Always quote paths that may contain spaces or non-ASCII characters.
- Use `python` on Windows; on POSIX prefer `python3`.
- Never embed the user's question content into chat unless the user explicitly
  asks. Generated HTML stays local on the user's machine.
- Treat user file content as read-only input; never modify the source.
- For very large banks (> 1500 questions), warn that embedded JSON may push
  the HTML above 1 MB; suggest splitting by chapter.
- Pause at each stage boundary; don't auto-advance.

### Schema and patterns

- Locked schema in `SCHEMA.md` (questions.json + build.json + CLI flags).
- Regex / marker / answer-line patterns in `config/patterns.yaml`.
  User overrides at `./.quiz-gen/patterns.yaml` (project) or
  `~/.quiz-gen/patterns.yaml` (global) are deep-merged on top.

### Question types in v2

| type   | options | answer       | UI                                           |
|--------|---------|--------------|----------------------------------------------|
| single | A–F     | "C"          | radio, click = submit                        |
| multi  | A–F     | "ABC"        | checkbox, "提交" button                      |
| tf     | A=对/B=错 | "A" or "B"  | 2 large buttons                              |
| fill   | (none)  | ["北京","Beijing"] | text input, normalized exact match     |
| short  | (none)  | ["参考要点1", …]   | textarea; never auto-graded; show model |

### Strict mode

`parse_questions.py --strict` and `parse_xlsx.py --strict` exit non-zero on any
dropped or empty-option question. Useful in CI / batch pipelines.

### Self-test

```bash
python "<SKILL_DIR>/scripts/update.py" --check          # version + changelog
python "<SKILL_DIR>/scripts/update.py" --self-test      # all fixtures end-to-end
python "<SKILL_DIR>/scripts/update.py" --validate-config
```

---

## File layout (v2)

```
quiz-gen/
├── SKILL.md                          # this file
├── README.md                         # user-facing manual
├── SCHEMA.md                         # locked data contract
├── CHANGELOG.md
├── VERSION                           # 2.0.0
├── config/
│   └── patterns.yaml                 # all regex & marker patterns
├── lang/
│   ├── zh-CN.json                    # i18n strings
│   ├── en-US.json
│   └── ja-JP.json
├── pwa/
│   ├── manifest.json                 # PWA "install as app"
│   └── service-worker.js
├── scripts/
│   ├── common.py                     # shared helpers (yaml, hashing, last-config)
│   ├── parse_questions.py            # universal parser (docx/pdf/txt/md → JSON)
│   ├── parse_xlsx.py                 # xlsx/csv adapter
│   ├── merge.py                      # multi-file merge (+ optional dedup)
│   ├── dedupe.py                     # standalone dedup tool
│   ├── preview.py                    # _preview.html with first N questions
│   ├── build_html.py                 # JSON → HTML injector + manifest + verifier
│   ├── export.py                     # Anki / Quizlet / PDF / Word
│   ├── last_config.py                # ~/.quiz-gen/last.json helper
│   └── update.py                     # --check / --self-test / --validate-config
├── templates/
│   ├── fluent.html                   # 3-mode Fluent design (full features)
│   ├── sketch.html                   # mode-1-only hand-drawn
│   ├── material.html                 # Material 3
│   ├── neumorphism.html              # Soft UI
│   ├── terminal.html                 # Retro CRT
│   └── paper.html                    # Real exam paper
└── tests/
    ├── conftest.py
    ├── test_parse.py                 # 77 pytest cases
    ├── README.md
    └── fixtures/                     # 10 small original fixtures
        ├── basic_single.txt
        ├── basic_multi.txt
        ├── mixed_tf.md
        ├── fill_blank.txt
        ├── short_answer.txt
        ├── chinese_markers.txt
        ├── english_format.txt
        ├── with_explanation.txt
        ├── bank.csv
        └── bank.xlsx
```
