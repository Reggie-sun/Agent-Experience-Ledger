#!/usr/bin/env python3
"""Probe hook payloads for VSCode/CLI compatibility dogfooding."""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


CONTINUE_RESPONSE = {"continue": True}


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def read_payload() -> tuple[dict[str, Any], bool]:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}, True
        value = json.loads(raw)
        return (value, True) if isinstance(value, dict) else ({}, True)
    except Exception:
        return {}, False


def prompt_present(payload: dict[str, Any]) -> bool:
    for key in ("prompt", "user_prompt", "message", "input"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return True
    messages = payload.get("messages")
    if isinstance(messages, list):
        return any(
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
            and bool(message["content"].strip())
            for message in messages
        )
    return False


def write_probe_line(payload: dict[str, Any], json_parse_ok: bool) -> None:
    path = Path.home() / ".agent-experience-ledger" / "hook-probe.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": now_utc(),
        "hook_event_name": payload.get("hook_event_name"),
        "cwd": payload.get("cwd"),
        "session_id": payload.get("session_id"),
        "transcript_path_present": bool(payload.get("transcript_path")),
        "prompt_present": prompt_present(payload),
        "last_assistant_message_present": bool(payload.get("last_assistant_message")),
        "json_parse_ok": json_parse_ok,
        "raw_keys": sorted(str(key) for key in payload.keys()),
        "argv": sys.argv,
    }
    if "stop_hook_active" in payload:
        line["stop_hook_active"] = payload.get("stop_hook_active")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        payload, json_parse_ok = read_payload()
        try:
            write_probe_line(payload, json_parse_ok)
        except Exception:
            pass
        print(json.dumps(CONTINUE_RESPONSE))
        return 0
    except Exception:
        print(json.dumps(CONTINUE_RESPONSE))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
