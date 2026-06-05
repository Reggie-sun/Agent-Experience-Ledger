---
schema_version: "1"
title: "Account-scoped cookie capture must separate secret storage from config references"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "security"
tags: ["auth-secret", "config-runtime", "testing", "purchase-queue"]
confidence: "high"
repo: "csgojiaoben"
branch: "master"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, cookie values, tokens, passwords, or live credential material included."
---

## Summary

When adding capture flows for browser login cookies, treat the cookie value as secret-bearing runtime state and keep `config.yaml` limited to account-scoped file references plus identity metadata. The API can report capture status and configured paths, but tests should prove that responses and tracked config never contain the captured cookie value.

## Applies When

- Adding BUFF, Steam Web, or similar browser cookie capture for a multi-account trading or automation flow.
- Extending config APIs that save `purchase_accounts` credential references.
- Wiring a capture service into a route that receives secret values from a browser, sidecar, or local profile import.

## Evidence

- Implemented an account-scoped Steam Web cookie capture path that writes captured cookies to `data/purchase_accounts/{account_id}/steam_cookies.json` and backfills only `purchase_accounts[].steam_cookie_file`.
- Added service and API tests covering successful save, missing required Steam Web login cookie failure, response redaction, and config-file redaction.
- Verification passed with `pytest tests/test_services/test_steam_web_cookie_capture.py tests/test_services/test_steam_gc_password_bootstrap.py tests/test_api/test_config.py tests/test_services/test_purchase_account_auto_link.py tests/test_purchase_queue -q`, `ruff check` on changed files, and `git diff --check`.

## Lesson

Future agents should model secret capture as two separate concerns: validate and persist the secret only in the account-private credential file, then update config with a non-secret reference. Include regression tests that inspect the API response and tracked config text for absence of the captured sentinel value.

## Avoid

- Writing browser cookie strings, refresh tokens, passwords, or Guard codes into `config.yaml`, docs, logs, status responses, or memory candidates.
- Treating Steam GC refresh tokens as equivalent to Steam Web cookies; they satisfy different runtime paths.
- Reporting a capture flow as safe without checking both behavior tests and a final sensitive-value scan.

## Verification

- Run focused service/API tests for the capture flow.
- Run `ruff check` on changed implementation and tests.
- Run `git diff --check`.
- Re-read tracked config and scan relevant tracked docs/config for cookie/token/password sentinels before handoff.
