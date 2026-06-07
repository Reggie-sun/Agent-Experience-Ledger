---
schema_version: "1"
title: "Throttle self-dogfood capture loops in ledger repos"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["hooks", "dogfood", "observability", "agent-workflow"]
confidence: "high"
repo: "Agent_Experience_Ledger"
branch: "main"
capture_request_id: "capture-20260607-100543-019ea0e2-7f40-7c50-87f7--e73d6ea5"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, private content, credentials, or secret values included."
---

## Summary

当 ledger 仓库正在 dogfood 自己的 hooks 时，`Stop` capture 需要额外的节流和降噪规则。讨论 hook、memory、agent 等系统词本身会持续命中关键词；同时每次写入 `inbox/` 又会让工作区保持 dirty，于是系统容易把一次诊断会话拆成多次高分 capture。

## Applies When

- 当前仓库就是 Agent Experience Ledger 或类似的 memory / hook 项目。
- 会话主题是在解释、调试或 brainstorm hook 行为本身。
- 最近改动主要是新增 candidate memory，而不是产品代码、测试代码或新的工程决策。

## Evidence

- 本地审计摘要显示同一个 `Agent_Experience_Ledger` 会话连续多次达到 `threshold_met`，每次都要求写新的 candidate。
- 这些触发发生在同一轮 dogfood 讨论中，工作区持续包含多个 `inbox/` 新文件，因此 git 改动信号始终存在。
- brainstorm 梳理发现 `scripts/stop_trigger.py` 当前只检查 active-loop、关键词命中和总分阈值，没有 session cooldown、同主题去重、或 ledger 自身诊断降噪。
- 用户明确观察到“这个窗口一直在触发”，说明当前启发式在自我观察场景下用户体验过于敏感。

## Lesson

未来优化 lifecycle hooks 时，要为 self-dogfood 场景单独设计抑制规则：同一 session 短时间内已写过 candidate 时进入 cooldown；只改 `inbox/` 且主题仍是 hook 诊断时默认放行；同主题候选已存在时优先建议合并或不再创建。这样既保留真实工程经验捕获，又避免 memory 系统把调试自身的过程无限拆分。

## Avoid

- 把“讨论 hooks 本身”产生的关键词命中等同于每一轮都有新的可复用工程经验。
- 只依赖 dirty worktree 和关键词分数来判断 capture 价值。
- 在没有 cooldown 或去重的情况下，让 candidate 写入本身继续提高下一次 capture 的触发概率。

## Verification

- 用本地审计摘要确认同一 session 中连续 block 的次数、间隔和 `reason_code`。
- 检查 git 状态，确认新增改动是否主要集中在 `inbox/` candidate files。
- 为 `scripts/stop_trigger.py` 增加覆盖 self-dogfood、inbox-only changes、same-session cooldown、same-topic candidate exists 的回归测试。
