# -*- coding: utf-8 -*-
"""
quiz-gen v2 HTML builder.

Injects questions.json + i18n + config into an HTML template.
Also offers --check mode to verify a built file.

Template tokens:
  /*__DATA_PLACEHOLDER__*/    → minified questions JSON
  /*__I18N_PLACEHOLDER__*/    → language JSON
  /*__CONFIG_PLACEHOLDER__*/  → config JSON object
  <!--__PWA_LINKS__-->        → manifest <link> (when --pwa)
  <!--__PWA_REGISTER__-->     → SW registration <script> (when --pwa)

Usage:
  python build_html.py --data q.json --template tpl.html --output out.html \\
      --lang zh-CN --pwa --cloud-sync
  python build_html.py --check out.html
"""
import argparse, base64, hashlib, json, os, re, sys, io
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def load_lang(lang: str) -> dict:
    lang_file = SKILL_ROOT / "lang" / f"{lang}.json"
    if not lang_file.exists():
        sys.exit(f"ERROR: lang file not found: {lang_file}")
    with open(lang_file, encoding="utf-8") as f:
        return json.load(f)


def load_pwa_assets():
    """Return (manifest_b64, sw_b64) for embedding."""
    manifest_path = SKILL_ROOT / "pwa" / "manifest.json"
    sw_path = SKILL_ROOT / "pwa" / "service-worker.js"
    if not manifest_path.exists():
        sys.exit(f"ERROR: pwa/manifest.json not found at {manifest_path}")
    if not sw_path.exists():
        sys.exit(f"ERROR: pwa/service-worker.js not found at {sw_path}")
    manifest_b64 = base64.b64encode(manifest_path.read_bytes()).decode("ascii")
    sw_b64 = base64.b64encode(sw_path.read_bytes()).decode("ascii")
    return manifest_b64, sw_b64


def parse_modes(modes_str: str) -> list:
    try:
        return [int(x.strip()) for x in modes_str.split(",") if x.strip()]
    except ValueError:
        sys.exit(f"ERROR: --modes must be comma-separated integers, got: {modes_str}")


