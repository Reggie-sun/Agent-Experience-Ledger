#!/usr/bin/env python3
"""Install Phase 1 global skill files and print hook snippets."""

from __future__ import annotations

import json
import shlex
import shutil
import re
from pathlib import Path

from ledger_common import build_arg_parser, ledger_root, now_utc


BEGIN_MARKER = "# BEGIN Agent Experience Ledger Phase 1 hooks"
END_MARKER = "# END Agent Experience Ledger Phase 1 hooks"


def hook_command(script_name: str) -> str:
    script = ledger_root() / "scripts" / script_name
    return f"python3 {shlex.quote(str(script))}"


def hook_json() -> dict:
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command("recall.py"),
                            "timeout": 10,
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command("stop_trigger.py"),
                            "timeout": 10,
                        }
                    ]
                }
            ],
        }
    }


def codex_toml_snippet() -> str:
    recall = hook_command("recall.py").replace("\\", "\\\\").replace('"', '\\"')
    stop = hook_command("stop_trigger.py").replace("\\", "\\\\").replace('"', '\\"')
    return f"""{BEGIN_MARKER}
# Keep existing hooks and add these groups under top-level [hooks].

[[hooks.UserPromptSubmit]]
[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{recall}"
timeout = 10

[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = "{stop}"
timeout = 10
{END_MARKER}
"""


def backup_path(path: Path) -> Path:
    stamp = now_utc().replace(":", "").replace("+", "Z")
    return path.with_name(f"{path.name}.agent-experience-ledger.{stamp}.bak")


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


def install_claude_hooks() -> None:
    path = Path.home() / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit(f"Refusing to edit non-object JSON: {path}")
        backup = backup_path(path)
        shutil.copy2(path, backup)
        print(f"Backed up {path} -> {backup}")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"Refusing to edit settings with non-object hooks: {path}")
    desired = hook_json()["hooks"]
    for event, groups in desired.items():
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            raise SystemExit(f"Refusing to edit non-list hooks.{event}: {path}")
        desired_command = groups[0]["hooks"][0]["command"]
        already_present = any(
            desired_command == hook.get("command")
            for group in existing
            if isinstance(group, dict)
            for hook in group.get("hooks", [])
            if isinstance(hook, dict)
        )
        if not already_present:
            existing.extend(groups)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Installed Claude hooks in {path}")


def install_codex_hooks() -> None:
    path = Path.home() / ".codex" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if path.exists():
        backup = backup_path(path)
        shutil.copy2(path, backup)
        print(f"Backed up {path} -> {backup}")
    block = codex_toml_snippet().strip() + "\n"
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n?",
        re.DOTALL,
    )
    if pattern.search(original):
        updated = pattern.sub(block, original)
    else:
        separator = "\n\n" if original.strip() else ""
        updated = original.rstrip() + separator + block
    path.write_text(updated, encoding="utf-8")
    print(f"Installed Codex hooks in {path}")


def print_hook_snippets() -> None:
    print("Claude settings JSON snippet:")
    print(json.dumps(hook_json(), indent=2))
    print()
    print("Codex config.toml snippet:")
    print(codex_toml_snippet())


def main() -> int:
    parser = build_arg_parser("Install Agent Experience Ledger global assets.")
    parser.add_argument("--install-skills", action="store_true", help="Copy shared skill to global skill folders.")
    parser.add_argument("--install-claude-hooks", action="store_true", help="Merge hooks into ~/.claude/settings.json.")
    parser.add_argument("--install-codex-hooks", action="store_true", help="Append hooks block to ~/.codex/config.toml.")
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
        install_claude_hooks()
    if args.install_codex_hooks:
        install_codex_hooks()
    if args.write_hook_json:
        path = ledger_root() / "agent-experience-ledger-hooks.json"
        path.write_text(json.dumps(hook_json(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}")
    if args.print_hook_snippets or not any(vars(args).values()):
        print_hook_snippets()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
