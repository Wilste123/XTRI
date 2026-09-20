"""Prepare WORKOUT events for Intervals.icu API (compile + load fields)."""

from __future__ import annotations

from typing import Any

from coach_bot.intervals_workout_syntax import (
    estimate_workout_minutes,
    extract_workout_syntax,
    validate_workout_syntax,
)


def finalize_workout_event(event: dict[str, Any]) -> dict[str, Any]:
    """Ensure description is parseable workout syntax and load/time fields are set."""
    ev = dict(event)
    if ev.get("category") and str(ev.get("category")).upper() != "WORKOUT":
        return ev

    raw_desc = str(ev.get("description") or "")
    syntax = extract_workout_syntax(raw_desc)
    if not syntax and raw_desc.strip().startswith("-"):
        syntax = raw_desc.strip()

    if syntax:
        val = validate_workout_syntax(syntax)
        if val.ok:
            ev["description"] = syntax
            secs = val.estimated_minutes * 60
            if secs > 0:
                ev["planned_duration"] = secs
                ev["moving_time"] = secs
            load = ev.get("icu_training_load") or ev.get("load")
            if load is None and val.estimated_minutes:
                from coach_bot.intervals_planner import estimate_planned_load

                ev["icu_training_load"] = estimate_planned_load(
                    val.estimated_minutes, 6.0 if "85" in syntax else 5.0
                )
                ev["load"] = ev["icu_training_load"]
            elif load is not None:
                ev["icu_training_load"] = int(load)
                ev["load"] = int(load)

    sport = str(ev.get("type") or "")
    if syntax and not ev.get("target"):
        if sport in ("Ride", "Run"):
            ev["target"] = "HR"
        elif sport == "Swim":
            ev["target"] = "PACE"

    # Empty workout_doc nudges Intervals to compile from description (forum pattern).
    if syntax:
        ev["workout_doc"] = {}

    return ev


def finalize_workout_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [finalize_workout_event(e) for e in events]
