#!/usr/bin/env python3
"""Print or install ~/.claude/settings.json hooks for Agent Experience Ledger."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path

from ledger_common import build_arg_parser, ledger_root, now_utc


def command(script_name: str) -> str:
    return f"python3 {shlex.quote(str(ledger_root() / 'scripts' / script_name))}"


def hooks_snippet() -> dict:
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": command("recall.py"), "timeout": 10}]}],
            "Stop": [{"hooks": [{"type": "command", "command": command("stop_trigger.py"), "timeout": 10}]}],
        }
    }


def backup(path: Path) -> None:
    if path.exists():
        stamp = now_utc().replace(":", "").replace("+", "Z")
        target = path.with_name(f"{path.name}.agent-experience-ledger.{stamp}.bak")
        shutil.copy2(path, target)
        print(f"Backed up {path} -> {target}")


def merge_hooks(existing: dict, desired: dict) -> dict:
    output = dict(existing)
    hooks = output.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit("Refusing to edit settings with non-object hooks")
    for event, groups in desired["hooks"].items():
        event_groups = hooks.setdefault(event, [])
        if not isinstance(event_groups, list):
            raise SystemExit(f"Refusing to edit non-list hooks.{event}")
        desired_commands = {
            hook["command"]
            for group in groups
            for hook in group.get("hooks", [])
            if isinstance(hook, dict) and "command" in hook
        }
        existing_commands = {
            hook.get("command")
            for group in event_groups
            if isinstance(group, dict)
            for hook in group.get("hooks", [])
            if isinstance(hook, dict)
        }
        if not desired_commands <= existing_commands:
            event_groups.extend(groups)
    return output


def main() -> int:
    parser = build_arg_parser("Print or install Claude settings hooks snippet.")
    parser.add_argument("--install", action="store_true", help="Merge into ~/.claude/settings.json with backup.")
    args = parser.parse_args()

    snippet = hooks_snippet()
    if not args.install:
        print(json.dumps(snippet, indent=2))
        return 0

    path = Path.home() / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            raise SystemExit(f"Refusing to edit non-object JSON: {path}")
    backup(path)
    path.write_text(json.dumps(merge_hooks(existing, snippet), indent=2) + "\n", encoding="utf-8")
    print(f"Installed Claude hooks in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
