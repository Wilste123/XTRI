"""Prepare WORKOUT events for Intervals.icu API (compile + load fields)."""

from __future__ import annotations

from typing import Any

from coach_bot.intervals_workout_syntax import (
    expand_repeat_blocks,
    extract_workout_syntax,
    validate_workout_syntax,
)


def finalize_workout_event(event: dict[str, Any]) -> dict[str, Any]:
    """Ensure description is parseable workout syntax and load/time fields are set."""
    ev = dict(event)
    if ev.get("category") and str(ev.get("category")).upper() != "WORKOUT":
        return ev

    explicit_load = event.get("planned_load") or event.get("icu_training_load") or event.get("load")

    raw_desc = str(ev.get("description") or "")
    syntax = expand_repeat_blocks(extract_workout_syntax(raw_desc) or raw_desc.strip())

    if syntax:
        val = validate_workout_syntax(syntax)
        if val.ok:
            ev["description"] = syntax
            secs = val.estimated_minutes * 60
            if secs > 0:
                ev["planned_duration"] = secs
                ev["moving_time"] = secs
            # TSS/load: la Intervals beregne ved compile med mindre eksplisitt oppgitt.
            if explicit_load is not None:
                try:
                    load_i = int(explicit_load)
                    ev["icu_training_load"] = load_i
                    ev["load"] = load_i
                except (TypeError, ValueError):
                    ev.pop("icu_training_load", None)
                    ev.pop("load", None)
            else:
                ev.pop("icu_training_load", None)
                ev.pop("load", None)

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
