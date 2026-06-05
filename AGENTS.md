# Agent Experience Ledger Rules

## Phase Boundary
- Phase 1 is a local Markdown ledger. Do not integrate RAG, Qdrant, Redis, vector databases, embeddings, or the Enterprise-grade RAG backend.
- Hooks must fail open: if a script errors, emits invalid input, or cannot access the ledger, the agent session continues normally.
- Candidate memories are written only to `inbox/`. Human review is required before promotion to `memories/`.
- Do not auto-merge memories, and do not push directly to `main`.

## Privacy
- Do not store raw transcripts by default.
- Do not store secrets, API keys, `.env` values, credentials, tokens, customer data, or private content.
- Capture reusable engineering experience, not chat archives, logs, or one-off session summaries.

## Workflow
- Do not use sub-agents in this repository unless the user explicitly asks for them.
- `scripts/recall.py` runs on `UserPromptSubmit` and searches promoted Markdown memories with local keyword scoring.
- `scripts/stop_trigger.py` runs on `Stop` and decides whether to ask the agent to write one candidate memory.
- `scripts/redact.py` redacts secret-looking values before a candidate is written or promoted.
- `skills/experience-capture/SKILL.md` is the shared skill that tells Codex or Claude how to write a safe candidate.
- Review candidates through a branch and PR. Promote with `scripts/promote.py`; reject with `scripts/reject_memory.py`.
