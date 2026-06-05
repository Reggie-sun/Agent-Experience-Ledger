#!/usr/bin/env python3
"""Promote a reviewed candidate from inbox/ to memories/."""

from __future__ import annotations

import shutil
from pathlib import Path

from ledger_common import (
    build_arg_parser,
    ledger_root,
    update_memory_status,
    validate_memory_text,
)


def main() -> int:
    parser = build_arg_parser("Promote a reviewed memory candidate.")
    parser.add_argument("path", help="Path under inbox/.")
    parser.add_argument("--reviewer", default="", help="Reviewer name or handle.")
    args = parser.parse_args()

    root = ledger_root()
    source = Path(args.path).expanduser().resolve()
    inbox = (root / "inbox").resolve()
    memories = root / "memories"
    if inbox not in source.parents:
        raise SystemExit(f"Refusing to promote non-inbox file: {source}")
    text = source.read_text(encoding="utf-8")
    errors = validate_memory_text(text, expected_statuses={"candidate"})
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    destination = memories / source.name
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")
    shutil.move(str(source), str(destination))
    extra = {"reviewer": args.reviewer} if args.reviewer else {}
    update_memory_status(destination, "promoted", extra=extra)
    print(f"Promoted {source.relative_to(root)} -> {destination.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
