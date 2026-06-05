---
schema_version: "1"
title: "Verify scoped commits against a dirty index before stopping"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "workflow"
tags: ["git", "scoped-commit", "dirty-worktree", "review"]
confidence: "high"
repo: "Enterprise-grade_RAG"
branch: "main"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, credentials, account data, or command logs with secrets included."
---

## Summary

When committing a tightly scoped task in a dirty repository, treat the staged index as part of the risk surface. A path-scoped commit can still be confused by previously staged unrelated files, so future agents should verify the final commit contents, not just the status output or intended path list.

## Applies When

- The worktree has unrelated dirty or staged files and the current task must commit only a small allowed path set.
- Some target files are already staged before the current agent starts.
- A commit command fails, returns unexpected output, or the status changes in a surprising way.

## Evidence

- In `Enterprise-grade_RAG` on branch `main`, a SOP template repair session had many unrelated dirty files and one unrelated staged file.
- Final verification with `git show --name-status HEAD` caught that the first commit included `eval/optimization_cases.yaml`, which was outside the task boundary.
- The commit was corrected by restoring only the index entry for that file from `HEAD^`, preserving the worktree change, then amending the commit.

## Lesson

Before stopping after a scoped commit, always run both `git diff --cached --name-only` before committing and `git show --name-status HEAD` after committing. If an unrelated file appears in the commit but its worktree changes must be preserved, remove only the staged/index version with `git restore --source=HEAD^ --staged <path>` and then `git commit --amend --no-edit`.

## Avoid

- Do not assume `git commit --only <paths>` or an intended path list is enough when the index already contains unrelated staged changes.
- Do not use destructive restore/reset commands to fix an accidental commit unless the user explicitly asked to discard worktree changes.
- Do not skip post-commit file-list verification in a dirty repository.

## Verification

- Check `git diff --cached --name-only` before commit.
- Check `git show --name-status HEAD` after commit.
- Confirm `git status --short --untracked-files=all` shows unrelated files still uncommitted and no unintended staged entries remain.
