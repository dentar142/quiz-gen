# -*- coding: utf-8 -*-
"""last_config.py — View, clear, or manually set the last-used quiz-gen config.

Stored at ~/.quiz-gen/last.json via common.save_last_config.

Usage:
    python last_config.py --show
    python last_config.py --clear
    python last_config.py --set key=value [key=value …]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_last_config, save_last_config, LAST_CONFIG_HOME


def cmd_show(cfg: dict) -> None:
    if not cfg:
        print(f"No last config found at {LAST_CONFIG_HOME}")
        return
    print(f"Last config ({LAST_CONFIG_HOME}):")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def cmd_clear() -> None:
    p = LAST_CONFIG_HOME
    if p.exists():
        p.unlink()
        print(f"Cleared: {p}")
    else:
        print(f"Nothing to clear (file does not exist: {p})")


def cmd_set(cfg: dict, pairs: list[str]) -> dict:
    for pair in pairs:
        if "=" not in pair:
            print(f"Warning: skipping malformed pair (expected key=value): {pair!r}",
                  file=sys.stderr)
            continue
        key, _, raw_val = pair.partition("=")
        key = key.strip()
        raw_val = raw_val.strip()
        # Attempt to parse as JSON scalar; fall back to string
        try:
            value = json.loads(raw_val)
        except json.JSONDecodeError:
            value = raw_val
        cfg[key] = value
        print(f"  Set {key!r} = {value!r}")
    return cfg


def main():
    ap = argparse.ArgumentParser(
        description="View, clear, or set entries in the quiz-gen last-used config."
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--show", action="store_true",
                       help="Print the current last config")
    group.add_argument("--clear", action="store_true",
                       help="Delete the last config file")
    group.add_argument("--set", nargs="+", metavar="key=value",
                       help="Set one or more keys in the last config")
    args = ap.parse_args()

    if args.show:
        cmd_show(load_last_config())

    elif args.clear:
        cmd_clear()

    elif args.set:
        cfg = load_last_config()
        cfg = cmd_set(cfg, args.set)
        save_last_config(cfg)
        print(f"Saved to {LAST_CONFIG_HOME}")


if __name__ == "__main__":
    main()
