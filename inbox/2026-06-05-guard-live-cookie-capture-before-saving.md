---
schema_version: "1"
title: "Guard live cookie capture with identity checks before saving"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "security"
tags: ["auth-secret", "verification", "tdd", "account-linking"]
confidence: "high"
repo: "csgojiaoben"
branch: "master"
capture_request_id: "capture-20260605-085024-019e96b2-2d29-7f93-bc7b--2ed8c3c4"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, cookie values, tokens, passwords, or live credential material included."
---

## Summary

Before executing a live account-level browser cookie capture, add and verify an identity guard that prevents saving cookies for the wrong account. A failed live capture should be reported as a verified failure, with proof that no credential reference or private cookie file was created.

## Applies When

- Capturing Steam Web, BUFF, or similar browser cookies for account-scoped automation.
- Linking platform identities where one account may already have a stable expected ID.
- Running a live login capture after implementing or changing secret persistence code.

## Evidence

- Added a TDD regression test for rejecting a Steam Web cookie whose parsed SteamID does not match the target purchase account.
- Implemented the guard before running the live capture attempt.
- A live capture attempt timed out without completing login; safe state checks showed `steam_cookie_file` remained empty and no account-level Steam cookie file was created.
- capture_request_id: `capture-20260605-085024-019e96b2-2d29-7f93-bc7b--2ed8c3c4`

## Lesson

Future agents should add account identity validation before saving any live captured credential, then verify both positive behavior and failed-live-attempt behavior. Capability tests, identity guard tests, and safe file-reference checks together make the result trustworthy without exposing secrets.

## Avoid

- Saving a captured cookie solely because the required cookie names exist.
- Treating a timeout or incomplete login as partial success.
- Printing or storing cookie values to prove whether capture worked.

## Verification

- Run focused tests for successful save and identity mismatch rejection.
- Run lint and `git diff --check`.
- After any live capture attempt, inspect only safe indicators: configured file reference, expected private file existence, cookie name/count metadata, and redacted status.
