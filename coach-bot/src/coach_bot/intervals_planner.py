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
    "jogg": "Run",
    "sykkel": "Ride",
    "sykl": "Ride",
    "bike": "Ride",
    "ride": "Ride",
    "svøm": "Swim",
    "svom": "Swim",
    "swim": "Swim",
    "styrke": "Workout",
    "strength": "Workout",
    "walk": "Walk",
    "gåtur": "Walk",
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


def coach_external_id(event_date: date, sport: str) -> str:
    return f"lofoten-coach-{event_date.isoformat()}-{sport.lower()}"


def _parse_rpe_from_cells(*cells: str) -> float | None:
    for cell in cells:
        m = re.search(r"RPE\s*(\d+(?:\.\d+)?)", cell or "", re.I)
        if m:
            return float(m.group(1))
        m = re.search(r"Z\s*(\d)", cell or "", re.I)
        if m:
            return float(m.group(1)) + 2.0
    return None


def estimate_planned_load(duration_min: int, rpe: float | None = None) -> int:
    """Rough planned TSS/load for Intervals calendar events."""
    r = rpe if rpe is not None else 5.0
    return max(10, int(round(duration_min * r * 0.85)))


def _collect_plan_rows(plan_md: str) -> list[dict[str, Any]]:
    """Table rows in file order (Man … Søn), without calendar dates."""
    rows: list[dict[str, Any]] = []
    for line in plan_md.splitlines():
        if not line.strip().startswith("|"):
            continue
        if "---" in line or "Dag" in line:
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
        if "fri" in workout_cell.lower() and (mins is None or mins <= 0):
            continue
        rows.append(
            {
                "workout_cell": workout_cell,
                "duration_cell": duration_cell,
                "intensity_cell": intensity_cell,
                "mins": mins or 45,
            }
        )
    return rows


def events_from_repo_plan(
    repo: RepoReader,
    as_of: date | None = None,
    *,
    start_date: date | None = None,
    skip_past: bool = True,
) -> list[dict[str, Any]]:
    """Map baseline/week table to consecutive days forward from start_date (default today)."""
    today = as_of or date.today()
    anchor = start_date or today
    if anchor < today and skip_past:
        anchor = today
    ref = repo.active_training_week(today)
    md = repo.read(ref.filename)
    if md.startswith("(fil mangler"):
        return []
    events: list[dict[str, Any]] = []
    for i, row in enumerate(_collect_plan_rows(md)):
        event_date = anchor + timedelta(days=i)
        if skip_past and event_date < today:
            continue
        workout_cell = row["workout_cell"]
        mins = int(row["mins"])
        sport = _detect_type(workout_cell)
        rpe = _parse_rpe_from_cells(row.get("intensity_cell", ""), workout_cell)
        load = estimate_planned_load(mins, rpe)
        name = workout_cell[:80] or "Økt"
        desc_parts = [workout_cell]
        if row.get("intensity_cell"):
            desc_parts.append(f"Intensitet: {row['intensity_cell']}")
        desc_parts.append(f"Planlagt load ~{load} TSS (est.)")
        events.append(
            {
                "category": "WORKOUT",
                "type": sport,
                "start_date_local": f"{event_date.isoformat()}T00:00:00",
                "name": name,
                "description": " · ".join(desc_parts)[:500],
                "planned_duration": mins * 60,
                "load": load,
                "icu_training_load": load,
                "external_id": coach_external_id(event_date, sport),
            }
        )
    return events


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
        event_date = week_start + timedelta(days=day_offset)
        load = estimate_planned_load(mins)
        ext_id = coach_external_id(event_date, sport)
        events.append(
            {
                "category": "WORKOUT",
                "type": sport,
                "start_date_local": start_local,
                "name": name,
                "description": workout_cell,
                "planned_duration": mins * 60,
                "load": load,
                "icu_training_load": load,
                "external_id": ext_id,
            }
        )
    return events


def events_for_active_week(
    repo: RepoReader,
    as_of: date | None = None,
    *,
    start_date: date | None = None,
    skip_past: bool = True,
) -> list[dict[str, Any]]:
    today = as_of or date.today()
    return events_from_repo_plan(
        repo, today, start_date=start_date, skip_past=skip_past
    )


def scale_events_duration(events: list[dict[str, Any]], percent: float) -> list[dict[str, Any]]:
    """Return copies of events with planned_duration adjusted by percent."""
    from coach_bot.event_duration import event_duration_seconds

    factor = 1 + percent / 100.0
    out: list[dict[str, Any]] = []
    for e in events:
        dur = event_duration_seconds(e)
        if dur <= 0:
            continue
        new = max(300, int(round(dur * factor / 60.0)) * 60)
        patched = dict(e)
        patched["planned_duration"] = new
        out.append(patched)
    return out


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
        "external_id": coach_external_id(target, sport),
        "load": estimate_planned_load(mins),
        "icu_training_load": estimate_planned_load(mins),
    }
