"""Build compact LLM context from Intervals + repo."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from coach_bot.aggregates import (
    build_training_snapshot,
    filter_events_for_date,
    filter_events_in_range,
    format_hours_table,
)
from coach_bot.coach_insights import build_coach_brief
from coach_bot.intent import Intent
from coach_bot.intervals_client import IntervalsClient
from coach_bot import atlas
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


def _format_recent_activities(recent: list[dict[str, Any]]) -> str:
    if not recent:
        return "(ingen økter i perioden)"
    lines: list[str] = []
    for act in recent:
        tss = act.get("tss")
        tss_s = f", TSS={tss}" if tss else ""
        hr = act.get("avg_hr")
        hr_s = f", HR={hr}" if hr else ""
        w = act.get("avg_watts")
        w_s = f", W={w}" if w else ""
        lines.append(
            f"- {act.get('date')}: {act.get('type')} – {act.get('name')} "
            f"({act.get('hours')} t{tss_s}{hr_s}{w_s})"
        )
    return "\n".join(lines)


class ContextBuilder:
    def __init__(
        self,
        intervals: IntervalsClient,
        repo: RepoReader,
        tz: str,
        week_override: str | None = None,
    ) -> None:
        self._intervals = intervals
        self._repo = repo
        self._tz = tz
        self._week_override = week_override

    def _training_block(self, bundle: dict[str, Any], snapshot: Any) -> str:
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
        parts.append("\n## Siste økter\n" + _format_recent_activities(snapshot.recent_activities))
        parts.append("\n## Wellness (siste dager)\n" + _format_wellness(bundle["wellness"]))
        return "\n".join(parts)

    def for_chat(self, user_message: str, intent: Intent | None = None) -> str:
        from coach_bot.intent import detect_intent

        intent = intent or detect_intent(user_message)
        bundle = self._intervals.fetch_coach_bundle(activity_days=28)
        snapshot = build_training_snapshot(bundle["activities"], tz=self._tz)
        today = snapshot.as_of
        tomorrow = today + timedelta(days=1)
        start_week = today - timedelta(days=6)

        events_tomorrow = filter_events_for_date(bundle["events"], tomorrow)
        events_today = filter_events_for_date(bundle["events"], today)
        events_week = filter_events_in_range(bundle["events"], start_week, today)
        repo = self._repo.bundle_for_coach()
        phase = self._repo.detect_phase()

        include_advanced = intent in (Intent.STATUS, Intent.WEEK, Intent.ANALYSIS, Intent.CHART)
        brief = build_coach_brief(
            snapshot,
            bundle,
            repo["current_status"],
            week_override=self._week_override,
            phase=phase,
            include_advanced=include_advanced,
        )
        week_plan = self._repo.week_plan_excerpt(as_of_date=today)

        atlas_block = atlas.excerpt_for_context(
            self._repo._root,
            user_message,
            max_chars=2500,
        )

        parts = [
            "# Coach-kontekst (DM)",
            f"Intent: {intent.value}",
            "",
            brief,
            "",
            "### PERSONLIG ATLAS (relevant hukommelse om William)",
            atlas_block,
            "",
        ]

        if intent in (Intent.TOMORROW, Intent.GENERAL, Intent.STATUS):
            parts.extend(
                [
                    f"## I dag ({today})\n{_format_events(events_today)}\n",
                    f"## I morgen ({tomorrow})\n{_format_events(events_tomorrow)}\n",
                ]
            )

        if intent in (Intent.WEEK, Intent.STATUS, Intent.GENERAL):
            parts.extend(
                [
                    f"## Plan denne uken ({start_week} – {today})\n{_format_events(events_week)}\n",
                    "## Aktiv ukeplan (repo)\n" + week_plan + "\n",
                ]
            )

        if intent in (Intent.STATUS, Intent.GENERAL, Intent.ANALYSIS, Intent.CHART):
            parts.append("## Gjennomført (Intervals)\n" + self._training_block(bundle, snapshot))

        if intent == Intent.RACE:
            parts.append("### MASTERPLAN (utdrag)\n" + repo["masterplan_excerpt"] + "\n")

        if intent in (Intent.STATUS, Intent.WEEK, Intent.GENERAL):
            parts.append("### CURRENT_STATUS\n" + repo["current_status"] + "\n")
            parts.append("### Treningsprogram (utdrag)\n" + repo["program_excerpt"] + "\n")
            parts.append("### Tester\n" + repo["test_results_excerpt"] + "\n")

        if intent == Intent.PAIN:
            parts.append("### CURRENT_STATUS (flagg/smerte)\n" + repo["current_status"] + "\n")

        if intent == Intent.GENERAL:
            parts.append("### DAGENS_NIVA (utdrag)\n" + repo["dagens_niva_excerpt"] + "\n")

        return "\n".join(parts)
