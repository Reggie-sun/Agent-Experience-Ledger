#!/usr/bin/env python3
"""Stop hook: decide whether to ask the agent to capture one experience memory."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ledger_common import changed_files, continue_response, cwd_from_payload, diff_stat, run_git


CAPTURE_REASON = (
    "Before stopping, use the experience-capture skill to write one candidate memory to the ledger inbox. "
    "Capture only reusable engineering experience. Redact secrets. Do not store raw transcript. "
    "After writing the candidate, stop."
)

KEYWORDS = {
    "bug",
    "fix",
    "fixed",
    "root cause",
    "test",
    "tests",
    "refactor",
    "refactored",
    "architecture",
    "decision",
    "failed attempt",
    "rag",
    "memory",
    "agent",
    "evaluation",
}


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


def transcript_exists(payload: dict) -> bool:
    raw = payload.get("transcript_path")
    if not raw:
        return False
    try:
        return Path(str(raw)).expanduser().exists()
    except OSError:
        return False


def inside_git_repo(cwd: Path) -> bool:
    return run_git(cwd, ["rev-parse", "--is-inside-work-tree"]) == "true"


def keyword_hits(message: str) -> int:
    lowered = message.lower()
    hits = 0
    for keyword in KEYWORDS:
        if " " in keyword:
            if keyword in lowered:
                hits += 1
        elif re.search(rf"\b{re.escape(keyword)}\b", lowered):
            hits += 1
    return hits


def score_payload(payload: dict) -> int:
    cwd = cwd_from_payload(payload)
    score = 0
    if changed_files(cwd):
        score += 2
    if diff_stat(cwd):
        score += 2
    score += min(keyword_hits(str(payload.get("last_assistant_message") or "")), 4)
    if transcript_exists(payload):
        score += 1
    if inside_git_repo(cwd):
        score += 1
    return score


def decide(payload: dict) -> dict:
    if payload.get("stop_hook_active") is True:
        return continue_response()
    threshold = 3
    if score_payload(payload) < threshold:
        return continue_response()
    return {"decision": "block", "reason": CAPTURE_REASON}


def main() -> int:
    try:
        emit(decide(read_payload()))
    except Exception as exc:
        emit({"continue": True, "systemMessage": f"experience stop trigger failed: {exc}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
