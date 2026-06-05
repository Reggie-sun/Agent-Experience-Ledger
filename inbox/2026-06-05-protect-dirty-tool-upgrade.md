---
schema_version: "1"
title: "Protect dirty diverged tool repos before upgrading"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "workflow"
tags: ["git", "upgrade", "workflow"]
confidence: "high"
repo: "Enterprise-grade_RAG"
branch: "main"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, logs, credentials, or private content included."
---

## Summary

When upgrading a separate tool repository that is dirty and diverged from upstream, treat local commits and uncommitted edits as user work first. Make a backup branch, stash uncommitted changes including untracked files, rebase or merge the committed local work onto the fetched upstream, then restore the stash and validate. This preserves local fixes while still completing the upgrade.

## Applies When

- A tool or dependency repository needs to be updated from upstream.
- The target worktree has local commits, staged changes, unstaged changes, or untracked files.
- Upstream changes overlap with locally modified files.

## Evidence

- The gstack update flow found a dirty, diverged `main` with one local commit and multiple staged, unstaged, and untracked files.
- A backup branch was created before changing history, local edits were stashed with untracked files, the local commit was rebased onto `origin/main`, conflicts were resolved by preserving upstream structure while migrating the local fix, and the stash was restored.
- Validation then passed with `./setup`, `bun test browse/test/server-auth.test.ts test/gen-skill-docs.test.ts`, and `git diff --check`.

## Lesson

For upgrade tasks, do not blindly follow upstream instructions that use `git reset --hard` or broad stash/reset flows when the worktree contains local work. First classify the local state and create an explicit recovery point. Then integrate upstream in a way that preserves committed and uncommitted user changes separately.

## Avoid

- Running `git reset --hard origin/main` in a dirty tool repo without checking for local commits and uncommitted work.
- Collapsing staged, unstaged, and untracked changes into an undocumented state that the user cannot reason about after the upgrade.
- Keeping an old local fix verbatim when upstream refactored the surrounding lifecycle; migrate the intent into the new structure instead.

## Verification

- Check `git status --short --branch`, `git rev-list --left-right --count HEAD...origin/main`, and overlapping paths before upgrading.
- After conflict resolution, run targeted tests for the files touched by the local fix and the tool's setup/build command.
- Confirm no conflict markers remain with a line-anchored marker search in the affected files.
