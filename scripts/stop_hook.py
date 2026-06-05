#!/usr/bin/env python3
"""Stop hook: decide whether to request one experience memory candidate."""

from __future__ import annotations

import os
import re

from ledger_common import (
    branch_name,
    changed_files,
    continue_response,
    cwd_from_payload,
    diff_stat,
    fail_open,
    ledger_root,
    read_json_stdin,
    repo_name,
    source_agent,
    tokenize,
)


POSITIVE_TERMS = {
    "implemented": 2,
    "fixed": 2,
    "debugged": 3,
    "root cause": 4,
    "regression": 3,
    "refactored": 2,
    "verified": 2,
    "tests passed": 3,
    "added tests": 3,
    "design": 1,
    "architecture": 2,
    "lesson": 2,
    "pitfall": 3,
    "blocked by": 2,
}

NEGATIVE_TERMS = {
    "no changes": -3,
    "not able to": -2,
    "could not": -1,
    "just a summary": -3,
    "status update": -2,
}


def has_running_background_work(payload: dict) -> bool:
    for key in ("background_tasks", "session_crons"):
        items = payload.get(key)
        if isinstance(items, list) and items:
            return True
    return False


def score_stop(payload: dict, files: list[str], stat: str) -> tuple[int, list[str]]:
    message = str(payload.get("last_assistant_message") or "")
    lowered = message.lower()
    score = 0
    reasons: list[str] = []
    for term, value in POSITIVE_TERMS.items():
        if term in lowered:
            score += value
            reasons.append(term)
    for term, value in NEGATIVE_TERMS.items():
        if term in lowered:
            score += value
            reasons.append(term)
    if len(message) > 600:
        score += 1
        reasons.append("substantial final response")
    if files:
        score += min(len(files), 4)
        reasons.append(f"{len(files)} changed files")
    if stat:
        score += 1
        reasons.append("git diff stat present")
    codeish_tokens = {"test", "api", "hook", "script", "schema", "frontend", "backend", "bug", "fix"}
    overlap = codeish_tokens & set(tokenize(message))
    if overlap:
        score += min(len(overlap), 3)
        reasons.append("engineering keywords")
    if len(message.strip()) < 160 and not files:
        score -= 3
        reasons.append("short response without file changes")
    return score, reasons


def suggested_tags(files: list[str], message: str) -> list[str]:
    tags = set()
    lowered = message.lower()
    if any(path.startswith("scripts/") or path.endswith(".py") for path in files):
        tags.add("automation")
    if any(path.startswith("tests/") or "test" in path for path in files) or "test" in lowered:
        tags.add("testing")
    if "hook" in lowered or any("hook" in path for path in files):
        tags.add("hooks")
    if "debug" in lowered or "root cause" in lowered:
        tags.add("debugging")
    if "design" in lowered or "ui" in lowered:
        tags.add("design")
    return sorted(tags)[:5] or ["engineering"]


def continuation_instruction(payload: dict, files: list[str], stat: str, reasons: list[str]) -> str:
    cwd = cwd_from_payload(payload)
    repo = repo_name(cwd)
    branch = branch_name(cwd)
    agent = source_agent(payload)
    max_files = 12
    visible_files = files[:max_files]
    file_lines = "\n".join(f"- {path}" for path in visible_files) or "- none detected"
    if len(files) > max_files:
        file_lines += f"\n- ... and {len(files) - max_files} more"
    tags = ", ".join(suggested_tags(files, str(payload.get("last_assistant_message") or "")))
    reason_text = ", ".join(reasons[:8]) or "reusable engineering work likely completed"
    stat_text = stat.strip()[:1200] if stat else "No git diff stat available."
    return f"""Before stopping, use the experience-capture skill to write one candidate memory to inbox/. Do not store raw transcript. Redact secrets. Only capture reusable engineering experience. Do not call RAG, embeddings, Qdrant, Redis, or any external memory backend. After writing, stop.

Safe context for the candidate:
- Ledger root: {ledger_root()}
- Source agent: {agent}
- Working directory: {cwd}
- Repo: {repo}
- Branch: {branch}
- Suggested tags: {tags}
- Capture trigger: {reason_text}

Changed files:
{file_lines}

Git diff stat:
{stat_text}
"""


def main() -> dict:
    payload = read_json_stdin()
    if os.environ.get("AGENT_EXPERIENCE_LEDGER_DISABLE_CAPTURE") == "1":
        return continue_response()
    if payload.get("stop_hook_active") is True:
        return continue_response()
    if has_running_background_work(payload):
        return continue_response()
    cwd = cwd_from_payload(payload)
    files = changed_files(cwd)
    stat = diff_stat(cwd)
    score, reasons = score_stop(payload, files, stat)
    threshold = int(os.environ.get("AGENT_EXPERIENCE_LEDGER_CAPTURE_THRESHOLD", "5"))
    if score < threshold:
        return continue_response()
    return {
        "decision": "block",
        "reason": continuation_instruction(payload, files, stat, reasons),
    }


if __name__ == "__main__":
    raise SystemExit(fail_open(main))