def detect_latex(data: dict) -> bool:
    """Check if any question/option/explanation contains LaTeX markers."""
    pat = re.compile(r"\$")
    for q in data.get("questions", []):
        if pat.search(q.get("question", "")):
            return True
        for v in q.get("options", {}).values():
            if pat.search(v):
                return True
        if pat.search(q.get("explanation", "") or ""):
            return True
    return False


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(args):
    # Load data
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    # Load template
    with open(args.template, encoding="utf-8") as f:
        tpl = f.read()

    # Load i18n
    i18n = load_lang(args.lang)

    # Parse modes
    modes = parse_modes(args.modes) if args.modes else [1, 2, 3]

    # Detect latex
    has_latex = detect_latex(data)

    # Scoring
    scoring = {
        "single": args.single_score,
        "multi":  args.multi_score,
        "tf":     args.tf_score,
        "fill":   args.fill_score,
        "short":  args.short_score,
    }

    # Test config
    test_chapters = (
        [c.strip() for c in args.test_chapters.split(",") if c.strip()]
        if args.test_chapters else None
    )
    test_config = {
        "single":   args.test_single,
        "multi":    args.test_multi,
        "tf":       args.test_tf,
        "fill":     args.test_fill,
        "short":    args.test_short,
        "chapters": test_chapters,
    }

    # Features
    features = {
        "dark_mode":      not args.no_dark,
        "pwa":            args.pwa,
        "cloud_sync":     args.cloud_sync,
        "notes":          not args.no_notes,
        "wrong_practice": not args.no_wrong_practice,
        "latex":          has_latex,
    }

    # Config object
    config = {
        "modes":       modes,
        "scoring":     scoring,
        "test_config": test_config,
        "features":    features,
        "dark_default": not args.no_dark,
        "lang":        args.lang,
    }

    # Derive theme name from template path
    tpl_path = Path(args.template)
    theme_name = tpl_path.stem  # e.g. "fluent"
    if args.theme:
        theme_name = args.theme

    # Minify JSON payloads
    js_data   = json.dumps(data,   ensure_ascii=False, separators=(",", ":"))
    js_i18n   = json.dumps(i18n,   ensure_ascii=False, separators=(",", ":"))
    js_config = json.dumps(config, ensure_ascii=False, separators=(",", ":"))

    # Replace placeholders
    out = tpl
    out = out.replace("/*__DATA_PLACEHOLDER__*/",   js_data)
    out = out.replace("/*__I18N_PLACEHOLDER__*/",   js_i18n)
    out = out.replace("/*__CONFIG_PLACEHOLDER__*/", js_config)

    # PWA embedding
    if args.pwa:
        manifest_b64, sw_b64 = load_pwa_assets()
        pwa_link = (
            f'<link rel="manifest" href="data:application/manifest+json;base64,{manifest_b64}">'
        )
        # SW is registered via a blob URL derived from base64
        pwa_register = (
            "<script>\n"
            "(function(){\n"
            "  if(!('serviceWorker' in navigator)) return;\n"
            f"  var swB64='{sw_b64}';\n"
            "  var bin=atob(swB64);\n"
            "  var arr=new Uint8Array(bin.length);\n"
            "  for(var i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);\n"
            "  var blob=new Blob([arr],{type:'application/javascript'});\n"
            "  var url=URL.createObjectURL(blob);\n"
            "  navigator.serviceWorker.register(url).catch(function(){});\n"
            "})();\n"
            "</script>"
        )
        out = out.replace("<!--__PWA_LINKS__-->",    pwa_link)
        out = out.replace("<!--__PWA_REGISTER__-->", pwa_register)
    else:
        out = out.replace("<!--__PWA_LINKS__-->",    "")
        out = out.replace("<!--__PWA_REGISTER__-->", "")

    # Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")

    size_bytes = out_path.stat().st_size
    n_q = len(data.get("questions", []))
    n_ch = len(data.get("chapters", []))
    print(f"Built: {args.output} ({size_bytes/1024:.1f} KB), Embedded: {n_q} questions, {n_ch} chapters")

    # Write build.json
    build_json = {
        "version":     "2.0.0",
        "built_at":    utc_now(),
        "template":    theme_name,
        "lang":        args.lang,
        "modes":       modes,
        "scoring":     scoring,
        "test_config": test_config,
        "features":    features,
        "data": {
            "questions":    n_q,
            "chapters":     n_ch,
            "sha256":       sha256_file(args.data),
            "source_files": [s.get("path", "") for s in data.get("sources", [])],
        },
        "output_size_bytes": size_bytes,
    }
    build_out = out_path.parent / "build.json"
    build_out.write_text(
        json.dumps(build_json, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Manifest: {build_out}")


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------
def check(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()

    problems = []
    warnings = []

    # Templates may legitimately omit I18N/CONFIG (e.g., sketch.html mode-1
    # only). DATA placeholder, however, MUST be replaced.
    if "/*__DATA_PLACEHOLDER__*/" in html:
        problems.append("placeholder NOT replaced: /*__DATA_PLACEHOLDER__*/")
    for tok in ("/*__I18N_PLACEHOLDER__*/", "/*__CONFIG_PLACEHOLDER__*/"):
        if tok in html:
            warnings.append(f"placeholder NOT replaced: {tok}")

    # Verify DATA (required)
    m = re.search(r"const DATA\s*=\s*(.*?);", html, re.DOTALL)
    if not m:
        problems.append("DATA constant not found")
    else:
        try:
            data = json.loads(m.group(1))
            qn = len(data.get("questions", []))
            cn = len(data.get("chapters", []))
            print(f"  questions: {qn}, chapters: {cn}")
            if qn == 0:
                problems.append("DATA has 0 questions")
        except Exception as e:
            problems.append(f"DATA JSON invalid: {e}")

    # Verify I18N (optional)
    m2 = re.search(r"const I18N\s*=\s*(.*?);", html, re.DOTALL)
    if not m2:
        warnings.append("I18N constant not present (template uses hardcoded strings)")
    else:
        try:
            json.loads(m2.group(1))
        except Exception as e:
            problems.append(f"I18N JSON invalid: {e}")

    # Verify CONFIG (optional)
    m3 = re.search(r"const CONFIG\s*=\s*(.*?);", html, re.DOTALL)
    if not m3:
        warnings.append("CONFIG constant not present (template ignores build flags)")
    else:
        try:
            json.loads(m3.group(1))
        except Exception as e:
            problems.append(f"CONFIG JSON invalid: {e}")

    # Simple tag-balance heuristic
    for tag in ("div", "section", "button", "header", "main", "p", "span"):
        opens  = len(re.findall(rf"<{tag}\b", html))
        closes = len(re.findall(rf"</{tag}\b", html))
        if opens != closes:
            problems.append(f"tag <{tag}> imbalance: {opens} open vs {closes} close")

    for w in warnings:
        print(f"  ! {w}")
    if problems:
        print("FAIL:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("OK")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="quiz-gen v2 HTML builder")
    ap.add_argument("--data",     help="questions.json path")
    ap.add_argument("--template", help="template HTML path")
    ap.add_argument("--output",   help="output HTML path")
    ap.add_argument("--theme",    choices=["fluent","sketch","material","neumorphism","terminal","paper"],
                    help="theme name (informational; selects template stem)")
    ap.add_argument("--lang",     choices=["zh-CN","en-US","ja-JP"], default="zh-CN")
    ap.add_argument("--modes",    default="1,2,3", help="comma list e.g. 1,2,3")

    # Scoring
    ap.add_argument("--single-score", type=int, default=5)
    ap.add_argument("--multi-score",  type=int, default=3)
    ap.add_argument("--tf-score",     type=int, default=2)
    ap.add_argument("--fill-score",   type=int, default=4)
    ap.add_argument("--short-score",  type=int, default=6)

    # Test config
    ap.add_argument("--test-single",   type=int, default=20)
    ap.add_argument("--test-multi",    type=int, default=10)
    ap.add_argument("--test-tf",       type=int, default=0)
    ap.add_argument("--test-fill",     type=int, default=0)
    ap.add_argument("--test-short",    type=int, default=0)
    ap.add_argument("--test-chapters", default=None, help="comma-separated chapter filter")

    # Feature flags
    ap.add_argument("--no-dark",           action="store_true")
    ap.add_argument("--pwa",               action="store_true")
    ap.add_argument("--cloud-sync",        action="store_true")
    ap.add_argument("--no-notes",          action="store_true")
    ap.add_argument("--no-wrong-practice", action="store_true")

    # Check mode
    ap.add_argument("--check", help="verify a built HTML and exit")

    args = ap.parse_args()

    if args.check:
        check(args.check)
        return

    if not (args.data and args.template and args.output):
        ap.error("--data, --template, --output required (or use --check)")

    build(args)


if __name__ == "__main__":
    main()
