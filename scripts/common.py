# -*- coding: utf-8 -*-
"""Shared helpers: pattern loader, hashing, normalization, last-config persistence."""
import hashlib, json, os, re, sys, time
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
PATTERNS_DEFAULT = Path(__file__).resolve().parent.parent / "config" / "patterns.yaml"
LAST_CONFIG_HOME = Path.home() / ".quiz-gen" / "last.json"


def get_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"


# ---------------------------------------------------------------------
# YAML loader (zero-dependency: try PyYAML, else minimal subset)
# ---------------------------------------------------------------------
def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_yaml(text)


def _mini_yaml(text: str) -> dict:
    """Tiny YAML subset: supports nested mappings, scalar / quoted strings,
    and `- item` lists. Intended only for our patterns.yaml shape."""
    root: dict = {}
    stack: list = [(0, root)]  # list of (indent, container)

    def parse_scalar(s: str):
        s = s.strip()
        if not s:
            return None
        if (s.startswith("'") and s.endswith("'")) or (
            s.startswith('"') and s.endswith('"')
        ):
            return s[1:-1]
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        if s.lower() in ("null", "~", ""):
            return None
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s

    def parse_inline_list(s: str):
        s = s.strip()
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            if not inner:
                return []
            parts, buf, depth, q = [], "", 0, None
            for ch in inner:
                if q:
                    buf += ch
                    if ch == q:
                        q = None
                elif ch in "'\"":
                    q = ch
                    buf += ch
                elif ch == "[":
                    depth += 1
                    buf += ch
                elif ch == "]":
                    depth -= 1
                    buf += ch
                elif ch == "," and depth == 0:
                    parts.append(buf)
                    buf = ""
                else:
                    buf += ch
            if buf.strip():
                parts.append(buf)
            return [parse_scalar(p) for p in parts]
        return None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # Pop stack to current indent
        while stack and stack[-1][0] > indent:
            stack.pop()
        parent = stack[-1][1]

        # List item
        if stripped.startswith("- "):
            val_str = stripped[2:].strip()
            il = parse_inline_list(val_str)
            value = il if il is not None else parse_scalar(val_str)
            if isinstance(parent, list):
                parent.append(value)
            else:
                # Convert dict-key context: parent should already be a list
                # ; if not, ignore.
                pass
            continue

        # key: value
        if ":" in stripped:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if not rest:
                # Determine new container by peeking next non-empty line
                child: object = {}
                # Provisionally a dict; will be converted to list if first
                # child is a list item.
                if isinstance(parent, dict):
                    parent[key] = child
                stack.append((indent + 2, child))
                continue
            il = parse_inline_list(rest)
            if il is not None:
                value: object = il
            else:
                value = parse_scalar(rest)
            if isinstance(parent, dict):
                parent[key] = value
    # Post-process: convert any dicts with only integer-like keys?  Skip — we
    # don't need that for our schema.
    return root


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_patterns() -> dict:
    base = _load_yaml(PATTERNS_DEFAULT)
    for override in (
        Path.cwd() / ".quiz-gen" / "patterns.yaml",
        Path.home() / ".quiz-gen" / "patterns.yaml",
    ):
        if override.exists():
            base = _deep_merge(base, _load_yaml(override))
    # Heal: list-shaped containers may have been left as dicts
    for top in list(base.values()):
        pass
    return base


# ---------------------------------------------------------------------
# Hashing & normalization
# ---------------------------------------------------------------------
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("（", "(").replace("）", ")")
    return s.lower()


def question_hash(q: dict) -> str:
    payload = normalize_text(q.get("question", "")) + "||" + "||".join(
        normalize_text(q.get("options", {}).get(L, ""))
        for L in "ABCDEF"
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------
# Last-config persistence
# ---------------------------------------------------------------------
def load_last_config() -> dict:
    try:
        return json.loads(LAST_CONFIG_HOME.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_config(cfg: dict) -> None:
    try:
        LAST_CONFIG_HOME.parent.mkdir(parents=True, exist_ok=True)
        LAST_CONFIG_HOME.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ---------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------
def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
