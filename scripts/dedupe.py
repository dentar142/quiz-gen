# -*- coding: utf-8 -*-
"""dedupe.py — Standalone dedup tool for a single questions.json.

Reports duplicate questions (same qhash) and their indices.
With --apply, rewrites the file keeping only the first occurrence of each duplicate.

Usage:
    python dedupe.py --input questions.json [--apply]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import utc_now_iso, get_version, question_hash


def load_questions_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"ERROR: file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: invalid JSON in {path}: {e}")


def find_duplicates(questions: list[dict]) -> dict[str, list[int]]:
    """Return {qhash: [idx, idx, …]} for hashes with 2+ occurrences."""
    hash_to_indices: dict[str, list[int]] = {}
    for i, q in enumerate(questions):
        qh = q.get("qhash") or question_hash(q)
        hash_to_indices.setdefault(qh, []).append(i)
    return {qh: idxs for qh, idxs in hash_to_indices.items() if len(idxs) > 1}


def report_duplicates(questions: list[dict], dups: dict[str, list[int]]) -> None:
    if not dups:
        print("No duplicates found.")
        return

    total_extra = sum(len(idxs) - 1 for idxs in dups.values())
    print(f"Found {len(dups)} duplicate group(s), {total_extra} extra question(s) to remove:\n")
    for group_num, (qh, idxs) in enumerate(dups.items(), start=1):
        q_kept = questions[idxs[0]]
        print(f"  Group {group_num}: qhash={qh}")
        print(f"    Keep  → id={q_kept.get('id')} (index {idxs[0]}): "
              f"{q_kept.get('question', '')[:60]!r}")
        for dup_idx in idxs[1:]:
            q_dup = questions[dup_idx]
            print(f"    Drop  → id={q_dup.get('id')} (index {dup_idx}): "
                  f"{q_dup.get('question', '')[:60]!r}")
        print()


def dedupe_questions(questions: list[dict]) -> tuple[list[dict], int]:
    """Return (deduped list, count removed). Keeps first occurrence."""
    seen: set[str] = set()
    kept: list[dict] = []
    removed = 0
    for q in questions:
        qh = q.get("qhash") or question_hash(q)
        if qh in seen:
            removed += 1
        else:
            seen.add(qh)
            kept.append(q)
    # Re-number ids
    for new_id, q in enumerate(kept, start=1):
        q["id"] = new_id
    return kept, removed


def main():
    ap = argparse.ArgumentParser(
        description="Report (and optionally remove) duplicate questions in a questions.json file."
    )
    ap.add_argument("--input", required=True, metavar="FILE",
                    help="Path to questions.json")
    ap.add_argument("--apply", action="store_true",
                    help="Rewrite the file removing duplicates (kept: first occurrence)")
    args = ap.parse_args()

    data = load_questions_json(args.input)
    questions = data.get("questions", [])

    dups = find_duplicates(questions)
    report_duplicates(questions, dups)

    if not args.apply:
        if dups:
            print("Run with --apply to rewrite the file and remove duplicates.")
        return

    if not dups:
        print("Nothing to do.")
        return

    kept, removed = dedupe_questions(questions)
    data["questions"] = kept
    data["version"] = get_version()
    data["created_at"] = utc_now_iso()

    out_path = Path(args.input)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Removed {removed} duplicate(s). {len(kept)} questions remain.")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
