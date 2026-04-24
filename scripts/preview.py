# -*- coding: utf-8 -*-
"""preview.py — Generate a _preview.html for visual confirmation of parsed questions.

Layout: simple, neutral, mobile-friendly. Shows chapter, type badge, question,
options, answer (highlighted), explanation if any.

Usage:
    python preview.py --data questions.json --output _preview.html [--limit 10] [--open]
"""
import argparse, json, sys, os, html
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_version

TYPE_LABELS = {
    "single": "单选",
    "multi":  "多选",
    "tf":     "判断",
    "fill":   "填空",
    "short":  "简答",
}

TYPE_COLORS = {
    "single": "#2563eb",
    "multi":  "#7c3aed",
    "tf":     "#059669",
    "fill":   "#d97706",
    "short":  "#dc2626",
}


def load_data(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"ERROR: data file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: invalid JSON: {e}")


def render_question(q: dict, idx: int) -> str:
    qtype = q.get("type", "single")
    chapter = html.escape(q.get("chapter", ""))
    question_text = html.escape(q.get("question", ""))
    options: dict = q.get("options", {})
    answer = q.get("answer", "")
    explanation = q.get("explanation", "")
    qid = q.get("id", idx + 1)

    badge_color = TYPE_COLORS.get(qtype, "#6b7280")
    badge_label = TYPE_LABELS.get(qtype, qtype)

    # Determine correct letters
    if isinstance(answer, list):
        correct_set: set[str] = set()
    else:
        correct_set = set(answer.upper())

    # Build options HTML
    options_html = ""
    if options:
        for letter, text in sorted(options.items()):
            is_correct = letter in correct_set
            bg = "#d1fae5" if is_correct else "#f9fafb"
            border = "#059669" if is_correct else "#e5e7eb"
            tick = " ✓" if is_correct else ""
            options_html += (
                f'<div style="padding:6px 10px;margin:4px 0;border-radius:6px;'
                f'background:{bg};border:1px solid {border};font-size:0.95em;">'
                f'<strong>{html.escape(letter)}.</strong> {html.escape(text)}'
                f'<span style="color:#059669;font-weight:bold;">{tick}</span></div>'
            )

    # Answer display
    if isinstance(answer, list):
        answer_display = "、".join(html.escape(a) for a in answer)
    else:
        answer_display = html.escape(str(answer))

    # Explanation
    expl_html = ""
    if explanation and explanation.strip():
        expl_html = (
            f'<div style="margin-top:10px;padding:8px 12px;background:#fffbeb;'
            f'border-left:3px solid #f59e0b;border-radius:4px;font-size:0.9em;color:#78350f;">'
            f'<strong>解析：</strong>{html.escape(explanation)}</div>'
        )

    return f"""
<div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px 20px;margin-bottom:20px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="font-size:0.8em;font-weight:600;color:{badge_color};background:{badge_color}18;
                 padding:2px 8px;border-radius:12px;border:1px solid {badge_color}44;">
      {badge_label}
    </span>
    <span style="font-size:0.8em;color:#6b7280;">#{qid}</span>
    <span style="font-size:0.8em;color:#9ca3af;">{chapter}</span>
  </div>
  <div style="font-size:1em;font-weight:500;color:#111827;line-height:1.6;margin-bottom:12px;">
    {question_text}
  </div>
  {options_html}
  <div style="margin-top:10px;font-size:0.88em;color:#374151;">
    <strong>答案：</strong><span style="color:#059669;font-weight:600;">{answer_display}</span>
  </div>
  {expl_html}
</div>"""


def build_html(data: dict, limit: int) -> str:
    questions = data.get("questions", [])[:limit]
    total_in_file = len(data.get("questions", []))
    sources = data.get("sources", [])
    source_paths = ", ".join(s.get("path", "") for s in sources) or "unknown"
    version = data.get("version", get_version())

    cards_html = "\n".join(render_question(q, i) for i, q in enumerate(questions))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>quiz-gen Preview</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: #f3f4f6;
      color: #111827;
      margin: 0;
      padding: 16px;
    }}
    .container {{
      max-width: 760px;
      margin: 0 auto;
    }}
    header {{
      background: #fff;
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 20px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      border-left: 4px solid #2563eb;
    }}
    header h1 {{
      margin: 0 0 4px 0;
      font-size: 1.25em;
      color: #1e3a8a;
    }}
    header p {{
      margin: 0;
      font-size: 0.85em;
      color: #6b7280;
    }}
    .footer {{
      text-align: center;
      font-size: 0.8em;
      color: #9ca3af;
      padding: 16px 0;
    }}
    @media (max-width: 600px) {{
      body {{ padding: 8px; }}
    }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>quiz-gen Preview</h1>
    <p>Showing {len(questions)} of {total_in_file} questions &nbsp;|&nbsp;
       Source: {html.escape(source_paths)} &nbsp;|&nbsp;
       Schema v{html.escape(version)}</p>
  </header>
  {cards_html}
  <div class="footer">quiz-gen v{html.escape(get_version())} — preview only, not the final quiz</div>
</div>
</body>
</html>"""


def open_browser(path: str) -> None:
    import platform
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        print(f"Warning: could not open browser: {e}")


def main():
    ap = argparse.ArgumentParser(description="Generate a preview HTML for a questions.json file.")
    ap.add_argument("--data", required=True, metavar="FILE",
                    help="Input questions.json")
    ap.add_argument("--output", required=True, metavar="FILE",
                    help="Output HTML file path")
    ap.add_argument("--limit", type=int, default=10, metavar="N",
                    help="Number of questions to preview (default: 10)")
    ap.add_argument("--open", action="store_true",
                    help="Open the generated HTML in the default browser")
    args = ap.parse_args()

    data = load_data(args.data)
    html_content = build_html(data, args.limit)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    total = len(data.get("questions", []))
    shown = min(args.limit, total)
    print(f"Preview: {shown} of {total} questions → {out_path}")

    if args.open:
        open_browser(str(out_path.resolve()))


if __name__ == "__main__":
    main()
