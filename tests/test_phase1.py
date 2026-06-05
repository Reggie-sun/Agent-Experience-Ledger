from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, payload: dict, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, **(env or {})},
        check=False,
    )


def parse_stdout(completed: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(completed.stdout)


def memory_text(status: str = "candidate", title: str = "Keep stop hooks fail-open and loop-safe") -> str:
    return f"""---
schema_version: "1"
title: "{title}"
date: "2026-06-05"
source_agent: "codex"
status: "{status}"
category: "hooks"
tags: ["hooks", "automation"]
confidence: "medium"
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

## Evidence

- The stop hook was run with stop_hook_active true and returned continue.

## Lesson

Always check stop_hook_active before returning a block decision so the agent does not loop.

## Avoid

- Returning a block decision while the hook is already active.

## Verification

- Run the stop hook with stop_hook_active true and confirm it returns continue.
"""


class Phase1Tests(unittest.TestCase):
    def test_recall_returns_at_most_five_relevant_promoted_memories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory_dir = root / "memories" / "hooks"
            memory_dir.mkdir(parents=True)
            (root / "inbox").mkdir()
            for index in range(6):
                title = f"Hook loop memory item {index}"
                (memory_dir / f"hook-loop-{index}.md").write_text(memory_text("promoted", title), encoding="utf-8")

            completed = run_script(
                "recall.py",
                {
                    "prompt": "I am building a Stop hook and need to avoid hook loops.",
                    "cwd": str(root),
                    "session_id": "session-123",
                    "transcript_path": str(root / "transcript.jsonl"),
                    "hook_event_name": "UserPromptSubmit",
                },
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )

            self.assertEqual(completed.returncode, 0)
            result = parse_stdout(completed)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertTrue(result["continue"])
            self.assertTrue(context.startswith("Relevant prior experience:\n"))
            self.assertIn("Hook loop memory item", context)
            self.assertNotIn("6.", context)

    def test_recall_no_match_and_error_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memories").mkdir()
            completed = run_script(
                "recall.py",
                {"prompt": "unrelated prompt", "cwd": str(root)},
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertEqual(parse_stdout(completed), {"continue": True})

            failed = run_script(
                "recall.py",
                {"prompt": "hook", "cwd": str(root)},
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root), "AGENT_EXPERIENCE_LEDGER_TOP_K": "bad"},
            )
            result = parse_stdout(failed)
            self.assertTrue(result["continue"])
            self.assertIn("experience recall failed:", result["systemMessage"])

    def test_stop_trigger_blocks_for_meaningful_git_turn_and_loops_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = root / "transcript.jsonl"
            transcript.write_text("{}", encoding="utf-8")

            completed = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "cwd": str(root),
                    "transcript_path": str(transcript),
                    "last_assistant_message": "Fixed a bug after finding the root cause and adding a test.",
                },
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            result = parse_stdout(completed)
            self.assertEqual(result["decision"], "block")
            self.assertEqual(
                result["reason"],
                "Before stopping, use the experience-capture skill to write one candidate memory to the ledger inbox. "
                "Capture only reusable engineering experience. Redact secrets. Do not store raw transcript. "
                "After writing the candidate, stop.",
            )

            active = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": True,
                    "cwd": str(root),
                    "last_assistant_message": "Fixed a bug.",
                },
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertEqual(parse_stdout(active), {"continue": True})

    def test_stop_trigger_low_score_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = run_script(
                "stop_trigger.py",
                {"hook_event_name": "Stop", "stop_hook_active": False, "cwd": tmp, "last_assistant_message": "Done."},
                {"AGENT_EXPERIENCE_LEDGER_ROOT": tmp},
            )
            self.assertEqual(parse_stdout(completed), {"continue": True})

    def test_redaction_removes_fake_secrets(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ledger_common import contains_secret
        from redact import redact_text

        sample = "\n".join(
            [
                "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456",
                "ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz123456",
                "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456",
                "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
                "DATABASE_URL=postgresql://user:pass@example.com:5432/db",
                "password = super-secret-password",
                "GENERIC_API_KEY=abcdef1234567890",
                "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----",
            ]
        )
        redacted = redact_text(sample)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertFalse(contains_secret(redacted))
        for leaked in ("sk-proj-", "sk-ant-", "ghp_", "postgresql://", "super-secret-password", "abc123"):
            self.assertNotIn(leaked, redacted)

    def test_schema_validation_and_promote_to_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox"
            inbox.mkdir()
            (root / "memories").mkdir()
            (root / "rejected").mkdir()
            candidate = inbox / "hook-loop.md"
            candidate.write_text(memory_text("candidate"), encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "promote.py"), str(candidate)],
                text=True,
                capture_output=True,
                env={**os.environ, "AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            promoted = root / "memories" / "hooks" / "hook-loop.md"
            self.assertTrue(promoted.exists())
            self.assertIn('status: "promoted"', promoted.read_text(encoding="utf-8"))

            invalid = inbox / "invalid.md"
            invalid.write_text(memory_text("candidate").replace('category: "hooks"\n', ""), encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "promote.py"), str(invalid)],
                text=True,
                capture_output=True,
                env={**os.environ, "AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertTrue(invalid.exists())
            self.assertFalse((root / "memories" / "invalid.md").exists())


if __name__ == "__main__":
    unittest.main()
