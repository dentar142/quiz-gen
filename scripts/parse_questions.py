# -*- coding: utf-8 -*-
"""quiz-gen v2 universal question-bank parser.

Inputs:  .docx | .pdf | .txt | .md   (xlsx/csv handled by parse_xlsx.py)
Output:  questions.json conforming to SCHEMA.md v2

Question types: single | multi | tf | fill | short
Options:        A–F (E/F optional)
"""
import argparse, json, os, re, sys, io, base64
from pathlib import Path

# Make our own package importable when invoked via `python script.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    load_patterns, normalize_text, question_hash, file_sha256,
    utc_now_iso, get_version, load_last_config, save_last_config,
)


# =====================================================================
# Pattern compilation (driven by config/patterns.yaml)
# =====================================================================
def compile_patterns(P: dict) -> dict:
    """Convert YAML patterns into compiled regexes / lookups."""
    sec = P.get("section", {})
    chap = P.get("chapter", {})
    qn = P.get("question_number", {})
    opts = P.get("options", {})
    ans = P.get("answer", {})
    expl = P.get("explanation", {})
    tf_ans = P.get("tf_answers", {})
    ig = P.get("ignore", {})

    def comp_list(lst):
        out = []
        for p in lst or []:
            try:
                out.append(re.compile(p))
            except re.error:
                pass
        return out

    # Build alias lookup: any alias string → canonical letter
    alias_map = {}
    for letter in opts.get("letters", ["A", "B", "C", "D", "E", "F"]):
        for alias in opts.get("aliases", {}).get(letter, [letter]):
            alias_map[alias] = letter
    # Sort aliases by length DESC so "（1）" wins over "1"
    sorted_aliases = sorted(alias_map.keys(), key=len, reverse=True)
    seps = opts.get("separators", [".", "．", "、", ":", "：", " ", "　"])
    sep_chars = "".join(re.escape(c) for c in seps if c)

    return {
        "chapter": comp_list(chap.get("text_patterns")),
        "single": comp_list(sec.get("single_patterns")),
        "multi": comp_list(sec.get("multi_patterns")),
        "tf": comp_list(sec.get("tf_patterns")),
        "fill": comp_list(sec.get("fill_patterns")),
        "short": comp_list(sec.get("short_patterns")),
        "qnum": comp_list(qn.get("patterns")),
        "answer": comp_list(ans.get("patterns")),
        "explanation": comp_list(expl.get("patterns")),
        "letters": opts.get("letters", ["A", "B", "C", "D", "E", "F"]),
        "alias_map": alias_map,
        "sorted_aliases": sorted_aliases,
        "sep_chars": sep_chars,
        "tf_a": [s for s in tf_ans.get("A", [])],
        "tf_b": [s for s in tf_ans.get("B", [])],
        "ignore_prefixes": ig.get("prefixes", []),
    }


# =====================================================================
# Marker detection on a single line
# =====================================================================
def find_letter_markers(text: str, CP: dict):
    """Return list of (pos, canonical_letter) sorted by pos for any of the
    aliased option markers in `text`. A marker must be followed by a
    separator OR a CJK char; and not be embedded inside an English word."""
    out = []
    seps = CP["sep_chars"]
    for alias in CP["sorted_aliases"]:
        # Don't tokenize multi-letter aliases inside words; for single letters,
        # require word-boundary-ish on the left.
        for m in re.finditer(re.escape(alias), text):
            start = m.start()
            end = m.end()
            # left guard: previous char must not be a Latin/Chinese letter OR digit
            if start > 0:
                prev = text[start - 1]
                if prev.isalnum() and len(alias) == 1 and alias.isalpha():
                    continue
            # right guard: must be followed by separator or CJK
            after = text[end:end + 1]
            if after:
                if not (after in seps or "一" <= after <= "鿿"
                        or after in "“”\"'（([【"):
                    continue
            out.append((start, CP["alias_map"][alias]))
    # Dedup overlapping markers — keep leftmost / longest
    out.sort()
    cleaned = []
    last_end = -1
    for pos, letter in out:
        if pos < last_end:
            continue
        cleaned.append((pos, letter))
        last_end = pos + 1
    return cleaned


