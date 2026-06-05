from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, payload: dict, env: dict[str, str]) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, **env},
        check=True,
    )
    return json.loads(completed.stdout)


def memory_text(status: str = "candidate") -> str:
    return f"""---
schema_version: "1"
title: "Keep stop hooks fail-open and loop-safe"
date: "2026-06-05"
source_agent: "codex"
status: "{status}"
tags: ["hooks", "automation"]
repo: "agent-experience-ledger"
branch: "phase-1"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript or secrets included."
---

## Summary

Stop hooks should block only once and otherwise return a continue response.

## Applies When

- Building lifecycle hooks that can ask an agent to continue work.

## Lesson

Always check stop_hook_active before returning a block decision so the agent does not loop.

## Avoid

- Returning a block decision while the hook is already active.

## Verification

- Run the stop hook with stop_hook_active true and confirm it returns continue.
"""


class Phase1Tests(unittest.TestCase):
    def test_recall_hook_returns_relevant_promoted_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memories").mkdir()
            (root / "inbox").mkdir()
            (root / "rejected").mkdir()
            (root / "memories" / "hook-loop.md").write_text(memory_text("promoted"), encoding="utf-8")
            result = run_script(
                "recall_hook.py",
                {"prompt": "I am building a Stop hook and need to avoid loops.", "cwd": str(root)},
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertTrue(result["continue"])
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Keep stop hooks fail-open", context)
            self.assertIn("local keyword search only", context)

    def test_recall_hook_fail_open_without_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memories").mkdir()
            result = run_script(
                "recall_hook.py",
                {"prompt": "unrelated prompt", "cwd": str(root)},
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertEqual(result, {"continue": True})

    def test_stop_hook_blocks_for_meaningful_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("memories", "inbox", "rejected"):
                (root / name).mkdir()
            result = run_script(
                "stop_hook.py",
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "cwd": str(root),
                    "last_assistant_message": (
                        "Implemented a hook system, fixed the root cause, added tests, "
                        "and verified tests passed for the automation scripts."
                    ),
                },
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertEqual(result["decision"], "block")
            self.assertIn("experience-capture", result["reason"])
            self.assertIn("Do not call RAG", result["reason"])

    def test_stop_hook_does_not_loop_when_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(
                "stop_hook.py",
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": True,
                    "cwd": tmp,
                    "last_assistant_message": "Implemented and verified tests passed.",
                },
                {"AGENT_EXPERIENCE_LEDGER_ROOT": tmp},
            )
            self.assertEqual(result, {"continue": True})

    def test_memory_validation_and_secret_detection(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ledger_common import contains_secret, validate_memory_text

        self.assertEqual(validate_memory_text(memory_text()), [])
        self.assertTrue(contains_secret("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456"))
        bad = memory_text().replace("contains_raw_transcript: false", "contains_raw_transcript: true")
        self.assertIn("privacy.contains_raw_transcript must be false", validate_memory_text(bad))


if __name__ == "__main__":
    unittest.main()
