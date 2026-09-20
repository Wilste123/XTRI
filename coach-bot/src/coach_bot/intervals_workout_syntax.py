"""Validate and estimate Intervals.icu native workout description text."""

from __future__ import annotations

import re
from dataclasses import dataclass

_STEP = re.compile(
    r"^\s*-\s*(\d+(?:\.\d+)?)\s*(m|min|h|km|k)\b",
    re.I,
)
_REPEAT = re.compile(r"^\s*(?:main\s+set\s+)?(\d+)\s*x\s*$", re.I)
_TARGET = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*(?:-\s*(\d+(?:\.\d+)?)\s*%)?\s*(HR|FTP|W|w|Pace|pace|Z\d)",
    re.I,
)
_ZONE = re.compile(r"\bZ[1-5]\b", re.I)
_DURATION_M = re.compile(r"(\d+(?:\.\d+)?)\s*(m|min)\b", re.I)
_DURATION_H = re.compile(r"(\d+(?:\.\d+)?)\s*h\b", re.I)


@dataclass
class SyntaxValidation:
    ok: bool
    errors: list[str]
    estimated_minutes: int
    step_lines: int


def _minutes_from_step_line(line: str) -> int:
    m = _STEP.match(line)
    if m:
        val = float(m.group(1))
        unit = m.group(2).lower()
        if unit in ("h",):
            return int(round(val * 60))
        if unit in ("km", "k"):
            return int(round(val * 5))  # rough placeholder for run
        return int(round(val))
    m = _DURATION_M.search(line)
    if m:
        return int(round(float(m.group(1))))
    m = _DURATION_H.search(line)
    if m:
        return int(round(float(m.group(1)) * 60))
    return 0


def estimate_workout_minutes(text: str) -> int:
    """Rough total duration from syntax (includes repeat blocks)."""
    if not text:
        return 0
    total = 0
    repeat = 1
    in_repeat = False
    block_mins = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rm = _REPEAT.match(line)
        if rm:
            if in_repeat and block_mins:
                total += repeat * block_mins
            repeat = int(rm.group(1))
            block_mins = 0
            in_repeat = True
            continue
        if line.startswith("-"):
            mins = _minutes_from_step_line(line)
            if in_repeat:
                block_mins += mins
            else:
                total += mins
            continue
        # Coach notes after blank line – stop counting
        if in_repeat and block_mins and not line.startswith("-"):
            total += repeat * block_mins
            in_repeat = False
            repeat = 1
            block_mins = 0
    if in_repeat and block_mins:
        total += repeat * block_mins
    return max(0, total)


def validate_workout_syntax(text: str, *, max_minutes: int = 240) -> SyntaxValidation:
    errors: list[str] = []
    if not (text or "").strip():
        return SyntaxValidation(False, ["Tom workout-tekst"], 0, 0)

    step_lines = 0
    has_target = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _REPEAT.match(line):
            continue
        if line.startswith("-"):
            step_lines += 1
            if not _STEP.match(line) and not _ZONE.search(line):
                errors.append(f"Steg uten gjenkjent varighet: {line[:60]}")
            if _TARGET.search(line) or _ZONE.search(line):
                has_target = True
            if re.search(r"\b(easy|recovery|rest|RPE)\b", line, re.I):
                has_target = True
        elif step_lines == 0 and not _REPEAT.match(line):
            continue

    if step_lines == 0:
        errors.append("Ingen steg-linjer (forventet linjer som «- 25m 65% HR»).")

    est = estimate_workout_minutes(text)
    if est > max_minutes:
        errors.append(f"Estimert varighet {est} min overstiger maks {max_minutes} min.")
    if step_lines > 0 and not has_target:
        errors.append("Ingen intensitetsmål (% HR/FTP/Z) – sett target for Intervals compile.")

    ok = len(errors) == 0 and step_lines > 0
    return SyntaxValidation(ok=ok, errors=errors, estimated_minutes=est, step_lines=step_lines)


def split_syntax_and_notes(description: str) -> tuple[str, str]:
    """Separate Intervals syntax block from free coach notes."""
    if not description:
        return "", ""
    lines = description.splitlines()
    syntax_lines: list[str] = []
    note_lines: list[str] = []
    in_notes = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if syntax_lines and not in_notes:
                in_notes = True
            continue
        if not in_notes and (
            stripped.startswith("-")
            or _REPEAT.match(stripped)
            or stripped.lower().startswith("main set")
        ):
            syntax_lines.append(line)
            continue
        in_notes = True
        note_lines.append(line)
    return "\n".join(syntax_lines).strip(), "\n".join(note_lines).strip()


def merge_event_description(syntax: str, coach_notes: str = "") -> str:
    syntax = (syntax or "").strip()
    notes = (coach_notes or "").strip()
    if syntax and notes:
        return f"{syntax}\n\n{notes}"
    return syntax or notes
