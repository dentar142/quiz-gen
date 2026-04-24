# -*- coding: utf-8 -*-
"""pytest configuration: path setup and shared parse() helper."""
import json
import subprocess
import sys
from pathlib import Path

# Make the scripts package importable from any working directory
SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))


def parse_txt(fixture_name: str) -> dict:
    """Parse a .txt or .md fixture via parse_questions directly and return the
    questions.json payload as a dict."""
    from common import load_patterns
    from parse_questions import compile_patterns, iter_text, parse_stream, get_version, utc_now_iso, file_sha256

    path = FIXTURES_DIR / fixture_name
    P = load_patterns()
    CP = compile_patterns(P)
    chapters, questions, dropped = parse_stream(iter_text(str(path)), CP)
    return {
        "version": get_version(),
        "chapters": chapters,
        "questions": questions,
        "dropped": dropped,
    }


def parse_tabular(fixture_name: str) -> dict:
    """Parse a .csv or .xlsx fixture via parse_xlsx internals and return a
    questions.json-shaped dict."""
    from parse_xlsx import (
        iter_rows, normalize_answer, normalize_type,
        find_col, normalize_header, HEADER_ALIASES, OPT_ALIASES,
    )
    from common import question_hash, get_version, utc_now_iso

    path = FIXTURES_DIR / fixture_name
    headers, body = next(iter_rows(str(path)))
    h_lower = [normalize_header(h) for h in headers]
    cols = {k: find_col(h_lower, v) for k, v in HEADER_ALIASES.items()}
    opt_cols = {L: find_col(h_lower, OPT_ALIASES[L]) for L in "ABCDEF"}

    chapters_seen = []
    questions = []
    for row in body:
        def cell(idx, r=row):
            return r[idx] if 0 <= idx < len(r) else None

        chap = str(cell(cols["chapter"]) or "未分类").strip()
        if chap not in chapters_seen:
            chapters_seen.append(chap)
        qtype = normalize_type(cell(cols["type"]))
        question_text = str(cell(cols["question"]) or "").strip()
        if not question_text:
            continue
        options = {}
        for L in "ABCDEF":
            v = cell(opt_cols[L])
            if v is not None and str(v).strip():
                options[L] = str(v).strip()
        if qtype == "tf" and not options:
            options = {"A": "对", "B": "错"}
        ans = normalize_answer(cell(cols["answer"]), qtype)
        expl = ""
        if cols["explanation"] >= 0:
            expl = str(cell(cols["explanation"]) or "").strip()
        q = {
            "id": len(questions) + 1,
            "source_id": "s1",
            "chapter": chap,
            "type": qtype,
            "question": question_text,
            "options": options,
            "answer": ans,
            "explanation": expl,
        }
        q["qhash"] = question_hash(q)
        questions.append(q)

    return {
        "version": get_version(),
        "chapters": chapters_seen,
        "questions": questions,
        "dropped": [],
    }


def parse(fixture_name: str) -> dict:
    """Return parsed dict for any fixture file by name."""
    ext = Path(fixture_name).suffix.lower()
    if ext in (".csv", ".xlsx", ".xls"):
        return parse_tabular(fixture_name)
    return parse_txt(fixture_name)
