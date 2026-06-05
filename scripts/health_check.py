#!/usr/bin/env python3
"""Local health check for Phase 1 hooks and skill assets."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ledger_common import ledger_root


def run_hook(script: str, payload: dict) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(ledger_root() / "scripts" / script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return False, completed.stderr.strip() or f"exit {completed.returncode}"
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, "stdout was not JSON"
    if not isinstance(parsed, dict):
        return False, "stdout JSON was not an object"
    return True, "ok"


def main() -> int:
    root = ledger_root()
    checks: list[tuple[str, bool, str]] = []
    for relative in [
        "scripts/recall_hook.py",
        "scripts/stop_hook.py",
        "skills/experience-capture/SKILL.md",
        "schema/experience-memory.schema.json",
    ]:
        path = root / relative
        checks.append((relative, path.exists(), "exists" if path.exists() else "missing"))

    ok, detail = run_hook("recall_hook.py", {"prompt": "health check", "cwd": str(root)})
    checks.append(("recall_hook.py sample", ok, detail))
    ok, detail = run_hook(
        "stop_hook.py",
        {
            "hook_event_name": "Stop",
            "stop_hook_active": True,
            "cwd": str(root),
            "last_assistant_message": "health check",
        },
    )
    checks.append(("stop_hook.py active-loop sample", ok, detail))

    global_skill_targets = [
        Path.home() / ".agents" / "skills" / "experience-capture" / "SKILL.md",
        Path.home() / ".claude" / "skills" / "experience-capture" / "SKILL.md",
    ]
    for target in global_skill_targets:
        checks.append((str(target), target.exists(), "installed" if target.exists() else "not installed"))

    failed = False
    for name, passed, detail in checks:
        status = "ok" if passed else "warn"
        if not passed and not name.startswith(str(Path.home())):
            failed = True
            status = "fail"
        print(f"{status}: {name} - {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
