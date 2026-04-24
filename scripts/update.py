# -*- coding: utf-8 -*-
"""update.py — Self-check, self-test, and validate-config for quiz-gen.

Subcommands:
    python update.py --check            # print local VERSION + CHANGELOG entry
    python update.py --self-test        # run all fixtures end-to-end
    python update.py --validate-config  # check patterns.yaml, lang/*, templates

Self-test:
    For each tests/fixtures/*.{docx,txt,md,csv,xlsx,pdf}, parse → JSON → check.
    Reports counts and pass/fail per fixture.
    If tests/fixtures/ doesn't exist, prints a warning and continues to validate templates.
"""
import argparse, json, subprocess, sys, os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_version, load_patterns

SUPPORTED_EXTS = {".docx", ".txt", ".md", ".csv", ".xlsx", ".pdf"}


# =====================================================================
# --check
# =====================================================================

def cmd_check() -> None:
    version = get_version()
    print(f"quiz-gen version: {version}")
    print(f"Skill root: {SKILL_ROOT}")

    changelog = SKILL_ROOT / "CHANGELOG.md"
    if not changelog.exists():
        print("CHANGELOG.md not found.")
        return

    lines = changelog.read_text(encoding="utf-8").splitlines()
    # Find the section for current version
    in_section = False
    section_lines = []
    for line in lines:
        if line.startswith(f"## {version}"):
            in_section = True
            section_lines.append(line)
            continue
        if in_section:
            if line.startswith("## ") and not line.startswith(f"## {version}"):
                break
            section_lines.append(line)

    if section_lines:
        print("\n--- CHANGELOG entry ---")
        print("\n".join(section_lines))
    else:
        print(f"\nNo CHANGELOG entry found for v{version}.")
        # Print first section regardless
        for line in lines:
            if line.startswith("## "):
                print(f"Latest entry: {line}")
                break


# =====================================================================
# --validate-config
# =====================================================================

