"""Parse proposed workouts from chat text for Intervals events."""

from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Any

from coach_bot.intervals_planner import _detect_type

_WRITE_ACTION = re.compile(
    r"(legg\s+den\s+inn|legge\s+den\s+inn|legg\s+inn|legge\s+inn|legg\s+til|"
    r"opprett|putt\s+den|synk\s+den|i\s+intervals|i\s+intervalls)",
    re.I,
)

_COMMIT_EXACT = frozenset(
    {
        "ja",
        "yes",
        "ok",
        "gjør det",
        "gjør",
        "bekreft",
        "legg inn",
    }
)


def wants_intervals_write(message: str) -> bool:
    lower = (message or "").lower().strip()
    if lower in _COMMIT_EXACT:
        return True
    if _WRITE_ACTION.search(lower):
        return True
    if "intervals" in lower or "intervalls" in lower:
        if any(w in lower for w in ("legg", "legge", "den", "opprett", "sett")):
            return True
    return False


def is_commit_message(message: str) -> bool:
    lower = (message or "").lower().strip()
    if lower in _COMMIT_EXACT:
        return True
    if "legg den inn" in lower or "legge den inn" in lower:
        return True
    if "legg den" in lower and ("interval" in lower or len(lower) < 40):
        return True
    return False


def asks_workout_for_calendar(message: str) -> bool:
    """User wants coach to plan/create a calendar workout (often tomorrow)."""
    lower = (message or "").lower()
    has_workout = any(w in lower for w in ("økt", "okt", "workout", "trening", "intervall"))
    has_action = any(
        w in lower for w in ("legg", "legge", "opprett", "kan du", "sette", "lage", "planlegg")
    )
    has_when = any(w in lower for w in ("i morgen", "imorgen", "tomorrow", "kalender"))
    has_intervals = "intervals" in lower or "intervalls" in lower
    return has_workout and has_action and (has_when or has_intervals)


def _parse_minutes(text: str) -> int:
    lower = text.lower()
    m = re.search(r"(\d+)\s*min", lower)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*h\b", lower)
    if m:
        return int(m.group(1)) * 60
    if re.search(r"\b1\s*time\b", lower) or "1 time" in lower:
        return 60
    m = re.search(r"(\d+)\s*time", lower)
    if m:
        return int(m.group(1)) * 60
    m = re.search(r"(\d+)\s*t\b", lower)
    if m:
        return int(m.group(1)) * 60
    return 45


def _parse_target_date(text: str, as_of: date) -> date:
    lower = text.lower()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return date.fromisoformat(m.group(1))
    if "i morgen" in lower or "imorgen" in lower or "tomorrow" in lower:
        return as_of + timedelta(days=1)
    if "i dag" in lower or "idag" in lower:
        return as_of
    return as_of + timedelta(days=1)


def _workout_name_from_text(text: str, mins: int) -> str:
    lower = text.lower()
    if "sykkel" in lower or "bike" in lower or "ride" in lower:
        if "intervall" in lower:
            return f"Sykkelintervall {mins} min"
        return f"Sykkel {mins} min"
    if "løp" in lower or "lop" in lower or "run" in lower:
        return f"Løp {mins} min"
    if "svøm" in lower or "svom" in lower or "swim" in lower:
        return f"Svøm {mins} min"
    if "styrke" in lower:
        return f"Styrke {mins} min"
    return f"Coach-økt {mins} min"


def extract_workout_from_text(
    body: str,
    *,
    as_of: date,
    user_hint: str = "",
) -> dict[str, Any] | None:
    """Best-effort structured event from coach proposal markdown."""
    combined = f"{user_hint}\n{body}"
    if not combined.strip():
        return None
    lower = combined.lower()
    if not any(
        w in lower
        for w in (
            "økt",
            "sykkel",
            "løp",
            "lop",
            "svøm",
            "intervall",
            "varighet",
            "oppvarming",
            "min",
            "time",
        )
    ):
        return None

    mins = _parse_minutes(combined)
    for line in combined.splitlines():
        if "varighet" in line.lower() or "total" in line.lower():
            mins = max(mins, _parse_minutes(line))

    target = _parse_target_date(combined, as_of)
    name = _workout_name_from_text(combined, mins)
    m = re.search(r"\*\*Type:\*\*\s*([^\n*]+)", combined, re.I)
    if m:
        name = m.group(1).strip()[:80]
    desc = body.strip()[:2000]
    sport = _detect_type(combined)
    if "intervall" in lower and sport == "Ride":
        name = name if "intervall" in name.lower() else f"Sykkelintervall {mins} min"

    name = name[:80]
    # Stabil id på tvers av prosess-restart (Pythons hash() er randomisert),
    # slik at upsert oppdaterer samme økt i stedet for å lage duplikat.
    name_hash = int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16) % 10000
    return {
        "category": "WORKOUT",
        "type": sport,
        "start_date_local": f"{target.isoformat()}T00:00:00",
        "name": name,
        "description": desc,
        "planned_duration": mins * 60,
        "external_id": f"lofoten-coach-single-{target.isoformat()}-{mins}-{name_hash}",
    }

