# Memory Schema

Experience memories are Markdown files with YAML-like frontmatter and fixed body sections.

## Required Frontmatter

```yaml
---
schema_version: "1"
title: "Short reusable engineering lesson"
date: "2026-06-05"
source_agent: "codex"
status: "candidate"
category: "hooks"
tags: ["testing", "hooks"]
confidence: "medium"
repo: "example-repo"
branch: "feature/example"
privacy:
  contains_raw_transcript: false
  contains_secrets: false
  redaction_notes: "No raw transcript or secrets included."
---
```

## Required Body Sections

```markdown
## Summary

One concise paragraph describing the reusable lesson.

## Applies When

- Concrete trigger or situation.

## Evidence

- Concrete code, test, debugging, or review evidence behind the lesson.

## Lesson

What future agents should do differently.

## Avoid

- Mistake or false shortcut to avoid.

## Verification

- Check that proves the lesson applies or the fix worked.
```
