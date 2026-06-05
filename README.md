# Agent Experience Ledger

Phase 1 is a global passive experience-capture system for Codex and Claude.

It does not use RAG, Qdrant, Redis, embeddings, vector search, or an existing Enterprise-grade RAG backend. It uses hooks, agent skills, local scripts, Markdown files, and GitHub review.

## Repository Layout

- `inbox/`: unreviewed candidate memories written by agents
- `memories/`: reviewed and promoted memories used by recall hooks
- `rejected/`: rejected candidates retained for audit
- `scripts/`: hook handlers and review utilities
- `schema/`: memory schema and examples
- `skills/`: shared skill definitions installed into global agent skill folders

## Phase 1 Flow

1. `UserPromptSubmit` hook reads JSON from stdin.
2. It extracts the prompt, cwd, repo name, and branch.
3. It searches `memories/` using simple keyword scoring.
4. It returns the top relevant memories as `additionalContext`.
5. `Stop` hook reads JSON from stdin.
6. It scores whether the session likely produced reusable engineering experience.
7. If useful and `stop_hook_active` is false, it blocks stopping once and instructs the agent to use `experience-capture`.
8. The agent writes exactly one candidate memory into `inbox/`.
9. A human reviews the candidate in GitHub and promotes or rejects it.

## Quick Start

Validate the repo:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_memory.py --all
python3 scripts/health_check.py
```

Install the shared skill files:

```bash
python3 scripts/install_global.py --install-skills
```

Print hook configuration snippets:

```bash
python3 scripts/install_codex_hooks.py
python3 scripts/install_claude_hooks.py
```

The installer does not call RAG, does not install vector stores, and does not read raw transcripts.

## Design Principle

Procedural code owns deterministic environment work: hook JSON parsing, keyword recall, validation, review moves, and fail-open behavior.

The agent owns judgment work: deciding the reusable lesson and writing the candidate memory. This keeps hooks reliable and keeps memory content reviewable.

## Hook Commands

Use these commands from global hook configuration:

```bash
python3 /absolute/path/to/agent-experience-ledger/scripts/recall.py
python3 /absolute/path/to/agent-experience-ledger/scripts/stop_trigger.py
```

Set `AGENT_EXPERIENCE_LEDGER_ROOT` if the scripts are invoked from another location:

```bash
export AGENT_EXPERIENCE_LEDGER_ROOT=/absolute/path/to/agent-experience-ledger
```

## Review Workflow

Candidate files go to `inbox/` only. Human reviewers promote a candidate after checking privacy, usefulness, and schema compliance:

```bash
python3 scripts/promote.py inbox/2026-06-05-example.md
```

Reject unsafe or low-value candidates:

```bash
python3 scripts/reject_memory.py inbox/2026-06-05-example.md --reason "Too session-specific"
```

Open a PR for review. Do not push directly to `main`, and do not auto-merge memory changes.
