"""Compact Slack message composition (less markdown noise)."""

from __future__ import annotations

import re
from typing import Any

from coach_bot.coach_reply import CoachReply

_MAX_LINES = 15
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_HEADERS = re.compile(r"^\*\*[^*]+\*\*\s*$", re.MULTILINE)

# Setninger der modellen fornekter egne evner eller ber om manuell Intervals-bruk.
# Slike linjer er feil (boten KAN skrive til Intervals og lage grafer) og fjernes.
_SELF_DENIAL = re.compile(
    r"(kan\s+ikke\s+(direkte\s+)?(legge?\s+inn|opprette|skrive|synke?)"
    r"|kan\s+ikke\s+(lage|vise|generere|tilby|gi\s+deg)\s+(en\s+)?"
    r"(visuell|visuelle|visuelt|grafisk|grafer|graf|figur|diagram|fremstilling|bilde|illustrasjon)"
    r"|f[åa]r\s+ikke\s+lagt\s+inn"
    r"|m[åa]\s+(du\s+)?(selv\s+)?(logge?\s+inn|gj[øo]re\s+det\s+manuelt)"
    r"|manuelt\s+i\s+intervals"
    r"|logg\s+inn\s+p[åa]\s+intervals"
    r"|g[åa]\s+(inn\s+)?(til|p[åa])\s+intervals"
    r"|beklager\s+misforst[åa]elsen)",
    re.IGNORECASE,
)

# Falske påstander om at boten allerede utfører skrivingen «nå» (den gjør det
# først etter bekreftelse). Fjernes så modellen ikke lyver om handling.
_FALSE_ACTION = re.compile(
    r"(jeg\s+legger\s+(dem|den|disse|inn|[øo]ktene).*\bn[åa]\b"
    r"|legger\s+(den|dem|disse)\s+inn\s+n[åa]"
    r"|(jeg|la\s+meg)\s+begynne?r?\s+med\s+[åa]\s+legge\s+inn"
    r"|gi\s+meg\s+et\s+[øo]yeblikk)",
    re.IGNORECASE,
)
_CAPABILITY_TRUTH = (
    "Jeg kan legge øktene rett inn i Intervals for deg – si «ja» eller «legg dem inn», "
    "så ordner jeg det."
)


def strip_self_denial(text: str) -> str:
    """Remove lines where the model wrongly denies its abilities or falsely
    claims it is performing the write right now.

    The coach can create calendar events and attach charts, so a reply must
    never say it cannot, tell William to do it manually, or pretend it already
    saved something. If stripping leaves nothing meaningful, fall back to the
    truthful capability line; otherwise make sure the real affordance is shown.
    """
    if not text:
        return text
    kept: list[str] = []
    stripped_any = False
    for ln in text.splitlines():
        if _SELF_DENIAL.search(ln) or _FALSE_ACTION.search(ln):
            stripped_any = True
            continue
        kept.append(ln)
    out = "\n".join(kept).strip()
    if len(out) < 15:
        return _CAPABILITY_TRUTH
    if stripped_any and "legg" not in out.lower() and _CAPABILITY_TRUTH not in out:
        out = f"{out}\n\n{_CAPABILITY_TRUTH}"
    return out


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


def natural_reply(text: str, max_lines: int = 24) -> CoachReply:
    """Coach's own voice: plain, mentor-like DM text with no title-card blocks.

    Used for conversational answers so they read like a real person texting,
    not a templated report. Self-denials are scrubbed so the bot never claims
    it cannot do something it actually can.
    """
    body = sanitize_for_slack(strip_self_denial(text or ""), max_lines=max_lines)
    if not body:
        body = "Jeg er her – hva vil du ta tak i?"
    return CoachReply(text=body[:3900], blocks=None)
