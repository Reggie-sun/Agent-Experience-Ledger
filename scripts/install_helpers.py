#!/usr/bin/env python3
"""Shared installer helpers for Agent Experience Ledger."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path
from typing import Any

from ledger_common import ledger_root, now_utc


LEGACY_HOOK_NAMES = ("recall_hook.py", "stop_hook.py")
DIRECT_HOOK_NAMES = ("recall.py", "stop_trigger.py")


def command(script_name: str) -> str:
    return f"python3 {shlex.quote(str(ledger_root() / 'scripts' / script_name))}"


def hooks_snippet(user_prompt_script: str = "recall.py", stop_script: str = "stop_trigger.py") -> dict[str, Any]:
    return {
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": command(user_prompt_script), "timeout": 10}]}
            ],
            "Stop": [{"hooks": [{"type": "command", "command": command(stop_script), "timeout": 10}]}],
        }
    }


def probe_hooks_snippet() -> dict[str, Any]:
    return hooks_snippet("hook_probe.py", "hook_probe.py")


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = now_utc().replace(":", "").replace("+", "Z")
    target = path.with_name(f"{path.name}.agent-experience-ledger.{stamp}.bak")
    shutil.copy2(path, target)
    return target


def iter_hook_commands(settings: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return commands
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []):
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    commands.append(hook["command"])
    return commands


def legacy_json_warnings(settings: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for command_text in iter_hook_commands(settings):
        if any(name in command_text for name in LEGACY_HOOK_NAMES):
            warnings.append(
                "legacy wrapper hook command detected; leaving it untouched to avoid deleting user config: "
                f"{command_text}"
            )
    return warnings


def legacy_codex_config_warnings(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    warnings: list[str] = []
    if "Agent Experience Ledger Phase 1 hooks" in text or any(name in text for name in LEGACY_HOOK_NAMES):
        warnings.append(
            f"legacy Codex config hook block may duplicate ~/.codex/hooks.json; leaving it untouched: {path}"
        )
    return warnings


def merge_hooks(existing: dict[str, Any], desired: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    output = dict(existing)
    hooks = output.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit("Refusing to edit settings with non-object hooks")
    changed = False
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
        missing_commands = desired_commands - existing_commands
        if missing_commands:
            for group in groups:
                filtered_hooks = [
                    hook
                    for hook in group.get("hooks", [])
                    if isinstance(hook, dict) and hook.get("command") in missing_commands
                ]
                if filtered_hooks:
                    event_groups.append({**group, "hooks": filtered_hooks})
                    changed = True
    return output, changed


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Refusing to edit invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Refusing to edit non-object JSON: {path}")
    return data


def write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
