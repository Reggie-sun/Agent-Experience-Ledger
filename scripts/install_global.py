#!/usr/bin/env python3
"""Install Phase 1 global skill files and print hook snippets."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from install_helpers import hooks_snippet
from ledger_common import build_arg_parser, ledger_root


def install_skills() -> None:
    source = ledger_root() / "skills" / "experience-capture" / "SKILL.md"
    targets = [
        Path.home() / ".agents" / "skills" / "experience-capture" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "experience-capture" / "SKILL.md",
    ]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
            backup = target.with_suffix(".md.bak")
            shutil.copy2(target, backup)
            print(f"Backed up {target} -> {backup}")
        shutil.copy2(source, target)
        print(f"Installed {target}")


def print_hook_snippets() -> None:
    print("Deprecated: install_global.py is not the canonical hook installer.")
    print("Use `python3 scripts/install_codex_hooks.py --install` for Codex hooks.")
    print("Use `python3 scripts/install_claude_hooks.py --install` for Claude hooks.")
    print()
    print("Canonical ~/.codex/hooks.json snippet:")
    print(json.dumps(hooks_snippet(), indent=2))
    print()
    print("Canonical ~/.claude/settings.json snippet:")
    print(json.dumps(hooks_snippet(), indent=2))


def main() -> int:
    parser = build_arg_parser("Install Agent Experience Ledger global assets.")
    parser.add_argument("--install-skills", action="store_true", help="Copy shared skill to global skill folders.")
    parser.add_argument(
        "--install-claude-hooks",
        action="store_true",
        help="Deprecated. Use scripts/install_claude_hooks.py --install.",
    )
    parser.add_argument(
        "--install-codex-hooks",
        action="store_true",
        help="Deprecated. Use scripts/install_codex_hooks.py --install.",
    )
    parser.add_argument("--print-hook-snippets", action="store_true", help="Print hook config snippets.")
    parser.add_argument(
        "--write-hook-json",
        action="store_true",
        help="Write a reusable hooks JSON file under the ledger repo.",
    )
    args = parser.parse_args()

    if args.install_skills:
        install_skills()
    if args.install_claude_hooks:
        print("Deprecated: use `python3 scripts/install_claude_hooks.py --install` for canonical Claude hooks.")
    if args.install_codex_hooks:
        print("Deprecated: use `python3 scripts/install_codex_hooks.py --install` for canonical Codex hooks.")
    if args.write_hook_json:
        path = ledger_root() / "agent-experience-ledger-hooks.json"
        path.write_text(json.dumps(hooks_snippet(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}")
    if args.print_hook_snippets or not any(vars(args).values()):
        print_hook_snippets()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
