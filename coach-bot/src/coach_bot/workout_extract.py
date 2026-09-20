"""Parse proposed workouts from chat text for Intervals events."""

from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Any

from coach_bot.intervals_planner import (
    _DAY_MAP,
    _SPORT_MAP,
    _detect_type,
    _parse_duration_minutes,
    coach_external_id,
    estimate_planned_load,
)

_WRITE_ACTION = re.compile(
    r"(legg\s+den\s+inn|legge\s+den\s+inn|legg\s+inn|legge\s+inn|legg\s+til|"
    r"opprett|putt\s+den|synk\s+den|i\s+intervals|i\s+intervalls)",
    re.I,
)

_COMMIT_EXACT = frozenset(
    {
        "ja",
        "js",
        "jaa",
        "jada",
        "jepp",
        "japp",
        "ja takk",
        "yes",
        "yep",
        "ok",
        "okay",
        "okey",
        "gjør det",
        "gjør",
        "kjør",
        "kjør på",
        "kjør det",
        "bekreft",
        "legg inn",
        "legg dem inn",
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


def is_commit_only_message(message: str) -> bool:
    """Bare bekreftelse (ja/ok) uten ny plan i samme melding."""
    if not is_commit_message(message):
        return False
    lower = (message or "").lower().strip()
    # «Legg den inn i Intervals» er write-oppfølging på forrige plan, ikke bare «ja».
    if ("legg den" in lower or "legge den" in lower) and (
        "interval" in lower or "intervall" in lower
    ):
        return False
    if len(lower) > 60:
        return False
    plan_words = (
        "synk",
        "ukeplan",
        "legg inn",
        "legge inn",
        "lag en",
        "lage en",
        "neste 7",
        "detalj",
        "tss",
    )
    return not any(w in lower for w in plan_words)


def wants_full_plan(message: str) -> bool:
    """User refers to the whole multi-day plan, not a single workout."""
    low = (message or "").lower()
    return any(
        w in low
        for w in (
            "hele planen",
            "hele uka",
            "hele uken",
            "alle øktene",
            "alle oktene",
            "alle disse",
            "disse",
            "alle",
            "hele",
            "planen",
            "ukeplan",
            "uken",
            "uka",
        )
    )


_MONTHS_NO = {
    "januar": 1,
    "februar": 2,
    "mars": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


def _parse_plan_date(fragment: str, as_of: date) -> date | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", fragment)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})\.?\s*(" + "|".join(_MONTHS_NO) + r")", fragment.lower())
    if m:
        day = int(m.group(1))
        mon = _MONTHS_NO[m.group(2)]
        try:
            d = date(as_of.year, mon, day)
        except ValueError:
            return None
        if (d - as_of).days < -180:
            try:
                d = date(as_of.year + 1, mon, day)
            except ValueError:
                return None
        return d
    return None


def _week_start_from_plan_header(text: str, as_of: date) -> date | None:
    m = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*[–\-—]\s*(\d{4}-\d{2}-\d{2})", text
    )
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            pass
    m = re.search(r"ukeplan\s*\(?\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None


def _skip_rest_day(workout_cell: str, mins: int) -> bool:
    low = workout_cell.lower()
    if mins <= 0:
        return True
    if "fri" in low and not any(
        k in low for k in ("løp", "lop", "sykkel", "sykl", "svøm", "svom", "styrke", "gåtur")
    ):
        return True
    if low.strip() in ("—", "-", "fri", "hvile"):
        return True
    return False


def extract_week_plan_from_markdown_table(
    text: str, *, as_of: date, max_events: int = 14
) -> list[dict[str, Any]]:
    """Parse coach markdown table (| Man | Økt | Varighet |) into calendar events."""
    if not text or "|" not in text:
        return []
    week_start = _week_start_from_plan_header(text, as_of)
    if week_start is None:
        return []
    events: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if "---" in line or re.search(r"\|\s*dag\s*\|", line, re.I):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        day_cell, workout_cell, duration_cell = cells[0], cells[1], cells[2]
        intensity_cell = cells[3] if len(cells) > 3 else ""
        day_key = day_cell.lower().strip()[:3]
        if day_key not in _DAY_MAP:
            continue
        mins = _parse_duration_minutes(duration_cell) or _parse_duration_minutes(workout_cell)
        if mins is None:
            mins = 45
        if _skip_rest_day(workout_cell, mins):
            continue
        event_date = week_start + timedelta(days=_DAY_MAP[day_key])
        sport = _detect_type(workout_cell)
        name = _workout_name_from_text(workout_cell, mins)
        desc_parts = [workout_cell.strip()]
        if intensity_cell:
            desc_parts.append(f"Intensitet: {intensity_cell}")
        load = estimate_planned_load(mins)
        events.append(
            {
                "category": "WORKOUT",
                "type": sport,
                "start_date_local": f"{event_date.isoformat()}T00:00:00",
                "name": name[:80],
                "description": " · ".join(desc_parts)[:500],
                "planned_duration": mins * 60,
                "load": load,
                "icu_training_load": load,
                "external_id": coach_external_id(event_date, sport),
            }
        )
        if len(events) >= max_events:
            break
    events.sort(key=lambda e: e["start_date_local"])
    return events


def extract_week_plan_from_assistant(
    text: str, *, as_of: date, max_events: int = 14
) -> list[dict[str, Any]]:
    """Best effort: markdown uke-tabell først, deretter dag-for-dag-prosa."""
    table_events = extract_week_plan_from_markdown_table(
        text, as_of=as_of, max_events=max_events
    )
    if len(table_events) >= 2:
        return table_events
    prose = extract_week_plan_from_text(text, as_of=as_of, max_events=max_events)
    if len(prose) >= len(table_events):
        return prose
    return table_events


def extract_week_plan_from_text(
    text: str, *, as_of: date, max_events: int = 14
) -> list[dict[str, Any]]:
    """Parse a multi-day plan the coach wrote in chat into Intervals events.

    Handles both single-line days ("**20. september**: Løp 45 min") and a date
    header followed by an indented workout line. One event per date.
    """
    if not text:
        return []
    events: list[dict[str, Any]] = []
    seen: set[date] = set()
    pending_date: date | None = None
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*• ").strip()
        if not line:
            continue
        date_here = _parse_plan_date(line, as_of)
        workout_part = line.split(":", 1)[1] if ":" in line else line
        low = workout_part.lower()
        has_sport = any(k in low for k in _SPORT_MAP)
        has_dur = "min" in low or "time" in low
        if date_here is not None and not (has_sport or has_dur):
            pending_date = date_here
            continue
        if not (has_sport or has_dur):
            continue
        d = date_here or pending_date
        if d is None or d in seen:
            continue
        seen.add(d)
        mins = _parse_minutes(workout_part)
        sport = _detect_type(workout_part)
        name = _workout_name_from_text(workout_part, mins)
        desc = workout_part.strip().strip("*").strip()[:500]
        events.append(
            {
                "category": "WORKOUT",
                "type": sport,
                "start_date_local": f"{d.isoformat()}T00:00:00",
                "name": name,
                "description": desc,
                "planned_duration": mins * 60,
                "external_id": f"lofoten-coach-plan-{d.isoformat()}",
            }
        )
        if len(events) >= max_events:
            break
    events.sort(key=lambda e: e["start_date_local"])
    return events


def asks_workout_for_calendar(message: str) -> bool:
    """User wants coach to plan/create a calendar workout (often tomorrow)."""
    lower = (message or "").lower()
    if ("legg den" in lower or "legge den" in lower) and (
        "interval" in lower or "intervall" in lower
    ):
        return False
    has_workout = any(w in lower for w in ("økt", "okt", "workout", "trening"))
    if "intervall" in lower and "intervals" not in lower and "intervalls" not in lower:
        has_workout = True
    has_action = any(
        w in lower for w in ("legg", "legge", "opprett", "kan du", "sette", "lage", "planlegg")
    )
    has_when = any(w in lower for w in ("i morgen", "imorgen", "tomorrow", "kalender"))
    has_intervals = "intervals" in lower or "intervalls" in lower
    return has_workout and has_action and (has_when or has_intervals)


def _workout_focus_text(combined: str) -> str:
    """Narrow text used for duration parsing (ignore uke-volum m.m.)."""
    lower = combined.lower()
    for marker in ("### anbefalt økt", "**type:**", "## plan for i morgen"):
        idx = lower.find(marker)
        if idx >= 0:
            return combined[idx : idx + 2000]
    lines: list[str] = []
    for line in combined.splitlines():
        low = line.lower()
        if any(
            x in low
            for x in (
                "volummålet",
                "timer for uken",
                "3–5 timer",
                "3-5 timer",
                "bratte volum",
            )
        ):
            continue
        lines.append(line)
    return "\n".join(lines)


def _parse_minutes(text: str) -> int:
    lower = text.lower()
    m = re.search(r"(\d+)\s*min", lower)
    if m:
        return int(m.group(1))
    # Desimaltimer først: «1.5 time» / «1,5 t» -> 90 min.
    m = re.search(r"(\d+[.,]\d+)\s*(?:time|timer|t\b|h\b)", lower)
    if m:
        return int(round(float(m.group(1).replace(",", ".")) * 60))
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
    if "sykkel" in lower or "sykl" in lower or "bike" in lower or "ride" in lower:
        if "intervall" in lower:
            return f"Sykkelintervall {mins} min"
        return f"Sykkel {mins} min"
    if "løp" in lower or "lop" in lower or "run" in lower or "jogg" in lower:
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

    focus = _workout_focus_text(combined)
    mins = _parse_minutes(focus)
    for line in focus.splitlines():
        if "varighet" in line.lower() or "total" in line.lower():
            mins = max(mins, _parse_minutes(line))
    mins = min(mins, 240)

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

