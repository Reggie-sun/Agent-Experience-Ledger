#!/usr/bin/env python3
"""Redact secrets from stdin or files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ledger_common import contains_secret, redact_secrets


def redact_text(text: str) -> str:
    return redact_secrets(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact secret-looking values.")
    parser.add_argument("paths", nargs="*", help="Files to redact. Reads stdin when omitted.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if input contains secret-looking values.")
    args = parser.parse_args()

    found = False
    if args.paths:
        for raw in args.paths:
            path = Path(raw)
            text = path.read_text(encoding="utf-8")
            found = contains_secret(text) or found
            sys.stdout.write(redact_text(text))
    else:
        text = sys.stdin.read()
        found = contains_secret(text)
        sys.stdout.write(redact_text(text))
    return 1 if args.check and found else 0


if __name__ == "__main__":
    raise SystemExit(main())