def split_by_markers(text: str, markers, CP: dict):
    """Given line text and list of (pos, letter), return {letter: content}."""
    out = {}
    for i, (start, letter) in enumerate(markers):
        # skip past separators after the marker character
        after = start + 1
        while after < len(text) and (text[after] in CP["sep_chars"]):
            after += 1
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        out[letter] = text[after:end].strip()
    return out


# =====================================================================
# Buffer → question
# =====================================================================
def parse_buffer(lines, ctype, CP):
    """Convert buffered question paragraphs into {question, options}.
    Return None on parse failure (no recognizable options for typed Qs)."""
    if not lines:
        return None
    if ctype in ("fill", "short"):
        # No options; everything is the question text
        return {"question": " ".join(lines).strip(), "options": {}}
    if ctype == "tf":
        # T/F questions usually have NO option markers — just the prompt.
        return {
            "question": " ".join(lines).strip(),
            "options": {"A": "对", "B": "错"},
        }

    # single / multi: locate first option line
    first_opt = None
    for i, ln in enumerate(lines):
        markers = find_letter_markers(ln, CP)
        if markers and markers[0][1] == "A":
            first_opt = i
            break
    if first_opt is None:
        # 5-line fallback
        if len(lines) == 5:
            return {
                "question": lines[0].strip(),
                "options": dict(zip("ABCD", [l.strip() for l in lines[1:5]])),
            }
        return None

    q_text = " ".join(lines[:first_opt]).strip()
    options = {L: "" for L in CP["letters"]}
    cur = None
    for ln in lines[first_opt:]:
        markers = find_letter_markers(ln, CP)
        # Only accept markers in monotonically increasing letter order
        next_idx = (CP["letters"].index(cur) + 1) if cur else 0
        seq = []
        for pos, letter in markers:
            if next_idx < len(CP["letters"]) and letter == CP["letters"][next_idx]:
                seq.append((pos, letter))
                next_idx += 1
        if len(seq) >= 2:
            split = split_by_markers(ln, seq, CP)
            for L, content in split.items():
                options[L] = (options[L] + " " + content).strip()
                cur = L
        elif len(seq) == 1:
            (pos, letter), = seq
            split = split_by_markers(ln, [(pos, letter)], CP)
            options[letter] = (options[letter] + " " + split[letter]).strip()
            cur = letter
        elif cur is not None:
            # continuation of previous option
            options[cur] = (options[cur] + " " + ln.strip()).strip()
    # Drop empty trailing letters (E/F may legitimately be empty)
    options = {L: v for L, v in options.items() if v}
    return {"question": q_text, "options": options}


# =====================================================================
# Source-format adapters
# =====================================================================
def iter_docx(path: str, image_out_dir=None):
    try:
        import docx
    except ImportError:
        sys.exit("ERROR: pip install python-docx")
    doc = docx.Document(path)
    img_idx = [0]

    def maybe_extract_images(p):
        if image_out_dir is None:
            return []
        out = []
        for run in p.runs:
            for blip in run.element.findall(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
            ):
                rid = blip.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                )
                if not rid:
                    continue
                try:
                    image = doc.part.related_parts[rid]
                    img_idx[0] += 1
                    name = f"img{img_idx[0]}{Path(image.partname).suffix or '.png'}"
                    Path(image_out_dir).mkdir(parents=True, exist_ok=True)
                    target = Path(image_out_dir) / name
                    target.write_bytes(image.blob)
                    out.append(str(target))
                except Exception:
                    pass
        return out

    for p in doc.paragraphs:
        text = p.text.strip()
        imgs = maybe_extract_images(p)
        style = p.style.name if p.style else "Normal"
        if not text and not imgs:
            continue
        yield text, style, imgs


def iter_pdf(path: str):
    try:
        import fitz
    except ImportError:
        sys.exit("ERROR: pip install PyMuPDF")
    doc = fitz.open(path)
    for page in doc:
        for line in page.get_text("text").splitlines():
            txt = line.strip()
            if not txt:
                continue
            yield txt, "Normal", []
    doc.close()


