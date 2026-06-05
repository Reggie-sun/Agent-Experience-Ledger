#!/usr/bin/env python3
"""Shared helpers for Agent Experience Ledger Phase 1."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1"
MAX_CONTEXT_CHARS = 9000
DEFAULT_TOP_K = 5

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "code",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "then",
    "this",
    "to",
    "use",
    "was",
    "we",
    "when",
    "with",
    "you",
    "your",
}

SECRET_PATTERNS = [
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-(?:proj|svcacct)?-?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss)://[^\s\"'<>]+"),
    re.compile(r"(?m)^[A-Z][A-Z0-9_]{1,80}\s*=\s*[^\n#]{4,}$"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd|credential|client[_-]?secret|"
        r"access[_-]?key|access[_-]?token|refresh[_-]?token)\b"
        r"\s*[:=]\s*['\"]?[^'\"\s]{6,}"
    ),
]


@dataclass(frozen=True)
class MemoryMatch:
    path: Path
    score: int
    title: str
    tags: list[str]
    summary: str
    lesson: str
    applies_when: str
    verification: str


def ledger_root() -> Path:
    configured = os.environ.get("AGENT_EXPERIENCE_LEDGER_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def today_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


def read_json_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def emit_json(value: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False) + "\n")


def continue_response() -> dict[str, Any]:
    return {"continue": True}


def fail_open(main: Any) -> int:
    try:
        result = main()
        if result is not None:
            emit_json(result)
        return 0
    except Exception as exc:  # pragma: no cover - defensive hook boundary
        if os.environ.get("AGENT_EXPERIENCE_LEDGER_DEBUG"):
            print(f"agent-experience-ledger hook failed open: {exc}", file=sys.stderr)
        emit_json(continue_response())
        return 0


def run_git(cwd: Path, args: list[str], timeout: float = 2.0) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def cwd_from_payload(payload: dict[str, Any]) -> Path:
    raw = payload.get("cwd") or os.getcwd()
    try:
        return Path(str(raw)).expanduser().resolve()
    except OSError:
        return Path.cwd()


def repo_name(cwd: Path) -> str:
    top = run_git(cwd, ["rev-parse", "--show-toplevel"])
    if top:
        return Path(top).name
    return cwd.name


def branch_name(cwd: Path) -> str:
    return run_git(cwd, ["branch", "--show-current"]) or "unknown"


def changed_files(cwd: Path) -> list[str]:
    status = run_git(cwd, ["status", "--short"])
    files: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        name = line[3:].strip()
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        files.append(name)
    return files


def diff_stat(cwd: Path) -> str:
    return run_git(cwd, ["diff", "--stat", "HEAD"], timeout=3.0)


def prompt_from_payload(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_prompt", "message", "input"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                content = message.get("content")
                if isinstance(content, str):
                    return content
    return ""


def source_agent(payload: dict[str, Any]) -> str:
    explicit = os.environ.get("AGENT_EXPERIENCE_LEDGER_AGENT")
    if explicit in {"codex", "claude"}:
        return explicit
    executable = Path(sys.argv[0]).name.lower()
    event = str(payload.get("hook_event_name", "")).lower()
    if "claude" in executable or "claude" in event:
        return "claude"
    if "codex" in executable or "codex" in event:
        return "codex"
    return "unknown"


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", text.lower())
    normalized: list[str] = []
    for token in tokens:
        for part in re.split(r"[-_]", token):
            if len(part) > 1 and part not in STOPWORDS:
                normalized.append(part)
        if token not in STOPWORDS:
            normalized.append(token)
    return normalized


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "false"}:
        return value == "true"
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return [part.strip().strip('"').strip("'") for part in value[1:-1].split(",") if part.strip()]
    return value


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")
    data: dict[str, Any] = {}
    current_map: dict[str, Any] | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  ") and current_map is not None and ":" in line:
            key, value = line.strip().split(":", 1)
            current_map[key.strip()] = parse_scalar(value)
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = parse_scalar(value)
            current_map = None
        else:
            nested: dict[str, Any] = {}
            data[key] = nested
            current_map = nested
    return data, body


def quote_yaml(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_frontmatter(data: dict[str, Any]) -> str:
    order = [
        "schema_version",
        "title",
        "date",
        "source_agent",
        "status",
        "category",
        "tags",
        "confidence",
        "repo",
        "branch",
        "privacy",
        "reviewed_at",
        "reviewer",
        "rejection_reason",
    ]
    lines = ["---"]
    for key in order:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, list):
            encoded = ", ".join(quote_yaml(str(item)) for item in value)
            lines.append(f"{key}: [{encoded}]")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for subkey, subvalue in value.items():
                if isinstance(subvalue, bool):
                    lines.append(f"  {subkey}: {'true' if subvalue else 'false'}")
                else:
                    lines.append(f"  {subkey}: {quote_yaml(str(subvalue))}")
        else:
            lines.append(f"{key}: {quote_yaml(str(value))}")
    for key, value in data.items():
        if key in order:
            continue
        lines.append(f"{key}: {quote_yaml(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def extract_section(body: str, name: str) -> str:
    pattern = re.compile(rf"^## {re.escape(name)}\s*$", re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^## .+$", body[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(body)
    return body[start:end].strip()


def load_memory(path: Path) -> MemoryMatch | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    frontmatter, body = split_frontmatter(text)
    if frontmatter.get("status") != "promoted":
        return None
    title = str(frontmatter.get("title") or path.stem)
    tags = frontmatter.get("tags")
    tag_list = [str(tag) for tag in tags] if isinstance(tags, list) else []
    return MemoryMatch(
        path=path,
        score=0,
        title=title,
        tags=tag_list,
        summary=extract_section(body, "Summary"),
        lesson=extract_section(body, "Lesson"),
        applies_when=extract_section(body, "Applies When"),
        verification=extract_section(body, "Verification"),
    )


def memory_search_text(memory: MemoryMatch) -> str:
    return " ".join(
        [
            memory.title,
            " ".join(memory.tags),
            memory.summary,
            memory.applies_when,
            memory.lesson,
            memory.verification,
        ]
    )


def score_memory(memory: MemoryMatch, query_tokens: set[str]) -> int:
    if not query_tokens:
        return 0
    text_tokens = tokenize(memory_search_text(memory))
    if not text_tokens:
        return 0
    counts: dict[str, int] = {}
    for token in text_tokens:
        counts[token] = counts.get(token, 0) + 1
    score = 0
    for token in query_tokens:
        if token in counts:
            score += min(counts[token], 3)
    title_tokens = set(tokenize(memory.title))
    tag_tokens = set(tokenize(" ".join(memory.tags)))
    score += 3 * len(query_tokens & title_tokens)
    score += 4 * len(query_tokens & tag_tokens)
    return score


def find_relevant_memories(query: str, top_k: int = DEFAULT_TOP_K) -> list[MemoryMatch]:
    root = ledger_root()
    query_tokens = set(tokenize(query))
    matches: list[MemoryMatch] = []
    for path in sorted((root / "memories").glob("**/*.md")):
        memory = load_memory(path)
        if memory is None:
            continue
        score = score_memory(memory, query_tokens)
        if score > 0:
            matches.append(
                MemoryMatch(
                    path=memory.path,
                    score=score,
                    title=memory.title,
                    tags=memory.tags,
                    summary=memory.summary,
                    lesson=memory.lesson,
                    applies_when=memory.applies_when,
                    verification=memory.verification,
                )
            )
    matches.sort(key=lambda item: (-item.score, item.path.name))
    return matches[:top_k]


def compact_text(text: str, limit: int = 700) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def format_memory_context(matches: list[MemoryMatch]) -> str:
    if not matches:
        return ""
    root = ledger_root()
    blocks = ["Relevant prior experience:"]
    for index, memory in enumerate(matches, start=1):
        relpath = memory.path.relative_to(root)
        tags = ", ".join(memory.tags) if memory.tags else "untagged"
        blocks.append(
            "\n".join(
                [
                    f"{index}. {memory.title} ({relpath})",
                    f"   Tags: {tags}",
                    f"   Lesson: {compact_text(memory.lesson, 320)}",
                    f"   Evidence: {compact_text(memory.verification, 220)}",
                ]
            )
        )
    output = "\n\n".join(blocks)
    return output[:MAX_CONTEXT_CHARS]


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80] or "memory"


def required_sections() -> list[str]:
    return ["Summary", "Applies When", "Evidence", "Lesson", "Avoid", "Verification"]


def validate_memory_text(text: str, expected_statuses: Iterable[str] | None = None) -> list[str]:
    errors: list[str] = []
    frontmatter, body = split_frontmatter(text)
    expected = set(expected_statuses or {"candidate", "promoted", "rejected"})
    required_keys = [
        "schema_version",
        "title",
        "date",
        "source_agent",
        "status",
        "category",
        "tags",
        "confidence",
        "privacy",
    ]
    for key in required_keys:
        if key not in frontmatter:
            errors.append(f"missing frontmatter key: {key}")
    if frontmatter.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be \"1\"")
    if frontmatter.get("status") not in expected:
        errors.append(f"status must be one of: {', '.join(sorted(expected))}")
    category = str(frontmatter.get("category") or "")
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,39}$", category):
        errors.append("category must be a lowercase slug")
    confidence = str(frontmatter.get("confidence") or "")
    if confidence not in {"low", "medium", "high"}:
        errors.append("confidence must be low, medium, or high")
    tags = frontmatter.get("tags")
    if not isinstance(tags, list) or not tags:
        errors.append("tags must be a non-empty inline list")
    privacy = frontmatter.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be a nested map")
    else:
        if privacy.get("contains_raw_transcript") is not False:
            errors.append("privacy.contains_raw_transcript must be false")
        if privacy.get("contains_secrets") is not False:
            errors.append("privacy.contains_secrets must be false")
    for section in required_sections():
        if not extract_section(body, section):
            errors.append(f"missing body section: ## {section}")
    if re.search(r"(?i)\btranscript_path\b", text):
        errors.append("memory must not include transcript_path")
    if contains_secret(text):
        errors.append("memory appears to contain a secret")
    return errors


def update_memory_status(path: Path, status: str, extra: dict[str, str] | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    frontmatter["status"] = status
    frontmatter["reviewed_at"] = now_utc()
    if extra:
        frontmatter.update(extra)
    path.write_text(format_frontmatter(frontmatter) + body, encoding="utf-8")


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=description)
