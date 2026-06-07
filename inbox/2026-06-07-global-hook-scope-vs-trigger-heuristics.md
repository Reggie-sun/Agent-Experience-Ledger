---
schema_version: "1"
title: "Separate global hook scope from repo-specific trigger heuristics"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["hooks", "skills", "agent-workflow", "installation"]
confidence: "high"
repo: "Agent_Experience_Ledger"
branch: "main"
capture_request_id: "capture-20260607-094353-019ea0e2-7f40-7c50-87f7--4a9716bb"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, private content, credentials, or secret values included."
---

## Summary

当一个 agent skill 或 hook 看起来“只在某个项目里会触发”时，先把“安装作用域”和“触发启发式”拆开检查。全局用户级 hooks 往往会在所有仓库生效，而某个项目之所以更常触发，可能只是因为当前 `Stop` 判定关键词、变更形态或会话内容更容易命中。

## Applies When

- 用户怀疑某个 hook、skill 或 recall 只在单个仓库生效。
- 你刚安装了用户级 `~/.codex/hooks.json`、`~/.claude/settings.json` 或全局 skill 目录配置。
- 某个项目频繁触发 capture / recall，导致人误以为系统被仓库名硬编码。

## Evidence

- `scripts/install_global.py` 将 `experience-capture` 复制到 `~/.agents/skills/experience-capture/SKILL.md` 和 `~/.claude/skills/experience-capture/SKILL.md`，说明 skill 安装目标是全局目录而不是当前仓库局部目录。
- `scripts/install_codex_hooks.py` 将 canonical hooks 合并写入 `~/.codex/hooks.json`，`scripts/install_claude_hooks.py` 将 hooks 合并写入 `~/.claude/settings.json`，说明 hooks 作用域是用户级配置。
- `scripts/install_helpers.py` 生成的 hook command 只指向 ledger 仓库里的 `scripts/recall.py` 与 `scripts/stop_trigger.py` 绝对路径，没有仓库白名单判断。
- `scripts/recall.py` 和 `scripts/stop_trigger.py` 都是基于 hook payload 中的 `cwd`、repo、branch、改动情况和关键词做动态判断；其中 `stop_trigger.py` 的 `KEYWORDS` 包含 `rag`、`memory`、`agent` 等词，所以 RAG 类工作更容易命中，但这不等于 scope 被限制在 RAG 仓库。

## Lesson

未来遇到“似乎只在某项目触发”的现象时，先验证配置写入位置是否是用户级，再检查 runtime 逻辑是否只是根据 payload 做评分。把安装范围、调用入口和启发式判定拆开看，通常能更快判断问题是 scope 限制、配置遗漏，还是触发条件偏置。

## Avoid

- 仅凭某个仓库更常出现 hook 行为，就推断脚本里存在 repo-specific hardcode。
- 在没有读安装脚本和 hook 入口前，把“触发频率偏置”误判成“部署范围错误”。
- 为了排查作用域问题而复制或重装一套局部配置，结果制造重复 hooks。

## Verification

- 检查 hooks 是否写入 `~/.codex/hooks.json`、`~/.claude/settings.json` 等用户级配置，而不是单仓库文件。
- 阅读安装脚本的目标路径和 merge 逻辑，确认是否存在 repo allowlist 或 path guard。
- 阅读 hook 入口脚本，确认 repo 名、branch、cwd 是作为 payload 输入参与评分，而不是被硬编码为唯一允许的项目。
- 用一个非目标仓库目录模拟或实测 `UserPromptSubmit` / `Stop` payload，确认 hooks 仍会执行。
