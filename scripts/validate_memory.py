#!/usr/bin/env python3
"""Validate Agent Experience Ledger Markdown memories."""

from __future__ import annotations

import sys
from pathlib import Path

from ledger_common import build_arg_parser, ledger_root, validate_memory_text


def validate_path(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return validate_memory_text(text)


def main() -> int:
    parser = build_arg_parser("Validate memory Markdown files.")
    parser.add_argument("paths", nargs="*", help="Memory files to validate.")
    parser.add_argument("--all", action="store_true", help="Validate inbox, memories, and rejected.")
    args = parser.parse_args()

    root = ledger_root()
    paths = [Path(item) for item in args.paths]
    if args.all:
        for name in ("inbox", "memories", "rejected"):
            paths.extend(sorted((root / name).glob("*.md")))
    if not paths:
        print("No memory files to validate.")
        return 0

    failed = False
    for path in paths:
        errors = validate_path(path)
        if errors:
            failed = True
            print(f"{path}: failed")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"{path}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
