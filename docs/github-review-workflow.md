# GitHub Review Workflow

Phase 1 treats memories like code review artifacts.

1. Agents write candidates to `inbox/` only.
2. A human opens a branch and PR for review.
3. The reviewer checks privacy, usefulness, and schema compliance.
4. Promote with `scripts/promote.py`.
5. Reject with `scripts/reject_memory.py`.
6. Merge only after review.

Do not auto-promote, auto-merge, or push directly to `main`.
