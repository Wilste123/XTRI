"""Build compact LLM context from Intervals + repo."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from coach_bot.aggregates import (
    build_training_snapshot,
    filter_events_for_date,
    filter_events_in_range,
    format_hours_table,
)
from coach_bot.intervals_client import IntervalsClient
from coach_bot.repo_reader import RepoReader


def _format_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return "(ingen planlagte events i perioden)"
    lines: list[str] = []
    for ev in events[:20]:
        d = (ev.get("start_date_local") or ev.get("start_date") or "")[:10]
        name = ev.get("name") or ev.get("category") or "Økt"
        desc = ev.get("description") or ""
        mins = ev.get("moving_time")
        dur = f", {int(mins) // 60} min" if mins else ""
        lines.append(f"- {d}: {name}{dur} {desc[:120]}".strip())
    if len(events) > 20:
        lines.append(f"... +{len(events) - 20} flere")
    return "\n".join(lines)


def _format_wellness(rows: list[dict[str, Any]], limit: int = 7) -> str:
    if not rows:
        return "(ingen wellness-data i Intervals – ikke anta søvn/HRV)"
    lines: list[str] = []
    for row in rows[-limit:]:
        d = row.get("id") or row.get("date") or "?"
        sleep = row.get("sleepSecs") or row.get("sleep")
        hrv = row.get("hrv") or row.get("hrvSDNN")
        weight = row.get("weight")
        rest_hr = row.get("restingHR")
        parts = [f"{d}"]
        if sleep:
            parts.append(f"søvn={sleep}")
        if hrv:
            parts.append(f"hrv={hrv}")
        if rest_hr:
            parts.append(f"restHR={rest_hr}")
        if weight:
            parts.append(f"vekt={weight}")
        comment = row.get("comments") or row.get("notes")
        if comment:
            parts.append(f"notat={str(comment)[:80]}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


class ContextBuilder:
    def __init__(self, intervals: IntervalsClient, repo: RepoReader, tz: str) -> None:
        self._intervals = intervals
        self._repo = repo
        self._tz = tz

    def _base_intervals_text(
        self, bundle: dict[str, Any], snapshot: Any
    ) -> str:
        parts = [
            f"As of: {snapshot.as_of} ({self._tz})",
            "",
            "## Siste 7 dager",
            format_hours_table(snapshot.last_7_days),
            "",
            "## Forrige 7 dager",
            format_hours_table(snapshot.previous_7_days),
            "",
            "## Siste 28 dager",
            format_hours_table(snapshot.last_28_days),
        ]
        if snapshot.volume_change_pct_7d is not None:
            parts.append(
                f"\nVolumendring 7d vs forrige 7d: {snapshot.volume_change_pct_7d:+.0f}%"
            )
        parts.append("\n## Siste økter\n" + json.dumps(snapshot.recent_activities, ensure_ascii=False, indent=2))
        parts.append("\n## Wellness (siste dager)\n" + _format_wellness(bundle["wellness"]))
        return "\n".join(parts)

    def for_status(self) -> str:
        bundle = self._intervals.fetch_coach_bundle(activity_days=28)
        snapshot = build_training_snapshot(bundle["activities"], tz=self._tz)
        repo = self._repo.bundle_for_coach()
        return (
            "# Kommando: /status\n\n"
            "## Intervals data\n"
            + self._base_intervals_text(bundle, snapshot)
            + "\n\n## Repo context\n"
            + f"### CURRENT_STATUS\n{repo['current_status']}\n\n"
            + f"### MASTERPLAN (utdrag)\n{repo['masterplan_excerpt']}\n"
        )

    def for_imorgen(self) -> str:
        bundle = self._intervals.fetch_coach_bundle(activity_days=14)
        snapshot = build_training_snapshot(bundle["activities"], tz=self._tz)
        today = snapshot.as_of
        tomorrow = today + timedelta(days=1)
        events_tomorrow = filter_events_for_date(bundle["events"], tomorrow)
        events_today = filter_events_for_date(bundle["events"], today)
        repo = self._repo.bundle_for_coach()
        return (
            "# Kommando: /imorgen\n\n"
            f"I dag ({today}):\n{_format_events(events_today)}\n\n"
            f"I morgen ({tomorrow}):\n{_format_events(events_tomorrow)}\n\n"
            "## Intervals data (belastning)\n"
            + self._base_intervals_text(bundle, snapshot)
            + "\n\n## Repo context\n"
            + f"### CURRENT_STATUS\n{repo['current_status']}\n"
        )

    def for_ukestatus(self) -> str:
        bundle = self._intervals.fetch_coach_bundle(activity_days=28)
        snapshot = build_training_snapshot(bundle["activities"], tz=self._tz)
        today = snapshot.as_of
        start_week = today - timedelta(days=6)
        events_week = filter_events_in_range(bundle["events"], start_week, today)
        repo = self._repo.bundle_for_coach()
        return (
            "# Kommando: /ukestatus\n\n"
            f"Uke {start_week} – {today}\n\n"
            "## Plan (events denne uken)\n"
            + _format_events(events_week)
            + "\n\n## Gjennomført (Intervals aggregert)\n"
            + format_hours_table(snapshot.last_7_days)
            + "\n\n## Intervals (detalj)\n"
            + self._base_intervals_text(bundle, snapshot)
            + "\n\n## Repo context\n"
            + f"### CURRENT_STATUS\n{repo['current_status']}\n\n"
            + f"### DAGENS_NIVA (utdrag)\n{repo['dagens_niva_excerpt']}\n"
        )
