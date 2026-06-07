#!/usr/bin/env python3
"""Stop hook: decide whether to ask the agent to capture one experience memory."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import uuid
from pathlib import Path

from ledger_common import changed_files, continue_response, cwd_from_payload, diff_stat, ledger_root, run_git


AUDIT_SCHEMA_VERSION = "1"

CAPTURE_REASON = (
    "Before stopping, use the experience-capture skill to write one candidate memory to the ledger inbox. "
    "Capture only reusable engineering experience. Redact secrets. Do not store raw transcript. "
    "When writing the candidate memory, include this capture_request_id in the frontmatter or evidence section. "
    "capture_request_id: "
    "{capture_request_id}. After writing the candidate, stop."
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


def repo_root(cwd: Path) -> str:
    return run_git(cwd, ["rev-parse", "--show-toplevel"])


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


def decision_signals(payload: dict) -> dict:
    cwd = cwd_from_payload(payload)
    files = changed_files(cwd)
    stat = diff_stat(cwd)
    hits = keyword_hits(str(payload.get("last_assistant_message") or ""))
    inside = inside_git_repo(cwd)
    score = 0
    if files:
        score += 2
    if stat:
        score += 2
    score += min(hits, 4)
    if transcript_exists(payload):
        score += 1
    if inside:
        score += 1
    root = repo_root(cwd) if inside else ""
    return {
        "cwd": cwd,
        "repo_root": root,
        "repo_name": Path(root).name if root else "",
        "inside_git_repo": inside,
        "changed_files": files,
        "changed_files_count": len(files),
        "diff_stat_present": bool(stat),
        "current_turn_keyword_hits": hits,
        "score": score,
    }


def score_payload(payload: dict) -> int:
    return int(decision_signals(payload)["score"])


def audit_log_path() -> Path:
    return Path.home() / ".agent-experience-ledger" / "stop-trigger-decisions.jsonl"


def timestamp_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_timestamp(value: object) -> _dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed


def cooldown_seconds() -> int:
    raw = os.environ.get("AGENT_EXPERIENCE_LEDGER_STOP_COOLDOWN_SECONDS", "600")
    try:
        return max(0, int(raw))
    except ValueError:
        return 600


def recent_session_block(payload: dict) -> bool:
    session_id = payload.get("session_id")
    if not session_id:
        return False
    window = cooldown_seconds()
    if window <= 0:
        return False
    path = audit_log_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=window)
    for line in reversed(lines[-200:]):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("session_id") != session_id or entry.get("decision") != "block":
            continue
        timestamp = parse_timestamp(entry.get("timestamp"))
        if timestamp and timestamp >= cutoff:
            return True
    return False


def is_housekeeping_path(path: str) -> bool:
    normalized = path.strip().lstrip("./")
    return normalized == "dogfood-log.md" or normalized.startswith("inbox/")


def is_self_dogfood_housekeeping(signals: dict) -> bool:
    if not signals["repo_root"]:
        return False
    try:
        if Path(signals["repo_root"]).resolve() != ledger_root():
            return False
    except OSError:
        return False
    files = signals.get("changed_files") or []
    return bool(files) and all(is_housekeeping_path(path) for path in files)


def capture_timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def short_identifier(value: object) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug[:24] or uuid.uuid4().hex[:8]


def new_capture_request_id(payload: dict) -> str:
    return f"capture-{capture_timestamp()}-{short_identifier(payload.get('session_id'))}-{uuid.uuid4().hex[:8]}"


def write_audit(
    payload: dict,
    signals: dict,
    decision: str,
    reason_code: str,
    capture_request_id: str | None = None,
) -> None:
    try:
        entry = {
            "timestamp": timestamp_utc(),
            "hook_event_name": payload.get("hook_event_name"),
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "cwd": str(signals["cwd"]),
            "repo_root": signals["repo_root"],
            "repo_name": signals["repo_name"],
            "stop_hook_active": payload.get("stop_hook_active"),
            "inside_git_repo": signals["inside_git_repo"],
            "changed_files_count": signals["changed_files_count"],
            "diff_stat_present": signals["diff_stat_present"],
            "current_turn_keyword_hits": signals["current_turn_keyword_hits"],
            "score": signals["score"],
            "decision": decision,
            "reason_code": reason_code,
            "schema_version": AUDIT_SCHEMA_VERSION,
        }
        if capture_request_id:
            entry["capture_request_id"] = capture_request_id
        path = audit_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        return


def continue_with_audit(payload: dict, signals: dict, reason_code: str) -> dict:
    write_audit(payload, signals, "continue", reason_code)
    return continue_response()


def block_with_audit(payload: dict, signals: dict) -> dict:
    capture_request_id = new_capture_request_id(payload)
    write_audit(payload, signals, "block", "threshold_met", capture_request_id)
    return {"decision": "block", "reason": CAPTURE_REASON.format(capture_request_id=capture_request_id)}


def decide(payload: dict) -> dict:
    signals = decision_signals(payload)
    if payload.get("stop_hook_active") is True:
        return continue_with_audit(payload, signals, "stop_hook_active")
    if is_self_dogfood_housekeeping(signals):
        return continue_with_audit(payload, signals, "self_dogfood_housekeeping")
    if recent_session_block(payload):
        return continue_with_audit(payload, signals, "session_cooldown")
    if signals["current_turn_keyword_hits"] == 0:
        return continue_with_audit(payload, signals, "no_current_turn_signal")
    threshold = 3
    if signals["score"] < threshold:
        return continue_with_audit(payload, signals, "below_threshold")
    return block_with_audit(payload, signals)


def main() -> int:
    try:
        emit(decide(read_payload()))
    except Exception as exc:
        emit({"continue": True, "systemMessage": f"experience stop trigger failed: {exc}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