def cmd_validate_config() -> int:
    """Validate patterns.yaml, lang/ files, and templates/. Returns exit code."""
    errors = 0
    warnings = 0

    print("=== Validating config ===\n")

    # patterns.yaml
    patterns_path = SKILL_ROOT / "config" / "patterns.yaml"
    if patterns_path.exists():
        try:
            P = load_patterns()
            required_keys = ["section", "chapter", "question_number", "options",
                             "answer", "explanation", "tf_answers", "ignore"]
            missing = [k for k in required_keys if k not in P]
            if missing:
                print(f"[WARN] patterns.yaml missing top-level keys: {missing}")
                warnings += 1
            else:
                print(f"[OK]   config/patterns.yaml — all required keys present")
        except Exception as e:
            print(f"[ERR]  config/patterns.yaml — failed to load: {e}")
            errors += 1
    else:
        # Try root-level patterns.yaml (legacy location)
        alt = SKILL_ROOT / "patterns.yaml"
        if alt.exists():
            print(f"[WARN] patterns.yaml found at root (legacy). Preferred: config/patterns.yaml")
            warnings += 1
        else:
            print(f"[ERR]  config/patterns.yaml not found")
            errors += 1

    # lang/ directory
    lang_dir = SKILL_ROOT / "lang"
    if lang_dir.exists():
        lang_files = list(lang_dir.glob("*.json")) + list(lang_dir.glob("*.js"))
        if lang_files:
            valid_langs = 0
            for lf in lang_files:
                if lf.suffix == ".json":
                    try:
                        json.loads(lf.read_text(encoding="utf-8"))
                        valid_langs += 1
                    except json.JSONDecodeError as e:
                        print(f"[ERR]  lang/{lf.name} — invalid JSON: {e}")
                        errors += 1
                else:
                    valid_langs += 1  # .js files we can't easily validate
            print(f"[OK]   lang/ — {valid_langs}/{len(lang_files)} files valid")
        else:
            print(f"[WARN] lang/ directory exists but contains no language files")
            warnings += 1
    else:
        print(f"[WARN] lang/ directory not found (i18n may not work)")
        warnings += 1

    # templates/ directory
    templates_dir = SKILL_ROOT / "templates"
    if templates_dir.exists():
        template_files = list(templates_dir.glob("*.html")) + list(templates_dir.glob("*.jinja2"))
        if template_files:
            print(f"[OK]   templates/ — {len(template_files)} template file(s) found: "
                  f"{[f.name for f in template_files]}")
        else:
            # Check subdirectories
            subdirs = [d for d in templates_dir.iterdir() if d.is_dir()]
            if subdirs:
                print(f"[OK]   templates/ — {len(subdirs)} subdirectory/ies: "
                      f"{[d.name for d in subdirs]}")
            else:
                print(f"[WARN] templates/ exists but no .html/.jinja2 files found")
                warnings += 1
    else:
        print(f"[ERR]  templates/ directory not found")
        errors += 1

    # VERSION
    version_file = SKILL_ROOT / "VERSION"
    if version_file.exists():
        ver = version_file.read_text(encoding="utf-8").strip()
        print(f"[OK]   VERSION — {ver}")
    else:
        print(f"[ERR]  VERSION file not found")
        errors += 1

    print(f"\nResult: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


# =====================================================================
# --self-test
# =====================================================================

def run_parse(fixture: Path, tmp_dir: Path) -> dict:
    """Run parse_questions.py (or parse_xlsx.py) on a fixture. Return result dict."""
    ext = fixture.suffix.lower()
    out_json = tmp_dir / f"{fixture.stem}.json"

    if ext in (".xlsx", ".xls", ".csv"):
        script = SKILL_ROOT / "scripts" / "parse_xlsx.py"
    else:
        script = SKILL_ROOT / "scripts" / "parse_questions.py"

    cmd = [sys.executable, str(script), "--input", str(fixture), "--output", str(out_json)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                encoding="utf-8", errors="replace")
        ok = result.returncode == 0
        if ok and out_json.exists():
            try:
                data = json.loads(out_json.read_text(encoding="utf-8"))
                q_count = len(data.get("questions", []))
                return {"ok": True, "questions": q_count, "stdout": result.stdout}
            except Exception as e:
                return {"ok": False, "error": f"JSON parse error: {e}", "stdout": result.stdout}
        else:
            return {"ok": False, "error": result.stderr or result.stdout,
                    "stdout": result.stdout}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (>60s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_self_test() -> int:
    """Run fixtures end-to-end. Returns exit code."""
    import tempfile

    fixtures_dir = SKILL_ROOT / "tests" / "fixtures"

    if not fixtures_dir.exists():
        print(f"Warning: tests/fixtures/ not found at {fixtures_dir}")
        print("Skipping fixture tests. Run --validate-config to check configuration.")
        return 0

    fixtures = [f for f in fixtures_dir.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]

    if not fixtures:
        print(f"Warning: No fixture files found in {fixtures_dir}")
        print(f"Expected extensions: {', '.join(sorted(SUPPORTED_EXTS))}")
        return 0

    print(f"=== Self-test: {len(fixtures)} fixture(s) ===\n")

    with tempfile.TemporaryDirectory(prefix="quiz-gen-selftest-") as tmp:
        tmp_dir = Path(tmp)
        passed = 0
        failed = 0
        results = []

        for fixture in sorted(fixtures):
            result = run_parse(fixture, tmp_dir)
            status = "PASS" if result["ok"] else "FAIL"
            if result["ok"]:
                passed += 1
                detail = f"{result.get('questions', 0)} questions parsed"
            else:
                failed += 1
                detail = result.get("error", "unknown error")[:120]
            print(f"  [{status}] {fixture.name}: {detail}")
            results.append((fixture.name, result["ok"], detail))

    print(f"\nResult: {passed} passed, {failed} failed out of {len(fixtures)} fixture(s)")
    return 0 if failed == 0 else 1


# =====================================================================
# CLI
# =====================================================================

def main():
    ap = argparse.ArgumentParser(
        description="quiz-gen self-check, self-test, and config validation."
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="Print local VERSION and CHANGELOG entry")
    group.add_argument("--self-test", action="store_true",
                       help="Run all fixture files end-to-end and report results")
    group.add_argument("--validate-config", action="store_true",
                       help="Check patterns.yaml, lang/, and templates/ for completeness")
    args = ap.parse_args()

    if args.check:
        cmd_check()
        sys.exit(0)
    elif args.self_test:
        code = cmd_self_test()
        # Also validate config after fixture run
        print()
        validate_code = cmd_validate_config()
        sys.exit(code or validate_code)
    elif args.validate_config:
        code = cmd_validate_config()
        sys.exit(code)


if __name__ == "__main__":
    main()
