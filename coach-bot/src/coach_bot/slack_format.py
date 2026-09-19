"""Slack Block Kit helpers for coach messages."""

from __future__ import annotations

from typing import Any


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}


def briefing_blocks(
    title: str,
    hook: str,
    sections: list[tuple[str, str]],
    footer: str | None = None,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150], "emoji": True}},
        _section(hook),
        {"type": "divider"},
    ]
    for heading, body in sections:
        if not body.strip():
            continue
        blocks.append(_section(f"*{heading}*\n{body.strip()}"))
    if footer:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": footer[:2000]}]})
    return blocks


def week_preview_blocks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = []
    for ev in events[:14]:
        d = (ev.get("start_date_local") or "")[:10]
        name = ev.get("name") or "Økt"
        mins = ev.get("planned_duration")
        dur = f" · {int(mins) // 60} min" if mins else ""
        lines.append(f"• {d}: {name}{dur}")
    body = "\n".join(lines) if lines else "_Ingen økter i forslaget._"
    return briefing_blocks(
        "Forhåndsvisning – Intervals",
        "Svar *ja* eller *legg inn* for å opprette i kalenderen. Svar *avbryt* for å droppe.",
        [("Planlagte økter", body)],
    )


def single_workout_preview_blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    return week_preview_blocks([event])


def parse_brief_sections(llm_text: str) -> list[tuple[str, str]]:
    """Best-effort split LLM markdown into Block Kit sections."""
    sections: list[tuple[str, str]] = []
    current_title = "Coach"
    current_lines: list[str] = []
    for line in llm_text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = line[3:].strip()
            current_lines = []
        elif line.startswith("# "):
            continue
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    if not sections:
        sections.append(("Coach", llm_text))
    return sections[:6]
