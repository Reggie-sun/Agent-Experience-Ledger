#!/usr/bin/env python3
"""UserPromptSubmit hook: inject relevant promoted memories."""

from __future__ import annotations

import os

from ledger_common import (
    branch_name,
    continue_response,
    cwd_from_payload,
    fail_open,
    find_relevant_memories,
    format_memory_context,
    prompt_from_payload,
    read_json_stdin,
    repo_name,
)


def main() -> dict:
    payload = read_json_stdin()
    prompt = prompt_from_payload(payload)
    cwd = cwd_from_payload(payload)
    enriched_query = " ".join([prompt, repo_name(cwd), branch_name(cwd), str(cwd)])
    top_k = int(os.environ.get("AGENT_EXPERIENCE_LEDGER_TOP_K", "5"))
    matches = find_relevant_memories(enriched_query, top_k=top_k)
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


if __name__ == "__main__":
    raise SystemExit(fail_open(main))
