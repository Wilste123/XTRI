"""Build Intervals.icu calendar events from repo week plans."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from coach_bot.repo_reader import RepoReader

_DAY_MAP = {
    "man": 0,
    "tir": 1,
    "ons": 2,
    "tor": 3,
    "fre": 4,
    "lør": 5,
    "søn": 6,
    "lor": 5,
    "son": 6,
}

_SPORT_MAP = {
    "løp": "Run",
    "lop": "Run",
    "run": "Run",
    "sykkel": "Ride",
    "bike": "Ride",
    "ride": "Ride",
    "svøm": "Swim",
    "svom": "Swim",
    "swim": "Swim",
    "styrke": "Workout",
    "strength": "Workout",
    "walk": "Walk",
}


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _parse_duration_minutes(cell: str) -> int | None:
    if not cell:
        return None
    m = re.search(r"(\d+)\s*min", cell, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*[–-]\s*(\d+)\s*min", cell)
    if m:
        return int((int(m.group(1)) + int(m.group(2))) / 2)
    return None


def _detect_type(text: str) -> str:
    lower = text.lower()
    for key, sport in _SPORT_MAP.items():
        if key in lower:
            return sport
    return "Workout"


def parse_week_plan_table(plan_md: str, week_start: date) -> list[dict[str, Any]]:
    """Parse markdown table rows from ukeplan files."""
    events: list[dict[str, Any]] = []
    for line in plan_md.splitlines():
        if not line.strip().startswith("|"):
            continue
        if "---" in line or "Dag" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        day_cell, workout_cell, duration_cell = cells[0], cells[1], cells[2]
        day_key = day_cell.lower().strip()[:3]
        if day_key not in _DAY_MAP:
            continue
        mins = _parse_duration_minutes(duration_cell) or _parse_duration_minutes(workout_cell)
        if "fri" in workout_cell.lower() and (mins is None or mins <= 0):
            continue
        day_offset = _DAY_MAP[day_key]
        event_date = week_start + timedelta(days=day_offset)
        mins = mins or 45
        name = workout_cell[:80] or "Økt"
        sport = _detect_type(workout_cell)
        start_local = f"{event_date.isoformat()}T00:00:00"
        ext_id = f"lofoten-coach-{week_start.isoformat()}-{day_offset}"
        events.append(
            {
                "category": "WORKOUT",
                "type": sport,
                "start_date_local": start_local,
                "name": name,
                "description": workout_cell,
                "planned_duration": mins * 60,
                "external_id": ext_id,
            }
        )
    return events


def events_for_active_week(repo: RepoReader, as_of: date | None = None) -> list[dict[str, Any]]:
    today = as_of or date.today()
    ref = repo.active_training_week(today)
    md = repo.read(ref.filename)
    week_start = _monday_of_week(today)
    return parse_week_plan_table(md, week_start)


def _parse_minutes_message(lower: str) -> int:
    m = re.search(r"(\d+)\s*min", lower)
    if m:
        return int(m.group(1))
    if re.search(r"\b1\s*time\b", lower):
        return 60
    m = re.search(r"(\d+)\s*time", lower)
    if m:
        return int(m.group(1)) * 60
    m = re.search(r"(\d+)\s*h\b", lower)
    if m:
        return int(m.group(1)) * 60
    return 45


def parse_single_workout_request(message: str, as_of: date) -> dict[str, Any] | None:
    """e.g. legg inn løp 45 min på tirsdag / legge inn sykkel 60 min i morgen"""
    lower = message.lower()
    triggers = (
        "legg inn",
        "legge inn",
        "legg til",
        "opprett",
        "ny økt",
    )
    if not any(k in lower for k in triggers):
        return None
    # Krev en eksplisitt idrett i selve meldingen, ellers er dette en
    # oppfølging som refererer til et tidligere forslag (håndteres et annet sted).
    if not any(k in lower for k in _SPORT_MAP):
        return None
    mins = _parse_minutes_message(lower)
    target = as_of
    if "i morgen" in lower or "imorgen" in lower:
        target = as_of + timedelta(days=1)
    else:
        iso = re.search(r"(\d{4}-\d{2}-\d{2})", message)
        if iso:
            target = date.fromisoformat(iso.group(1))
        else:
            for key, off in _DAY_MAP.items():
                if key in lower:
                    mon = _monday_of_week(as_of)
                    target = mon + timedelta(days=off)
                    if off < as_of.weekday() and "neste" not in lower:
                        target = target + timedelta(days=7)
                    break
    sport = _detect_type(lower)
    name = "Coach-økt"
    if "løp" in lower or "lop" in lower:
        name = f"Løp {mins} min"
    elif "sykkel" in lower:
        name = f"Sykkel {mins} min"
    elif "svøm" in lower or "svom" in lower:
        name = f"Svøm {mins} min"
    return {
        "category": "WORKOUT",
        "type": sport,
        "start_date_local": f"{target.isoformat()}T00:00:00",
        "name": name,
        "description": message.strip()[:500],
        "planned_duration": mins * 60,
        "external_id": f"lofoten-coach-single-{target.isoformat()}-{mins}",
    }
