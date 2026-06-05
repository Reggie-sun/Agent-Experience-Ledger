#!/usr/bin/env python3
"""Reject a candidate from inbox/ to rejected/."""

from __future__ import annotations

import shutil
from pathlib import Path

from ledger_common import build_arg_parser, ledger_root, update_memory_status


def main() -> int:
    parser = build_arg_parser("Reject a memory candidate.")
    parser.add_argument("path", help="Path under inbox/.")
    parser.add_argument("--reason", required=True, help="Short rejection reason.")
    parser.add_argument("--reviewer", default="", help="Reviewer name or handle.")
    args = parser.parse_args()

    root = ledger_root()
    source = Path(args.path).expanduser().resolve()
    inbox = (root / "inbox").resolve()
    rejected = root / "rejected"
    if inbox not in source.parents:
        raise SystemExit(f"Refusing to reject non-inbox file: {source}")
    destination = rejected / source.name
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")
    shutil.move(str(source), str(destination))
    extra = {"rejection_reason": args.reason}
    if args.reviewer:
        extra["reviewer"] = args.reviewer
    update_memory_status(destination, "rejected", extra=extra)
    print(f"Rejected {source.relative_to(root)} -> {destination.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
