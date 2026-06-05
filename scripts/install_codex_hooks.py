#!/usr/bin/env python3
"""Print or install ~/.codex/hooks.json for Agent Experience Ledger."""

from __future__ import annotations

import json
from pathlib import Path

from install_helpers import (
    backup,
    hooks_snippet,
    legacy_codex_config_warnings,
    legacy_json_warnings,
    merge_hooks,
    probe_hooks_snippet,
    read_json_file,
    write_json_file,
)
from ledger_common import build_arg_parser


def main() -> int:
    parser = build_arg_parser("Print or install Codex hooks.json snippet.")
    parser.add_argument("--install", action="store_true", help="Merge into ~/.codex/hooks.json with backup.")
    parser.add_argument("--probe", action="store_true", help="Print or install temporary hook_probe.py hooks.")
    args = parser.parse_args()

    snippet = probe_hooks_snippet() if args.probe else hooks_snippet()
    if not args.install:
        print(json.dumps(snippet, indent=2))
        return 0

    path = Path.home() / ".codex" / "hooks.json"
    existing = read_json_file(path)
    for warning in legacy_json_warnings(existing):
        print(f"Warning: {warning}")
    for warning in legacy_codex_config_warnings(Path.home() / ".codex" / "config.toml"):
        print(f"Warning: {warning}")
    backup_file = backup(path)
    if backup_file:
        print(f"Backed up {path} -> {backup_file}")
    if args.probe:
        write_json_file(path, snippet)
        print(f"Installed temporary Codex probe hooks in {path}")
        return 0
    merged, changed = merge_hooks(existing, snippet)
    write_json_file(path, merged)
    print(f"Installed Codex hooks in {path}")
    if not changed:
        print("Codex hooks already contained canonical commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