def iter_text(path: str):
    encoding = "utf-8"
    try:
        with open(path, encoding="utf-8") as f:
            f.read()
    except UnicodeDecodeError:
        encoding = "gbk"
    with open(path, encoding=encoding) as f:
        for line in f:
            txt = line.rstrip("\n").strip()
            if not txt:
                continue
            style = "Normal"
            if txt.startswith("# "):
                style = "Heading 1"; txt = txt[2:].strip()
            elif txt.startswith("## "):
                style = "Heading 2"; txt = txt[3:].strip()
            yield txt, style, []


# =====================================================================
# Main parse loop
# =====================================================================
def detect_section(line: str, CP: dict, fallback: str) -> str:
    for cand, key in [
        ("multi", "multi"), ("single", "single"),
        ("tf", "tf"), ("fill", "fill"), ("short", "short"),
    ]:
        for r in CP[cand]:
            if r.search(line):
                return key
    return fallback


def is_chapter(line: str, style: str, CP: dict) -> bool:
    if style.startswith("Heading 1"):
        return True
    for r in CP["chapter"]:
        if r.search(line):
            return True
    return False


def is_section(line: str, style: str) -> bool:
    return style.startswith("Heading 2")


def match_answer(line: str, CP: dict):
    for r in CP["answer"]:
        m = r.match(line)
        if m:
            return m.group(1).strip()
    return None


def match_explanation(line: str, CP: dict):
    for r in CP["explanation"]:
        m = r.match(line)
        if m:
            return m.group(1).strip()
    return None


def normalize_answer(raw: str, qtype: str, CP: dict):
    """Convert raw answer text to canonical form per type."""
    if qtype in ("fill", "short"):
        # Allow `；; / |` separators for multiple acceptable answers
        parts = re.split(r"[;；/|｜,，]\s*", raw.strip())
        return [p.strip() for p in parts if p.strip()]
    if qtype == "tf":
        s = raw.strip().upper().replace(" ", "")
        for cand in CP["tf_a"]:
            if s == cand.upper().replace(" ", ""):
                return "A"
        for cand in CP["tf_b"]:
            if s == cand.upper().replace(" ", ""):
                return "B"
        # Fall through: maybe already a letter
        if s in ("A", "B"):
            return s
        return s[:1] if s and s[0] in "AB" else ""
    # single / multi — resolve alias chars (e.g. ①②③④) via alias_map first,
    # then accept plain canonical letters A-F.
    letters_set = set(CP["letters"])
    result = []
    i = 0
    s = raw.strip()
    while i < len(s):
        # Try longest alias match at position i
        matched = False
        for alias in CP["sorted_aliases"]:
            if s[i:i + len(alias)] == alias:
                canon = CP["alias_map"][alias]
                if canon not in result:  # deduplicate
                    result.append(canon)
                i += len(alias)
                matched = True
                break
        if not matched:
            c = s[i].upper()
            if c in letters_set and c not in result:
                result.append(c)
            i += 1
    return "".join(result)


def strip_qnum(line: str, CP: dict) -> str:
    for r in CP["qnum"]:
        m = r.match(line)
        if m:
            return line[m.end():].strip()
    return line


