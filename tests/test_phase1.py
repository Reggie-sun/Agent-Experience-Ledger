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


def run_command(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        capture_output=True,
        env={**os.environ, **(env or {})},
        check=False,
    )


def hook_commands(settings: dict) -> list[str]:
    commands: list[str] = []
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                commands.append(hook.get("command", ""))
    return commands


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
            root = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
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
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )
            result = parse_stdout(completed)
            self.assertEqual(result["decision"], "block")
            self.assertIn("experience-capture skill", result["reason"])
            self.assertIn("Do not store raw transcript", result["reason"])
            self.assertRegex(result["reason"], r"capture_request_id: capture-\d{8}-\d{6}-[a-z0-9-]+")

            active = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": True,
                    "cwd": str(root),
                    "last_assistant_message": "Fixed a bug.",
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )
            self.assertEqual(parse_stdout(active), {"continue": True})

    def test_stop_trigger_low_score_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            completed = run_script(
                "stop_trigger.py",
                {"hook_event_name": "Stop", "stop_hook_active": False, "cwd": tmp, "last_assistant_message": "Done."},
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": tmp},
            )
            self.assertEqual(parse_stdout(completed), {"continue": True})

    def test_stop_trigger_dirty_git_repo_with_ordinary_message_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('ambient dirty worktree')\n", encoding="utf-8")

            completed = run_script(
                "stop_trigger.py",
                {"hook_event_name": "Stop", "stop_hook_active": False, "cwd": str(root), "last_assistant_message": "Done."},
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )

            self.assertEqual(parse_stdout(completed), {"continue": True})

    def test_stop_trigger_suppresses_self_dogfood_housekeeping_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ledger"
            home = Path(tmp) / "home"
            inbox = root / "inbox"
            inbox.mkdir(parents=True)
            home.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (inbox / "candidate.md").write_text(memory_text(), encoding="utf-8")
            (root / "dogfood-log.md").write_text("dogfood note\n", encoding="utf-8")

            completed = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "cwd": str(root),
                    "session_id": "self-dogfood-session",
                    "stop_hook_active": False,
                    "last_assistant_message": "Analyzed hook memory agent tests and capture behavior.",
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )

            self.assertEqual(parse_stdout(completed), {"continue": True})
            entry = read_jsonl(home / ".agent-experience-ledger" / "stop-trigger-decisions.jsonl")[0]
            self.assertEqual(entry["decision"], "continue")
            self.assertEqual(entry["reason_code"], "self_dogfood_housekeeping")

    def test_stop_trigger_cooldown_continues_after_recent_block_in_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            root.mkdir()
            home.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('first change')\n", encoding="utf-8")
            payload = {
                "hook_event_name": "Stop",
                "cwd": str(root),
                "session_id": "cooldown-session",
                "stop_hook_active": False,
                "last_assistant_message": "Fixed a bug after adding tests and documenting the decision.",
            }
            env = {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)}

            first = run_script("stop_trigger.py", payload, env)
            self.assertEqual(parse_stdout(first)["decision"], "block")

            second = run_script(
                "stop_trigger.py",
                {**payload, "turn_id": "next-turn", "last_assistant_message": "Fixed another test and memory issue."},
                env,
            )

            self.assertEqual(parse_stdout(second), {"continue": True})
            entries = read_jsonl(home / ".agent-experience-ledger" / "stop-trigger-decisions.jsonl")
            self.assertEqual(entries[-1]["decision"], "continue")
            self.assertEqual(entries[-1]["reason_code"], "session_cooldown")

    def test_stop_trigger_audit_logs_block_with_capture_request_id_and_no_raw_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('meaningful dirty worktree')\n", encoding="utf-8")
            raw_message = "SENTINEL_RAW_ASSISTANT_MESSAGE fixed bug root cause test"

            completed = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "cwd": str(root),
                    "session_id": "session-abc123",
                    "turn_id": "turn-789",
                    "stop_hook_active": False,
                    "last_assistant_message": raw_message,
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )

            result = parse_stdout(completed)
            self.assertEqual(result["decision"], "block")
            self.assertRegex(result["reason"], r"capture_request_id: capture-\d{8}-\d{6}-[a-z0-9-]+")
            capture_request_id = result["reason"].split("capture_request_id: ", 1)[1].split()[0].rstrip(".")
            audit_path = home / ".agent-experience-ledger" / "stop-trigger-decisions.jsonl"
            self.assertTrue(audit_path.exists())
            raw_audit = audit_path.read_text(encoding="utf-8")
            self.assertNotIn(raw_message, raw_audit)
            self.assertNotIn("last_assistant_message", raw_audit)
            entries = read_jsonl(audit_path)
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["hook_event_name"], "Stop")
            self.assertEqual(entry["session_id"], "session-abc123")
            self.assertEqual(entry["turn_id"], "turn-789")
            self.assertEqual(entry["cwd"], str(root.resolve()))
            self.assertEqual(entry["repo_root"], str(root.resolve()))
            self.assertEqual(entry["repo_name"], root.name)
            self.assertFalse(entry["stop_hook_active"])
            self.assertTrue(entry["inside_git_repo"])
            self.assertEqual(entry["changed_files_count"], 1)
            self.assertGreaterEqual(entry["current_turn_keyword_hits"], 3)
            self.assertGreaterEqual(entry["score"], 3)
            self.assertEqual(entry["decision"], "block")
            self.assertEqual(entry["reason_code"], "threshold_met")
            self.assertEqual(entry["capture_request_id"], capture_request_id)
            self.assertEqual(entry["schema_version"], "1")

    def test_stop_trigger_audit_logs_continue_without_capture_request_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('ambient dirty worktree')\n", encoding="utf-8")

            completed = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "cwd": str(root),
                    "session_id": "session-continue",
                    "stop_hook_active": False,
                    "last_assistant_message": "Done.",
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )

            self.assertEqual(parse_stdout(completed), {"continue": True})
            entry = read_jsonl(home / ".agent-experience-ledger" / "stop-trigger-decisions.jsonl")[0]
            self.assertEqual(entry["decision"], "continue")
            self.assertEqual(entry["reason_code"], "no_current_turn_signal")
            self.assertEqual(entry["current_turn_keyword_hits"], 0)
            self.assertNotIn("capture_request_id", entry)

    def test_recall_writes_safe_audit_without_raw_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ledger"
            home = Path(tmp) / "home"
            memory_dir = root / "memories" / "hooks"
            memory_dir.mkdir(parents=True)
            home.mkdir()
            (memory_dir / "hook-loop.md").write_text(memory_text("promoted"), encoding="utf-8")
            raw_prompt = "SENTINEL_RAW_PROMPT build a Stop hook loop memory"

            completed = run_script(
                "recall.py",
                {
                    "hook_event_name": "UserPromptSubmit",
                    "cwd": str(root),
                    "session_id": "recall-audit-session",
                    "prompt": raw_prompt,
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )

            self.assertTrue(parse_stdout(completed)["continue"])
            audit_path = home / ".agent-experience-ledger" / "recall-decisions.jsonl"
            self.assertTrue(audit_path.exists())
            raw_audit = audit_path.read_text(encoding="utf-8")
            self.assertNotIn(raw_prompt, raw_audit)
            entry = read_jsonl(audit_path)[0]
            self.assertEqual(entry["hook_event_name"], "UserPromptSubmit")
            self.assertEqual(entry["session_id"], "recall-audit-session")
            self.assertEqual(entry["cwd"], str(root.resolve()))
            self.assertTrue(entry["prompt_present"])
            self.assertGreaterEqual(entry["match_count"], 1)
            self.assertTrue(entry["injected_context"])
            self.assertEqual(entry["schema_version"], "1")

    def test_stop_trigger_audit_log_failure_fails_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            (home / ".agent-experience-ledger").write_text("not a directory", encoding="utf-8")
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "changed.py").write_text("print('meaningful dirty worktree')\n", encoding="utf-8")

            completed = run_script(
                "stop_trigger.py",
                {
                    "hook_event_name": "Stop",
                    "cwd": str(root),
                    "session_id": "session-log-failure",
                    "stop_hook_active": False,
                    "last_assistant_message": "Fixed a bug after finding the root cause and adding a test.",
                },
                {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)},
            )

            self.assertEqual(completed.returncode, 0)
            result = parse_stdout(completed)
            self.assertEqual(result["decision"], "block")
            self.assertIn("capture_request_id:", result["reason"])

    def test_stop_trigger_invalid_json_fails_open(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "stop_trigger.py")],
            input="{not-json",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        result = parse_stdout(completed)
        self.assertTrue(result["continue"])
        self.assertIn("experience stop trigger failed:", result["systemMessage"])

    def test_hook_probe_invalid_json_fails_open_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "hook_probe.py"), "--dogfood"],
                input="{not-json",
                text=True,
                capture_output=True,
                env={**os.environ, "HOME": str(home)},
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(parse_stdout(completed), {"continue": True})

            log = home / ".agent-experience-ledger" / "hook-probe.log"
            self.assertTrue(log.exists())
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertIn("timestamp", entry)
            self.assertIsNone(entry["hook_event_name"])
            self.assertIsNone(entry["cwd"])
            self.assertIsNone(entry["session_id"])
            self.assertFalse(entry["transcript_path_present"])
            self.assertFalse(entry["prompt_present"])
            self.assertFalse(entry["last_assistant_message_present"])
            self.assertFalse(entry["json_parse_ok"])
            self.assertEqual(entry["raw_keys"], [])
            self.assertNotIn("stop_hook_active", entry)
            self.assertTrue(entry["argv"][0].endswith("hook_probe.py"))
            self.assertIn("--dogfood", entry["argv"])

    def test_hook_probe_logs_user_prompt_submit_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(ROOT),
                "session_id": "session-123",
                "transcript_path": str(ROOT / "fake-transcript.jsonl"),
                "prompt": "probe prompt is present",
                "last_assistant_message": "assistant message is present",
            }
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "hook_probe.py")],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env={**os.environ, "HOME": str(home)},
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(parse_stdout(completed), {"continue": True})

            entry = json.loads((home / ".agent-experience-ledger" / "hook-probe.log").read_text(encoding="utf-8"))
            self.assertEqual(entry["hook_event_name"], "UserPromptSubmit")
            self.assertEqual(entry["cwd"], str(ROOT))
            self.assertEqual(entry["session_id"], "session-123")
            self.assertTrue(entry["transcript_path_present"])
            self.assertTrue(entry["prompt_present"])
            self.assertTrue(entry["last_assistant_message_present"])
            self.assertTrue(entry["json_parse_ok"])
            self.assertEqual(entry["raw_keys"], sorted(payload.keys()))
            self.assertNotIn("stop_hook_active", entry)

    def test_hook_probe_logs_stop_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            payload = {
                "hook_event_name": "Stop",
                "cwd": str(ROOT),
                "session_id": "session-456",
                "stop_hook_active": True,
                "last_assistant_message": "assistant message is present",
            }
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "hook_probe.py")],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env={**os.environ, "HOME": str(home)},
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(parse_stdout(completed), {"continue": True})

            entry = json.loads((home / ".agent-experience-ledger" / "hook-probe.log").read_text(encoding="utf-8"))
            self.assertEqual(entry["hook_event_name"], "Stop")
            self.assertEqual(entry["cwd"], str(ROOT))
            self.assertEqual(entry["session_id"], "session-456")
            self.assertFalse(entry["transcript_path_present"])
            self.assertFalse(entry["prompt_present"])
            self.assertTrue(entry["last_assistant_message_present"])
            self.assertTrue(entry["stop_hook_active"])
            self.assertTrue(entry["json_parse_ok"])
            self.assertEqual(entry["raw_keys"], sorted(payload.keys()))

    def test_redaction_removes_fake_secret_variants(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ledger_common import contains_secret
        from redact import redact_text

        sample = "\n".join(
            [
                "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456",
                "ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz123456",
                "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456",
                "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
                'Authorization: "Bearer zyxwvutsrqponmlkjihgfedcba987654"',
                "api_key=lowercase-secret-value-123456",
                'secret="""line-one\nline-two-secret"""',
                "DATABASE_URL=postgresql://user:pass@example.com:5432/db",
                "database_url=postgresql://user:p%40ssw0rd@example.com:5432/db",
                "password = super-secret-password",
                "PASSWORD='another-secret-password'",
                "GENERIC_API_KEY=abcdef1234567890",
                '{"token": "json-like-token-value-123456", "client_secret": "json-client-secret-123456"}',
                "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----",
            ]
        )
        redacted = redact_text(sample)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertFalse(contains_secret(redacted))
        for leaked in (
            "sk-proj-",
            "sk-ant-",
            "ghp_",
            "postgresql://",
            "super-secret-password",
            "json-like-token-value",
            "line-two-secret",
            "abc123",
        ):
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

    def test_validate_all_recurses_into_category_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "memories" / "hooks"
            nested.mkdir(parents=True)
            (root / "inbox").mkdir()
            (root / "rejected").mkdir()
            good = nested / "good.md"
            bad = nested / "bad.md"
            good.write_text(memory_text("promoted", "Good recursive memory"), encoding="utf-8")
            bad.write_text(
                memory_text("promoted", "Bad recursive memory").replace(
                    "## Evidence\n\n- The stop hook was run with stop_hook_active true and returned continue.\n\n",
                    "## Evidence\n\n",
                ),
                encoding="utf-8",
            )

            failed = run_command(
                [str(ROOT / "scripts" / "validate_memory.py"), "--all"],
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn(str(good), failed.stdout)
            self.assertIn(str(bad), failed.stdout)
            self.assertIn("missing body section: ## Evidence", failed.stdout)

            bad.unlink()
            passed = run_command(
                [str(ROOT / "scripts" / "validate_memory.py"), "--all"],
                {"AGENT_EXPERIENCE_LEDGER_ROOT": str(root)},
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertIn(f"{good}: ok", passed.stdout)

    def test_schema_validation_rejects_invalid_frontmatter_and_transcripts(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ledger_common import validate_memory_text

        cases = [
            (memory_text().replace('source_agent: "codex"', 'source_agent: "bot"'), "source_agent"),
            (memory_text().replace('confidence: "medium"', 'confidence: "certain"'), "confidence"),
            (memory_text().replace('status: "candidate"', 'status: "draft"'), "status"),
            (memory_text().replace('tags: ["hooks", "automation"]', 'tags: ["Bad Tag"]'), "tags"),
            (memory_text().replace('title: "Keep stop hooks fail-open and loop-safe"\n', ""), "title"),
            (memory_text() + '\n{"role":"user","content":"raw transcript line"}\n', "raw transcript-like"),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected):
                errors = validate_memory_text(text)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_schema_validation_accepts_optional_capture_attribution(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from ledger_common import validate_memory_text

        attributed = memory_text().replace(
            'branch: "phase-1"\n',
            'branch: "phase-1"\n'
            'capture_request_id: "capture-20260605-161657-session-abc123"\n'
            'source_session_id: "session-abc123"\n'
            'source_turn_id: "turn-789"\n'
            'source_repo: "Agent_Experience_Ledger"\n'
            'source_cwd: "/home/reggie/vscode_folder/Agent_Experience_Ledger"\n',
        )

        self.assertEqual(validate_memory_text(attributed), [])

    def test_installers_backup_idempotency_and_legacy_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            claude_settings = home / ".claude" / "settings.json"
            claude_settings.parent.mkdir(parents=True)
            claude_settings.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "python3 /ledger/scripts/stop_hook.py",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            env = {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)}
            first = run_command([str(ROOT / "scripts" / "install_claude_hooks.py"), "--install"], env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("Warning: legacy wrapper hook command detected", first.stdout)
            self.assertTrue(list(claude_settings.parent.glob("settings.json.agent-experience-ledger.*.bak")))
            data = json.loads(claude_settings.read_text(encoding="utf-8"))
            commands = hook_commands(data)
            self.assertEqual(sum("recall.py" in command for command in commands), 1)
            self.assertEqual(sum("stop_trigger.py" in command for command in commands), 1)
            self.assertTrue(any("stop_hook.py" in command for command in commands))

            second = run_command([str(ROOT / "scripts" / "install_claude_hooks.py"), "--install"], env)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            commands = hook_commands(json.loads(claude_settings.read_text(encoding="utf-8")))
            self.assertEqual(sum("recall.py" in command for command in commands), 1)
            self.assertEqual(sum("stop_trigger.py" in command for command in commands), 1)

    def test_probe_installers_print_and_install_temporary_probe_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)}

            printed_codex = run_command([str(ROOT / "scripts" / "install_codex_hooks.py"), "--probe"], env)
            self.assertEqual(printed_codex.returncode, 0, printed_codex.stdout + printed_codex.stderr)
            codex_config = json.loads(printed_codex.stdout)
            self.assertEqual(sum("hook_probe.py" in command for command in hook_commands(codex_config)), 2)
            self.assertFalse(any("recall.py" in command or "stop_trigger.py" in command for command in hook_commands(codex_config)))
            self.assertFalse((home / ".codex" / "hooks.json").exists())

            printed_claude = run_command([str(ROOT / "scripts" / "install_claude_hooks.py"), "--probe"], env)
            self.assertEqual(printed_claude.returncode, 0, printed_claude.stdout + printed_claude.stderr)
            claude_config = json.loads(printed_claude.stdout)
            self.assertEqual(sum("hook_probe.py" in command for command in hook_commands(claude_config)), 2)
            self.assertFalse(any("recall.py" in command or "stop_trigger.py" in command for command in hook_commands(claude_config)))
            self.assertFalse((home / ".claude" / "settings.json").exists())

            hooks = home / ".codex" / "hooks.json"
            hooks.parent.mkdir(parents=True)
            hooks.write_text(json.dumps({"hooks": {"Stop": []}}), encoding="utf-8")
            installed = run_command([str(ROOT / "scripts" / "install_codex_hooks.py"), "--probe", "--install"], env)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            self.assertIn("Installed temporary Codex probe hooks", installed.stdout)
            self.assertTrue(list(hooks.parent.glob("hooks.json.agent-experience-ledger.*.bak")))
            commands = hook_commands(json.loads(hooks.read_text(encoding="utf-8")))
            self.assertEqual(sum("hook_probe.py" in command for command in commands), 2)
            self.assertFalse(any("recall.py" in command or "stop_trigger.py" in command for command in commands))

    def test_codex_installer_invalid_json_fails_safe_and_warns_for_legacy_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            hooks = codex_dir / "hooks.json"
            hooks.write_text("{not-json", encoding="utf-8")
            env = {"HOME": str(home), "AGENT_EXPERIENCE_LEDGER_ROOT": str(ROOT)}
            failed = run_command([str(ROOT / "scripts" / "install_codex_hooks.py"), "--install"], env)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(hooks.read_text(encoding="utf-8"), "{not-json")

            hooks.write_text("{}", encoding="utf-8")
            (codex_dir / "config.toml").write_text(
                "# BEGIN Agent Experience Ledger Phase 1 hooks\ncommand = \"python3 /ledger/scripts/recall_hook.py\"\n",
                encoding="utf-8",
            )
            installed = run_command([str(ROOT / "scripts" / "install_codex_hooks.py"), "--install"], env)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            self.assertIn("Warning: legacy Codex config hook block may duplicate", installed.stdout)
            self.assertTrue(list(codex_dir.glob("hooks.json.agent-experience-ledger.*.bak")))
            commands = hook_commands(json.loads(hooks.read_text(encoding="utf-8")))
            self.assertEqual(sum("recall.py" in command for command in commands), 1)
            self.assertEqual(sum("stop_trigger.py" in command for command in commands), 1)


if __name__ == "__main__":
    unittest.main()
