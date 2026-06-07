---
schema_version: "1"
title: "Dogfood hooks with an external temporary repo"
date: "2026-06-07"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["hooks", "testing", "dogfood", "agent-workflow"]
confidence: "high"
repo: "Agent_Experience_Ledger"
branch: "main"
capture_request_id: "capture-20260607-094534-019ea0e2-7f40-7c50-87f7--7fa743b5"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, private content, credentials, or secret values included."
---

## Summary

验证用户级 hooks 是否跨仓库生效时，可以在 ledger 仓库外创建一个临时 git repo，用手写 JSON payload 直接调用 hook 脚本，再检查返回 JSON 和本地审计记录。这个方法能在不依赖宿主真实会话生命周期的情况下，快速区分“hook 脚本能否跨目录执行”和“宿主是否真的触发了 hook”。

## Applies When

- 用户怀疑全局 hook 只在某个项目中生效。
- 刚安装或修改 `~/.codex/hooks.json`、`~/.claude/settings.json` 里的 hook command。
- 需要验证 `UserPromptSubmit` 和 `Stop` hook 的 fail-open 行为、阻断行为或审计记录。

## Evidence

- 在 ledger 仓库外创建临时目录 `/tmp/ael-hook-scope-test.fy1hRd` 并初始化为 git repo 后，直接调用 `scripts/recall.py`，传入 `cwd` 指向该临时 repo，返回了有效 JSON：`{"continue": true}`。
- 同一个临时 repo 中保留一个未跟踪文件，并直接调用 `scripts/stop_trigger.py`，传入包含 `bug`、`fixed`、`tests` 等关键词的停止事件摘要，返回了 `decision: block` 和新的 `capture_request_id`。
- 本地 stop-trigger 审计记录包含该临时 repo 的 `cwd`、`repo_root`、`repo_name`、`changed_files_count`、`score` 和 `reason_code: threshold_met`，证明验证结果来自外部仓库上下文。

## Lesson

未来排查 hook 作用域时，优先构造一个仓库外的最小 git fixture，并直接给 hook 脚本喂入代表性 payload。`recall.py` 是否返回 continue、`stop_trigger.py` 是否按预期 block/continue、审计记录是否包含外部 `cwd`，三者合起来比单看配置文件更能说明系统真实行为。

## Avoid

- 只看 `~/.codex/hooks.json` 或 `~/.claude/settings.json` 就断言运行时行为已经正确。
- 只在当前仓库里测试 hook，然后把结果泛化到全局作用域。
- 把宿主没有触发 hook、payload 字段缺失、hook 脚本逻辑错误混成同一个问题。

## Verification

- 用 `mktemp -d` 创建 ledger 仓库外的临时目录，并用 `git init` 让 `stop_trigger.py` 能读取 repo 信号。
- 给临时 repo 制造一个小改动，再通过 stdin 向 `scripts/recall.py` 和 `scripts/stop_trigger.py` 分别传入 JSON payload。
- 检查 stdout 是有效 JSON，并确认本地 stop-trigger 审计记录中的最新条目指向该临时 repo。
