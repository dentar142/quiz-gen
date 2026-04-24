# -*- coding: utf-8 -*-
"""pytest suite for quiz-gen parsers.

Covers:
- question counts per fixture
- type detection
- answer normalization (single, multi, tf, fill, short)
- ①②③④ alias markers mapping to A/B/C/D
- English Answer: / Correct Answer: patterns
- explanation capture
- CSV == XLSX output equivalence (modulo metadata)
- multi-acceptable fill answers parsed to a list
"""
import sys
from pathlib import Path

import pytest

# conftest.py provides the parse() helper and sets sys.path
from conftest import parse, FIXTURES_DIR


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def questions(fixture_name: str):
    return parse(fixture_name)["questions"]


def dropped(fixture_name: str):
    return parse(fixture_name)["dropped"]


# ---------------------------------------------------------------------------
# 1. Question counts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture,expected_count", [
    ("basic_single.txt", 5),
    ("basic_multi.txt", 4),
    ("mixed_tf.md", 3),
    ("fill_blank.txt", 3),
    ("short_answer.txt", 2),
    ("chinese_markers.txt", 3),
    ("english_format.txt", 5),
    ("with_explanation.txt", 3),
    ("bank.csv", 5),
    ("bank.xlsx", 5),
])
def test_question_count(fixture, expected_count):
    """Each fixture parses to the expected number of questions."""
    qs = questions(fixture)
    assert len(qs) == expected_count, (
        f"{fixture}: expected {expected_count} questions, got {len(qs)}"
    )


@pytest.mark.parametrize("fixture", [
    "basic_single.txt", "basic_multi.txt", "mixed_tf.md",
    "fill_blank.txt", "short_answer.txt", "chinese_markers.txt",
    "english_format.txt", "with_explanation.txt",
])
def test_no_dropped_questions(fixture):
    """Text/md fixtures must not drop any questions."""
    d = dropped(fixture)
    assert d == [], f"{fixture}: {len(d)} question(s) dropped: {d}"


# ---------------------------------------------------------------------------
# 2. Type detection
# ---------------------------------------------------------------------------

def test_basic_single_all_single_type():
    """basic_single.txt: all questions detected as type 'single'."""
    for q in questions("basic_single.txt"):
        assert q["type"] == "single", f"id={q['id']} type={q['type']!r}"


def test_basic_multi_all_multi_type():
    """basic_multi.txt: all questions detected as type 'multi'."""
    for q in questions("basic_multi.txt"):
        assert q["type"] == "multi", f"id={q['id']} type={q['type']!r}"


def test_mixed_tf_all_tf_type():
    """mixed_tf.md: all questions detected as type 'tf'."""
    for q in questions("mixed_tf.md"):
        assert q["type"] == "tf", f"id={q['id']} type={q['type']!r}"


def test_fill_blank_all_fill_type():
    """fill_blank.txt: all questions detected as type 'fill'."""
    for q in questions("fill_blank.txt"):
        assert q["type"] == "fill", f"id={q['id']} type={q['type']!r}"


def test_short_answer_all_short_type():
    """short_answer.txt: all questions detected as type 'short'."""
    for q in questions("short_answer.txt"):
        assert q["type"] == "short", f"id={q['id']} type={q['type']!r}"


def test_bank_csv_type_mix():
    """bank.csv: contains single, multi, tf, and fill types."""
    types = {q["type"] for q in questions("bank.csv")}
    assert "single" in types
    assert "multi" in types
    assert "tf" in types
    assert "fill" in types


# ---------------------------------------------------------------------------
# 3. Answer normalization — single choice
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qid,expected_answer", [
    (1, "B"),  # 1+1=2
    (2, "D"),  # largest ocean = Pacific
    (3, "C"),  # days in a week = 7
    (4, "C"),  # capital of China = Beijing
    (5, "B"),  # nearest celestial body = Moon
])
def test_basic_single_answers(qid, expected_answer):
    """basic_single.txt: answer letters are correctly normalized."""
    qs = {q["id"]: q for q in questions("basic_single.txt")}
    assert qs[qid]["answer"] == expected_answer


# ---------------------------------------------------------------------------
# 4. Answer normalization — multi choice
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qid,expected_answer", [
    (1, "ABD"),  # Asian countries
    (2, "ACE"),  # even numbers: 2,4,8
    (3, "BC"),   # liquids
    (4, "ABD"),  # South American countries
])
def test_basic_multi_answers(qid, expected_answer):
    """basic_multi.txt: multi-letter answers are concatenated correctly."""
    qs = {q["id"]: q for q in questions("basic_multi.txt")}
    assert qs[qid]["answer"] == expected_answer


