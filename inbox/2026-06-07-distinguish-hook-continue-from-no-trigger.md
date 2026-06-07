---
schema_version: "1"
title: "Distinguish hook continue decisions from missing triggers"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["hooks", "diagnostics", "agent-workflow", "testing"]
confidence: "high"
repo: "Agent_Experience_Ledger"
branch: "main"
capture_request_id: "capture-20260607-095032-019ea0e2-7f40-7c50-87f7--3989abda"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, private content, credentials, or secret values included."
---

## Summary

当用户说某些项目“完全没有触发”hook 时，不要直接把它解释成 hook 没执行。先查本地 stop-trigger 审计记录：如果项目目录已经出现，并且记录是 `decision: continue`，问题通常是触发策略没有达到阻断条件，而不是全局 hook 安装或宿主调用失败。

## Applies When

- 用户体感上认为某个项目没有触发 Agent Experience Ledger。
- `Stop` hook 只有在返回 `decision: block` 时才会显示显性的 capture 提示。
- 需要判断问题属于安装范围、宿主调用、payload 信号缺失，还是启发式门槛过高。

## Evidence

- 审计聚合显示 `Agent_Experience_Ledger` 有 `continue: 3` 和 `block: 2`，`Enterprise-grade_RAG` 有 `continue: 7` 和 `block: 1`，`VPN` 有 `continue: 19` 和 `block: 1`，说明多个项目都运行过 `Stop` hook。
- `VPN` 多数记录的 `inside_git_repo` 为 false、`changed_files_count` 为 0，缺少 git repo 和 diff 信号，所以分数通常偏低。
- `Enterprise-grade_RAG` 多次记录有 git 改动信号但仍然 `continue`，原因码多为 `no_current_turn_signal`，说明当前停止事件摘要没有命中 `stop_trigger.py` 的关键词门槛。
- `scripts/stop_trigger.py` 的 `decide` 逻辑先检查 active-loop，再要求当前回合关键词命中；没有关键词时会直接 `continue`，即使其他信号分数很高。

## Lesson

未来排查“没触发”时，先按三层拆开：项目是否出现在审计记录里，出现后是 `block` 还是 `continue`，`continue` 的 `reason_code` 是缺关键词、低分、active-loop，还是缺少 git 信号。这样能快速判断该改配置、重启宿主、调整 payload 兼容性，还是优化 `Stop` 的启发式。

## Avoid

- 把没有弹出 capture 提示等同于 hook 没有运行。
- 只看用户体感，不查审计记录中的 `cwd`、`decision`、`reason_code` 和 git 信号。
- 在 `no_current_turn_signal` 占多数时反复重装 hooks；真正需要评估的是关键词门槛是否过窄。

## Verification

- 按 `cwd` 聚合本地 stop-trigger 审计记录，统计每个项目的 `block` / `continue` 数量。
- 对 `continue` 记录继续聚合 `reason_code`，确认是 `no_current_turn_signal`、`below_threshold` 还是 `stop_hook_active`。
- 对照 `scripts/stop_trigger.py` 中的关键词集合、git 信号评分和阈值逻辑，解释为什么某个项目没有弹出 capture 提示。
