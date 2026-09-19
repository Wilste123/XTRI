"""Compact Slack message composition (less markdown noise)."""

from __future__ import annotations

import re
from typing import Any

from coach_bot.coach_reply import CoachReply

_MAX_LINES = 15
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_HEADERS = re.compile(r"^\*\*[^*]+\*\*\s*$", re.MULTILINE)


def sanitize_for_slack(text: str, max_lines: int = _MAX_LINES) -> str:
    """Flatten LLM markdown for readable DM text."""
    if not text:
        return ""
    out = text.replace("\r\n", "\n")
    out = _HEADING.sub("", out)
    lines: list[str] = []
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if _BOLD_HEADERS.match(stripped):
            title = stripped.strip("*").strip()
            if title:
                lines.append(f"*{title}*")
            continue
        stripped = re.sub(r"^\s*[-*]\s+", "• ", stripped)
        stripped = re.sub(r"^\s*\d+\.\s+", "• ", stripped)
        lines.append(stripped)
    compact: list[str] = []
    for line in lines:
        if line == "" and compact and compact[-1] == "":
            continue
        compact.append(line)
    if len(compact) > max_lines:
        compact = compact[:max_lines] + ["…"]
    return "\n".join(compact).strip()


def extract_action_line(text: str) -> str | None:
    for line in text.splitlines():
        lower = line.lower().strip()
        if lower.startswith("neste:") or lower.startswith("neste steg"):
            return line.strip()
    return None


def compact_reply(
    title: str,
    llm_or_body: str,
    *,
    action_line: str | None = None,
) -> CoachReply:
    """Build CoachReply with at most a few Block Kit blocks."""
    body = sanitize_for_slack(llm_or_body)
    action = action_line or extract_action_line(llm_or_body)
    hook = body.split("\n", 1)[0][:220] if body else title
    section_body = body
    if action and action in section_body:
        section_body = section_body.replace(action, "").strip()

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150], "emoji": True}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": section_body[:2900] or hook},
        },
    ]
    if action:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": action[:2000]}],
            }
        )
    fallback = body if body else hook
    if action and action not in fallback:
        fallback = f"{fallback}\n{action}".strip()
    return CoachReply(text=fallback[:3900], blocks=blocks)


def compact_system_message(title: str, body: str, footer: str | None = None) -> CoachReply:
    """Deterministic bot messages (preview, confirmations)."""
    return compact_reply(title, body, action_line=footer)