# ---------------------------------------------------------------------------
# 5. Answer normalization — true/false
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qid,expected_answer", [
    (1, "B"),  # Earth largest planet? False
    (2, "A"),  # water boils at 100°C? True
    (3, "B"),  # Africa largest continent? False
])
def test_mixed_tf_answers(qid, expected_answer):
    """mixed_tf.md: 对 maps to A, 错 maps to B."""
    qs = {q["id"]: q for q in questions("mixed_tf.md")}
    assert qs[qid]["answer"] == expected_answer, (
        f"id={qid}: expected {expected_answer!r}, got {qs[qid]['answer']!r}"
    )


def test_tf_options_are_a_and_b():
    """tf questions always have options A=对 and B=错."""
    for q in questions("mixed_tf.md"):
        assert set(q["options"].keys()) == {"A", "B"}, (
            f"id={q['id']} options={q['options']}"
        )


# ---------------------------------------------------------------------------
# 6. Answer normalization — fill / short (array)
# ---------------------------------------------------------------------------

def test_fill_blank_returns_list():
    """fill_blank.txt: all fill answers are lists."""
    for q in questions("fill_blank.txt"):
        assert isinstance(q["answer"], list), (
            f"id={q['id']}: expected list, got {type(q['answer'])}"
        )


def test_fill_blank_single_acceptable_answer():
    """fill_blank.txt Q1: single answer list ['北京']."""
    q = questions("fill_blank.txt")[0]
    assert q["answer"] == ["北京"], f"got {q['answer']!r}"


def test_fill_blank_numeric_answer():
    """fill_blank.txt Q2: numeric answer ['12']."""
    q = questions("fill_blank.txt")[1]
    assert q["answer"] == ["12"], f"got {q['answer']!r}"


def test_fill_blank_multi_acceptable_answers():
    """fill_blank.txt Q3: 'H2O/水' splits to multiple acceptable answers."""
    q = questions("fill_blank.txt")[2]
    assert isinstance(q["answer"], list)
    assert len(q["answer"]) >= 2, f"expected ≥2 answers, got {q['answer']!r}"
    assert "H2O" in q["answer"]
    assert "水" in q["answer"]


def test_short_answer_returns_list():
    """short_answer.txt: short answers are lists of keyword strings."""
    for q in questions("short_answer.txt"):
        assert isinstance(q["answer"], list)
        assert len(q["answer"]) >= 1


# ---------------------------------------------------------------------------
# 7. ①②③④ markers map to A/B/C/D
# ---------------------------------------------------------------------------

def test_chinese_circle_markers_parse_three_questions():
    """chinese_markers.txt: 3 questions parsed, 0 dropped."""
    qs = questions("chinese_markers.txt")
    assert len(qs) == 3


def test_chinese_circle_marker_options_are_abcd():
    """chinese_markers.txt: ①②③④ in options line map to A/B/C/D."""
    for q in questions("chinese_markers.txt"):
        assert set(q["options"].keys()) == {"A", "B", "C", "D"}, (
            f"id={q['id']} options keys={set(q['options'].keys())}"
        )


@pytest.mark.parametrize("qid,expected_answer", [
    (1, "A"),  # 答案：① → A
    (2, "B"),  # 答案：② → B
    (3, "C"),  # 答案：③ → C
])
def test_chinese_circle_marker_answers(qid, expected_answer):
    """chinese_markers.txt: ①②③ in answer line resolve to A/B/C."""
    qs = {q["id"]: q for q in questions("chinese_markers.txt")}
    assert qs[qid]["answer"] == expected_answer


# ---------------------------------------------------------------------------
# 8. English Answer: and Correct Answer: patterns
# ---------------------------------------------------------------------------

def test_english_format_question_count():
    """english_format.txt: 5 questions parsed."""
    assert len(questions("english_format.txt")) == 5


@pytest.mark.parametrize("qid,expected_answer", [
    (1, "B"),   # Answer: B
    (2, "B"),   # Correct Answer: B
    (3, "C"),   # Answer: C
    (4, "B"),   # Answer: B
    (5, "C"),   # Correct Answer: C
])
def test_english_format_answers(qid, expected_answer):
    """english_format.txt: both 'Answer:' and 'Correct Answer:' patterns work."""
    qs = {q["id"]: q for q in questions("english_format.txt")}
    assert qs[qid]["answer"] == expected_answer


def test_english_format_all_single_type():
    """english_format.txt: all questions are type 'single'."""
    for q in questions("english_format.txt"):
        assert q["type"] == "single"


# ---------------------------------------------------------------------------
# 9. Explanation capture
# ---------------------------------------------------------------------------

def test_with_explanation_all_have_explanation():
    """with_explanation.txt: all 3 questions have non-empty explanation."""
    for q in questions("with_explanation.txt"):
        assert q.get("explanation"), (
            f"id={q['id']}: explanation is empty or missing"
        )


