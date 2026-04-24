# -*- coding: utf-8 -*-
"""merge.py — Merge N questions.json files into one.

Each input gets a unique source_id (s1, s2, …) if not already tagged.
Re-numbers `id` globally. Preserves chapters in encountered order.
With --dedup, drops duplicate questions (same qhash) keeping the first.

Usage:
    python merge.py --inputs file1.json file2.json … --output merged.json [--dedup]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import utc_now_iso, get_version, question_hash, file_sha256


def load_questions_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"ERROR: input file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: invalid JSON in {path}: {e}")


def merge(inputs: list[str], output: str, dedup: bool) -> None:
    all_sources = []
    all_chapters: list[str] = []
    all_questions: list[dict] = []
    seen_hashes: set[str] = set()
    dup_count = 0

    for file_idx, path in enumerate(inputs):
        source_label = f"s{file_idx + 1}"
        data = load_questions_json(path)

        # Build source entry
        try:
            sha = file_sha256(path)
        except Exception:
            sha = ""
        source_entry = {"id": source_label, "path": str(Path(path).resolve()), "sha256": sha}
        all_sources.append(source_entry)

        # Merge chapters preserving order
        for ch in data.get("chapters", []):
            if ch not in all_chapters:
                all_chapters.append(ch)

        # Merge questions, re-tagging source_id to the merge-level label
        for q in data.get("questions", []):
            q_copy = dict(q)
            q_copy["source_id"] = source_label

            # Ensure qhash is present
            if "qhash" not in q_copy or not q_copy["qhash"]:
                q_copy["qhash"] = question_hash(q_copy)

            qh = q_copy["qhash"]
            if dedup:
                if qh in seen_hashes:
                    dup_count += 1
                    continue
                seen_hashes.add(qh)

            all_questions.append(q_copy)

    # Re-number ids globally (1-based)
    for new_id, q in enumerate(all_questions, start=1):
        q["id"] = new_id

    payload = {
        "version": get_version(),
        "generator": "quiz-gen/merge",
        "created_at": utc_now_iso(),
        "sources": all_sources,
        "chapters": all_chapters,
        "questions": all_questions,
    }

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Merged {len(inputs)} file(s) → {len(all_questions)} questions, "
          f"{len(all_chapters)} chapters")
    if dedup:
        print(f"Duplicates removed: {dup_count}")
    print(f"Written: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Merge multiple questions.json files into one.")
    ap.add_argument("--inputs", nargs="+", required=True, metavar="FILE",
                    help="Input questions.json files (two or more)")
    ap.add_argument("--output", required=True, metavar="FILE",
                    help="Output merged questions.json path")
    ap.add_argument("--dedup", action="store_true",
                    help="Drop duplicate questions (same qhash), keeping the first occurrence")
    args = ap.parse_args()

    if len(args.inputs) < 1:
        ap.error("Provide at least one --inputs file.")

    merge(args.inputs, args.output, args.dedup)


if __name__ == "__main__":
    main()
