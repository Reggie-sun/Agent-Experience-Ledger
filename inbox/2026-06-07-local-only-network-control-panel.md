---
schema_version: "1"
title: "Keep local network control panels behind a fixed-action localhost helper"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "architecture"
tags: ["local-tools", "networking", "security", "testing"]
confidence: "high"
repo: "VPN"
branch: "unknown"
capture_request_id: "capture-20260607-083558-019ea107-a245-7e53-9662--c7067a40"
source_repo: "VPN"
source_cwd: "/home/reggie/vscode_folder/VPN"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, subscription URL, proxy token, node credential, or private key included."
---

## Summary

When building a browser control panel for a local proxy/VPN runtime, use a static UI plus a localhost-only helper API with fixed, allowlisted actions. This keeps the panel useful for status checks and controlled operations without exposing arbitrary shell execution or committing machine-specific secrets.

## Applies When

- A local dashboard needs to inspect or control system services, network interfaces, proxy groups, or connectivity checks.
- The project is intended to be reusable on another machine or uploaded to a public repository.
- Browser code cannot safely or directly run local commands such as `systemctl`, `ip`, `journalctl`, `curl`, or `git`.

## Evidence

- Implemented `mihomo-runtime/panel/server.py` as a Python standard-library helper bound to `127.0.0.1`.
- The helper exposes only fixed endpoints for status, proxy switching, fixed validation checks, and recent logs.
- Static UI files live under `mihomo-runtime/panel/static/` and do not embed subscription URLs or node credentials.
- Verification ran with `/usr/bin/python3 -m unittest discover -s mihomo-runtime/panel/tests -v`, `server.py --self-test`, direct `/api/status`, and a browser smoke test of the backup-IP button.

## Lesson

For local infrastructure dashboards, separate presentation from privileged local inspection. Keep the UI static and portable, put host-specific operations in a small localhost helper, and make the helper expose only named operations with constrained inputs. Add tests around parsing and response helpers before expanding UI behavior.

## Avoid

- Do not let a browser panel accept arbitrary shell commands.
- Do not bind the helper to a public interface by default.
- Do not commit generated runtime files, diagnostics, captures, subscription URLs, API secrets, proxy passwords, or WireGuard private keys.
- Do not trust proxy validation unless old `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` environment variables are cleared for checks.

## Verification

- Run unit tests for helper parsing and JSON response behavior.
- Run the helper self-test to verify service, TUN, WireGuard, and proxy-group state.
- Smoke-test the browser UI by loading the panel, checking rendered status, switching to the backup proxy for one IP check, and confirming it returns to the main proxy choice.
