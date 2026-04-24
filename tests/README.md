# quiz-gen parser tests

## Setup

```
pip install pytest openpyxl
```

For docx/pdf fixtures (not needed for the current suite):
```
pip install python-docx PyMuPDF
```

## Run

```
cd C:/Users/Neko/.claude/skills/quiz-gen
pytest tests/ -v
```

## Fixtures

All fixtures live in `tests/fixtures/`. Each exercises a specific parsing edge case:

| File | Edge case |
|---|---|
| `basic_single.txt` | Classic single-choice, Chinese headings |
| `basic_multi.txt` | Multi-choice with 3–5 options |
| `mixed_tf.md` | True/false with 对/错 answer styles |
| `fill_blank.txt` | Fill-in-blank including multi-acceptable answers |
| `short_answer.txt` | Short-answer (array answer, never auto-graded) |
| `chinese_markers.txt` | ①②③④ option markers mapping to A/B/C/D |
| `english_format.txt` | English `Answer:` and `Correct Answer:` patterns |
| `with_explanation.txt` | `解析:` line captured into explanation field |
| `bank.csv` | CSV tabular format |
| `bank.xlsx` | Excel format (same data as CSV) |

## Regenerate bank.xlsx

```
python tests/fixtures/_make_xlsx.py
```

## Smoke-test regression (original docx)

```
python scripts/parse_questions.py \
    --input "C:/Users/Neko/Downloads/选择题题库.docx" \
    --output /tmp/regress.json
# Must report: Total questions: 264 or more, 0 validation issues
```
