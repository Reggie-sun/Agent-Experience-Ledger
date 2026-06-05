#!/usr/bin/env python3
"""UserPromptSubmit hook: recall promoted memories with local keyword scoring."""

from __future__ import annotations

import json
import os
import sys

from ledger_common import (
    branch_name,
    continue_response,
    cwd_from_payload,
    find_relevant_memories,
    format_memory_context,
    prompt_from_payload,
    repo_name,
)


def read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("hook payload must be a JSON object")
    return value


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False) + "\n")


def build_query(payload: dict) -> str:
    cwd = cwd_from_payload(payload)
    fields = [
        prompt_from_payload(payload),
        str(payload.get("session_id") or ""),
        str(payload.get("hook_event_name") or ""),
        repo_name(cwd),
        branch_name(cwd),
        str(cwd),
    ]
    transcript_path = payload.get("transcript_path")
    if transcript_path:
        fields.append(str(transcript_path))
    return " ".join(part for part in fields if part)


def recall(payload: dict) -> dict:
    top_k = min(int(os.environ.get("AGENT_EXPERIENCE_LEDGER_TOP_K", "5")), 5)
    matches = find_relevant_memories(build_query(payload), top_k=top_k)
    context = format_memory_context(matches)
    if not context:
        return continue_response()
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }


def main() -> int:
    try:
        emit(recall(read_payload()))
    except Exception as exc:
        emit({"continue": True, "systemMessage": f"experience recall failed: {exc}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
