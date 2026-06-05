---
schema_version: "1"
title: "Treat VS Code prompt diagnostics as advisory until sourced"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "agent-workflow"
tags: ["agent-workflow", "hooks", "diagnostics", "vscode"]
confidence: "high"
repo: "Enterprise-grade_RAG"
branch: "main"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript, private content, credentials, or secret values included."
---

## Summary

当 `AGENTS.md` 在 VS Code Problems 面板出现大量 cognitive-load、ambiguity 或 coverage 提示时，先确认 diagnostic `source`。如果来源是 `chat-customizations-evaluations` 这类 prompt customization analyzer，它通常是在做提示词质量建议，不代表仓库 hook、harness 或 policy 真的失败。

## Applies When

- VS Code Problems 面板标记 `AGENTS.md`、skill、prompt 或 instructions 文件。
- 用户怀疑 hooks、repo policy 或 `AGENTS.md` 之间存在冲突。
- 仓库明确把人类可读规则和机器可读规则分层存放，例如 `AGENTS.md` 只承载 workflow 合同，而 `.agent/harness/policy.yaml` 承载 lane、mandatory reads 和 checks。

## Evidence

- `Enterprise-grade_RAG/AGENTS.md` 明确说明 `AGENTS.md` 是 workflow / control-plane 的顶层人类可读合同，不是唯一承载信息的文件，也不是机器真源的替代品。
- 同一文件还声明 `.agent/harness/policy.yaml` 负责文件分类、lane 触发、mandatory reads、recommended checks 和 harness smoke 入口。
- 本地 VS Code 扩展 `ms-vscode.vscode-chat-customizations-evaluations-1.0.6/package.json` 将该扩展描述为用于 analyzing、validating、improving AI prompts，并把 `AGENTS.md` 纳入可分析文件。
- 该扩展文档说明它会把 LLM 分析类别转换成 VS Code diagnostics 并发布到 Problems 面板。

## Lesson

未来 agent 看到 `AGENTS.md` 的 Problems 时，应先按 `source` 判断诊断来源，再对照仓库的规则 ownership。prompt-linter 建议可以用来修复清晰的文档问题，例如编号跳跃或术语不够明确；但不应因此把已经下沉到 `policy.yaml`、playbook 或 repo-local skill 的机器规则重新塞回 `AGENTS.md`。

## Avoid

- 把 Problems 面板里的 prompt analyzer 提示误判成 hook 执行失败。
- 为了消除 coverage warning，把仓库已经分层管理的机器规则复制回 `AGENTS.md`，制造第二套规则源。
- 因为诊断来源是 advisory 就忽略明显的小缺陷，例如优先级列表编号错误或高频短语缺少就近定义。

## Verification

- 检查每条 Problem 的 `source` 字段，确认它来自 repo hook、language server、extension，还是测试命令。
- 读取 `AGENTS.md` 中的 source ownership 段落，并确认是否存在对应的机器真源文件，例如 `.agent/harness/policy.yaml`。
- 必要时读取 VS Code extension 的 `package.json` 或用户指南，确认该 diagnostic 是否只是 prompt customization analysis。