def test_with_explanation_content_nonempty():
    """with_explanation.txt: explanations are non-trivial strings."""
    for q in questions("with_explanation.txt"):
        expl = q.get("explanation", "")
        assert len(expl) > 5, f"id={q['id']}: explanation too short: {expl!r}"


def test_basic_single_has_no_explanations():
    """basic_single.txt: questions without 解析 lines have empty explanation."""
    for q in questions("basic_single.txt"):
        # explanation field must exist but be empty string or absent
        expl = q.get("explanation", "")
        assert expl == "", f"id={q['id']}: unexpected explanation {expl!r}"


# ---------------------------------------------------------------------------
# 10. CSV == XLSX equivalence
# ---------------------------------------------------------------------------

def test_csv_xlsx_same_question_count():
    """bank.csv and bank.xlsx produce the same number of questions."""
    assert len(questions("bank.csv")) == len(questions("bank.xlsx"))


def test_csv_xlsx_same_types():
    """bank.csv and bank.xlsx: question types are identical in order."""
    csv_types = [q["type"] for q in questions("bank.csv")]
    xlsx_types = [q["type"] for q in questions("bank.xlsx")]
    assert csv_types == xlsx_types


def test_csv_xlsx_same_answers():
    """bank.csv and bank.xlsx: answers are identical in order."""
    csv_ans = [q["answer"] for q in questions("bank.csv")]
    xlsx_ans = [q["answer"] for q in questions("bank.xlsx")]
    assert csv_ans == xlsx_ans


def test_csv_xlsx_same_explanations():
    """bank.csv and bank.xlsx: explanations are identical in order."""
    csv_expls = [q["explanation"] for q in questions("bank.csv")]
    xlsx_expls = [q["explanation"] for q in questions("bank.xlsx")]
    assert csv_expls == xlsx_expls


def test_csv_xlsx_same_qhashes():
    """bank.csv and bank.xlsx: qhash (question fingerprint) is identical."""
    csv_hashes = [q["qhash"] for q in questions("bank.csv")]
    xlsx_hashes = [q["qhash"] for q in questions("bank.xlsx")]
    assert csv_hashes == xlsx_hashes


# ---------------------------------------------------------------------------
# 11. Fill multi-answer in CSV/XLSX
# ---------------------------------------------------------------------------

def test_csv_fill_multi_answer_is_list():
    """bank.csv fill question: answer is a list with multiple values."""
    fill_qs = [q for q in questions("bank.csv") if q["type"] == "fill"]
    assert fill_qs, "no fill questions in bank.csv"
    q = fill_qs[0]
    assert isinstance(q["answer"], list)
    assert len(q["answer"]) >= 2, f"expected ≥2 acceptable answers, got {q['answer']!r}"


def test_csv_fill_contains_everest():
    """bank.csv fill answer includes the English form 'Everest'."""
    fill_qs = [q for q in questions("bank.csv") if q["type"] == "fill"]
    q = fill_qs[0]
    assert "Everest" in q["answer"], f"'Everest' not in {q['answer']!r}"


# ---------------------------------------------------------------------------
# 12. tf answer in CSV
# ---------------------------------------------------------------------------

def test_csv_tf_answer_is_a_or_b():
    """bank.csv tf question: answer is canonical 'A' or 'B'."""
    tf_qs = [q for q in questions("bank.csv") if q["type"] == "tf"]
    assert tf_qs, "no tf questions in bank.csv"
    for q in tf_qs:
        assert q["answer"] in ("A", "B"), (
            f"tf answer not canonical: {q['answer']!r}"
        )


# ---------------------------------------------------------------------------
# 13. Options structure
# ---------------------------------------------------------------------------

def test_single_choice_has_abcd_options():
    """basic_single.txt: every question has at least A,B,C,D options."""
    for q in questions("basic_single.txt"):
        for letter in "ABCD":
            assert letter in q["options"], (
                f"id={q['id']}: missing option {letter!r}"
            )


def test_fill_and_short_have_no_options():
    """fill and short questions have empty options dict."""
    for fixture in ("fill_blank.txt", "short_answer.txt"):
        for q in questions(fixture):
            assert q["options"] == {}, (
                f"{fixture} id={q['id']}: expected empty options, got {q['options']}"
            )


# ---------------------------------------------------------------------------
# 14. qhash populated
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", [
    "basic_single.txt", "basic_multi.txt", "mixed_tf.md",
    "fill_blank.txt", "short_answer.txt", "chinese_markers.txt",
    "english_format.txt", "with_explanation.txt",
    "bank.csv", "bank.xlsx",
])
def test_qhash_present_and_nonempty(fixture):
    """Every parsed question has a non-empty qhash fingerprint."""
    for q in questions(fixture):
        assert q.get("qhash"), f"{fixture} id={q['id']}: qhash missing or empty"
