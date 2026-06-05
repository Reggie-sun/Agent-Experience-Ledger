---
schema_version: "1"
title: "Separate capability verification from live account state"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "verification"
tags: ["verification", "auth-secret", "status-reporting"]
confidence: "high"
repo: "csgojiaoben"
branch: "master"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, cookie values, tokens, passwords, or live credential material included."
---

## Summary

When implementing credential capture or account-linking features, report two separate truths: whether the code path is implemented and tested, and whether the real local account state has actually been populated. Passing tests for a capture route does not mean a real browser login cookie has been captured.

## Applies When

- Adding login, cookie capture, token bootstrap, or account-linking functionality.
- Answering whether a live account is "linked" after backend implementation work.
- Reviewing config files that store credential references rather than credential values.

## Evidence

- The Steam Web cookie capture service and API tests passed, proving the backend can save account-scoped cookie files safely.
- A follow-up state check of `config.yaml` and `data/purchase_accounts/` showed purchase accounts had BUFF cookie files but empty Steam Web cookie file references.
- The safe answer was that the capability was verified, but the real Steam Web cookie capture had not yet been performed.

## Lesson

Future agents should distinguish implementation verification from live-state verification in final answers. For secret-bearing flows, inspect only non-secret indicators such as configured paths, file existence, cookie names, counts, or redacted status fields.

## Avoid

- Saying a real account is linked just because unit or API tests passed.
- Reading or printing live cookie values to prove linkage.
- Collapsing "the endpoint works" and "the user's current account has been captured" into one claim.

## Verification

- Run the focused tests that prove the capability.
- Then separately inspect safe live-state signals such as `steam_cookie_file` being non-empty and an account-private cookie file existing.
- State both outcomes explicitly in the handoff.
