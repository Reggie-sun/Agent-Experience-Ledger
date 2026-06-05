---
name: experience-capture
description: Use when a Codex or Claude Stop hook asks the agent to write one safe Agent Experience Ledger candidate memory after a meaningful coding, debugging, design, or architecture session. Writes only structured Markdown candidates to inbox/, never raw transcripts, secrets, or promoted memories.
---

# Experience Capture

Write one reusable engineering lesson as a structured Markdown candidate in the Agent Experience Ledger.

## Hard Rules

- Write exactly one candidate memory unless the session has no reusable lesson.
- Write only to `inbox/`.
- Do not write to `memories/` or `rejected/`.
- Do not promote, merge, or push memory changes.
- Do not store raw transcript text, transcript paths, logs, pasted private content, customer data, `.env` values, credentials, tokens, API keys, or secrets.
- Do not call RAG, Qdrant, Redis, embeddings, vector databases, or external memory backends.
- Capture reusable engineering experience, not a chat archive or a generic completion summary.
- Raw transcripts are not memories. A transcript can only be used as private local evidence for the agent's judgment and must not be copied into the candidate.

## Workflow

1. Use the safe context from the hook: ledger root, cwd, repo, branch, changed file paths, capture_request_id, source_session_id, source_turn_id, and final outcome.
2. Decide whether there is one durable lesson future agents can reuse.
3. If not, do not write a candidate; stop normally.
4. Confirm the lesson has concrete evidence and assign confidence: `low`, `medium`, or `high`.
5. Draft a concise memory with the schema below. If the Stop instruction includes a `capture_request_id`, include it in frontmatter along with `source_session_id`, `source_turn_id`, `source_repo`, or `source_cwd` when available.
6. Redact any sensitive value before writing. Use `python3 scripts/redact.py` when checking pasted text.
7. Save to `inbox/YYYY-MM-DD-short-slug.md`.
8. Run `python3 scripts/validate_memory.py <candidate-path>` from the ledger root.
9. If validation fails, fix the candidate or delete it if it should not exist.

## Capture When

Capture when the session produced a reusable engineering lesson from:

- a bug, root cause, regression, or failed attempt
- a test, validation, or evaluation pattern
- a refactor, architecture decision, or design tradeoff
- an agent workflow lesson, hook behavior, memory hygiene, or review process

Do not capture routine progress, obvious advice, generic coding guidance, transient status, raw command output, or anything whose only evidence is private transcript text.

## Candidate Shape

```markdown
---
schema_version: "1"
title: "Short reusable engineering lesson"
date: "YYYY-MM-DD"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["hooks", "testing"]
confidence: "medium"
repo: "repo-name"
branch: "branch-name"
capture_request_id: "capture-YYYYMMDD-HHMMSS-short-session"
source_session_id: "session-id-if-provided"
source_turn_id: "turn-id-if-provided"
source_repo: "repo-name-if-provided"
source_cwd: "cwd-if-provided"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript or secrets included."
---

## Summary

One concise paragraph explaining the reusable lesson.

## Applies When

- Concrete trigger or situation where this lesson applies.

## Evidence

- Concrete code path, changed file, test result, reproduced failure, or review observation. Do not paste raw logs unless they are fully sanitized and essential.

## Lesson

Specific future-agent behavior that should change because of this experience.

## Avoid

- Mistake, false shortcut, or unsafe assumption to avoid.

## Verification

- Concrete check, command, review step, or observation that verifies the lesson.
```

## Quality Bar

A good candidate is:

- specific enough to affect future behavior
- short enough to be recalled as context
- independent of private transcript details
- grounded in code, tests, debugging, design, or workflow evidence
- explicit about confidence
- useful beyond this one session

Discard instead of writing when the lesson is only "be careful", "run tests", a task status update, or a one-off fact with no reusable decision value.
