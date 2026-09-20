"""Normalize planned event durations (Intervals uses seconds)."""

from __future__ import annotations

from typing import Any


def event_duration_seconds(ev: dict[str, Any]) -> int:
    """Best-effort duration in seconds for calendar events or activities."""
    pd = ev.get("planned_duration")
    if pd is not None:
        try:
            v = int(float(pd))
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    for key in ("moving_time", "duration", "elapsed_time"):
        v = ev.get(key)
        if v is None:
            continue
        try:
            sec = int(float(v))
            if sec > 0:
                return sec
        except (TypeError, ValueError):
            continue
    return 0


def event_duration_minutes(ev: dict[str, Any]) -> int | None:
    sec = event_duration_seconds(ev)
    if sec <= 0:
        return None
    return max(1, int(round(sec / 60.0)))


def format_event_duration(ev: dict[str, Any]) -> str:
    mins = event_duration_minutes(ev)
    if mins is None:
        return ""
    return f", {mins} min"
