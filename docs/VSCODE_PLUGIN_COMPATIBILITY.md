# VSCode Plugin Compatibility

Phase 1 core is ready for dogfooding through local scripts, Markdown files, skills, and review workflow. Before enabling the real recall/stop hooks in a VSCode-first workflow, verify that the VSCode-hosted agent actually executes local runtime hooks.

Use `scripts/hook_probe.py` as a temporary canary. It records hook payload shape only; it does not store prompt text, assistant text, raw transcripts, secrets, embeddings, or retrieval data.

## Config Locations

Codex official hook configuration should be tested through:

```text
~/.codex/hooks.json
```

Older Codex CLI setups may also have hook-related content in:

```text
~/.codex/config.toml
```

The Phase 1 canonical installer uses `~/.codex/hooks.json`. It warns about legacy config, but does not delete user config.

Claude Code VSCode shares settings with Claude Code CLI through:

```text
~/.claude/settings.json
```

This shared settings behavior still needs local verification because extension versions and launch paths can change.

Third-party VSCode agents, GitHub Copilot-hosted agents, and cloud-hosted coding agents may not execute local hook commands at all.

## Print Probe Config

Print a temporary Codex probe config:

```bash
python3 scripts/install_codex_hooks.py --probe
```

Print a temporary Claude probe config:

```bash
python3 scripts/install_claude_hooks.py --probe
```

These commands only print JSON. They do not overwrite existing hook config and do not install the real recall/stop hooks.

## Install Probe Hooks

Install probe hooks only when you are ready to test VSCode plugin compatibility. The installers back up existing config before writing:

```bash
python3 scripts/install_codex_hooks.py --probe --install
python3 scripts/install_claude_hooks.py --probe --install
```

Probe mode points both `UserPromptSubmit` and `Stop` to:

```text
scripts/hook_probe.py
```

It does not mix probe hooks with the real `scripts/recall.py` or `scripts/stop_trigger.py` hooks.

## Inspect The Log

The probe appends JSONL to:

```text
~/.agent-experience-ledger/hook-probe.log
```

Each line includes:

- `timestamp`
- `hook_event_name`
- `cwd`
- `session_id`
- `transcript_path_present`
- `prompt_present`
- `last_assistant_message_present`
- `stop_hook_active` when present
- `argv`
- `raw_keys`
- `json_parse_ok`

Inspect recent lines with:

```bash
tail -n 20 ~/.agent-experience-ledger/hook-probe.log
```

## Dogfood Procedure

1. Print the probe config and inspect it.
2. Run the matching `--probe --install` command.
3. Start a fresh Codex or Claude session from VSCode.
4. Send a small harmless prompt.
5. Stop the session normally.
6. Inspect `~/.agent-experience-ledger/hook-probe.log`.
7. Restore your backed-up hook config, or install canonical Phase 1 hooks later when you are ready.

## If Hooks Fire

If the log contains `UserPromptSubmit` and/or `Stop` lines, VSCode is executing local hook commands. Check which payload keys appear in `raw_keys`, then compare the presence flags with what `scripts/recall.py` and `scripts/stop_trigger.py` expect.

When satisfied, restore the previous config and install canonical hooks explicitly:

```bash
python3 scripts/install_codex_hooks.py --install
python3 scripts/install_claude_hooks.py --install
```

## If Hooks Do Not Fire

If no log lines appear after a fresh VSCode session:

1. Confirm the relevant config file was written and backed up.
2. Try the same probe through the Codex or Claude CLI.
3. Keep VSCode plugin usage hook-free until the host exposes local hook execution.
4. Use CLI agents for Phase 1 dogfooding.
5. Manually use the `experience-capture` skill for important sessions.

Do not add RAG, embeddings, vector databases, Qdrant, Redis runtime, network calls, or LLM calls as a workaround for missing local hook support.