def parse_stream(stream, CP, source_id="s1"):
    chapters_seen = []
    questions = []
    qid = 0
    current_chapter = "未分类"
    current_type = "single"
    buffer = []
    pending_images = []
    last_q = None        # most recent question (for explanation attach)
    dropped = []

    for raw, style, images in stream:
        if not raw and images:
            # Image-only paragraph belongs to current question buffer
            pending_images.extend(images)
            continue
        # Chapter / section detection
        if is_chapter(raw, style, CP):
            current_chapter = raw
            if raw not in chapters_seen:
                chapters_seen.append(raw)
            buffer = []
            pending_images = []
            continue
        if is_section(raw, style) or any(
            r.search(raw) for k in ("single", "multi", "tf", "fill", "short")
            for r in CP[k]
        ):
            new_t = detect_section(raw, CP, current_type)
            current_type = new_t
            buffer = []
            pending_images = []
            continue
        if any(raw.startswith(p) for p in CP["ignore_prefixes"]):
            continue

        # Explanation line (attaches to last question)
        expl = match_explanation(raw, CP)
        if expl is not None and last_q:
            last_q["explanation"] = (
                (last_q.get("explanation") or "") + " " + expl
            ).strip()
            continue

        # Answer line
        ans_raw = match_answer(raw, CP)
        if ans_raw is not None:
            ans = normalize_answer(ans_raw, current_type, CP)
            if buffer:
                buffer[0] = strip_qnum(buffer[0], CP)
            parsed = parse_buffer(buffer, current_type, CP)
            if parsed and ans:
                qid += 1
                q = {
                    "id": qid,
                    "source_id": source_id,
                    "chapter": current_chapter,
                    "type": current_type,
                    "question": parsed["question"],
                    "options": parsed["options"],
                    "answer": ans,
                    "explanation": "",
                }
                if pending_images:
                    q["images"] = [{"id": f"img{qid}_{i}", "data_url": _img_to_data_url(p)}
                                   for i, p in enumerate(pending_images)]
                q["qhash"] = question_hash(q)
                questions.append(q)
                last_q = q
            else:
                dropped.append({
                    "chapter": current_chapter,
                    "type": current_type,
                    "buffer": buffer.copy(),
                    "answer": ans_raw,
                })
            buffer = []
            pending_images = []
            continue

        buffer.append(raw)
        if images:
            pending_images.extend(images)

    return chapters_seen, questions, dropped


def _img_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".").lower() or "png"
    mime = {"jpg": "jpeg"}.get(ext, ext)
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


# =====================================================================
# CLI
# =====================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="docx/pdf/txt/md (or xlsx/csv via parse_xlsx.py)")
    ap.add_argument("--output", required=True, help="questions.json output path")
    ap.add_argument("--source-id", default="s1")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on dropped or empty-option questions")
    ap.add_argument("--lenient", action="store_true",
                    help="warn only (default behavior)")
    ap.add_argument("--extract-images", action="store_true",
                    help="extract embedded images from docx into <out_dir>/images/")
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    src = args.input
    ext = os.path.splitext(src)[1].lower()
    image_dir = None
    if args.extract_images:
        image_dir = os.path.join(os.path.dirname(os.path.abspath(args.output)), "images")

    if ext == ".docx":
        stream = iter_docx(src, image_out_dir=image_dir)
    elif ext == ".pdf":
        stream = iter_pdf(src)
    elif ext in (".txt", ".md"):
        stream = iter_text(src)
    elif ext in (".xlsx", ".xls", ".csv"):
        sys.exit(f"For {ext} use scripts/parse_xlsx.py")
    else:
        sys.exit(f"ERROR: unsupported file type {ext}")

    P = load_patterns()
    CP = compile_patterns(P)
    chapters, questions, dropped = parse_stream(stream, CP, source_id=args.source_id)

    # Validate
    issues = 0
    for q in questions:
        if q["type"] in ("single", "multi"):
            for L in q["answer"]:
                if not q["options"].get(L):
                    issues += 1
        elif q["type"] == "tf":
            if q["answer"] not in ("A", "B"):
                issues += 1

    by_type = {}
    for q in questions:
        by_type[q["type"]] = by_type.get(q["type"], 0) + 1

    print(f"Total questions: {len(questions)}")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"Chapters: {len(chapters)}")
    print(f"Dropped:  {len(dropped)}")
    print(f"Validation issues: {issues}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": get_version(),
        "generator": "quiz-gen",
        "created_at": utc_now_iso(),
        "sources": [{
            "id": args.source_id,
            "path": str(Path(src).resolve()),
            "sha256": file_sha256(src),
        }],
        "chapters": chapters,
        "questions": questions,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Written: {out_path}")

    if dropped:
        warn = out_path.parent / "_parse_warnings.txt"
        with open(warn, "w", encoding="utf-8") as f:
            for d in dropped:
                f.write(f"=== chapter: {d['chapter']}  type: {d['type']}  ans: {d['answer']} ===\n")
                for ln in d["buffer"]:
                    f.write(f"  | {ln}\n")
                f.write("\n")
        print(f"Warnings: {warn}")

    if args.strict and (dropped or issues):
        sys.exit(2)


if __name__ == "__main__":
    main()
