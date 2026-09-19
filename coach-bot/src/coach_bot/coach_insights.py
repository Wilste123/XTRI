"""Deterministic coach analysis (COACH_BRIEF) from data + repo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from coach_bot.aggregates import (
    TrainingSnapshot,
    acwr_from_wellness,
    consistency_stats,
    discipline_balance_pct,
    format_hours_table,
    intensity_load_per_hour,
    plan_adherence,
    plan_vs_actual,
    summarize_wellness_trends,
)

RACE_DATE = date(2027, 8, 20)
PROJECT_START = date(2026, 9, 19)

WEEK_VOLUME_TARGETS: dict[str, tuple[float, float]] = {
    "baseline-uke.md": (3.0, 5.0),
    "uke-01.md": (4.0, 6.0),
    "uke-02.md": (5.0, 6.0),
    "uke-03.md": (6.0, 7.0),
    "uke-04.md": (6.0, 7.0),
}


@dataclass
class WeekPlanRef:
    label: str
    filename: str
    hours_min: float
    hours_max: float


def resolve_week_plan(
    as_of: date,
    current_status_text: str,
    week_override: str | None = None,
) -> WeekPlanRef:
    if week_override and week_override.strip():
        raw = week_override.strip()
        if raw in ("baseline", "baseline-uke"):
            key = "baseline-uke.md"
        elif raw.startswith("uke-") and not raw.endswith(".md"):
            key = f"{raw}.md"
        elif not raw.endswith(".md"):
            key = f"{raw}.md"
        else:
            key = raw
        lo, hi = WEEK_VOLUME_TARGETS.get(key, (5.0, 7.0))
        label = key.replace(".md", "")
        return WeekPlanRef(label=label, filename=f"ukeplan/{key}", hours_min=lo, hours_max=hi)

    baseline_done = "baseline ikke fullført" not in current_status_text.lower() and (
        "[x] fullfør baseline" in current_status_text.lower()
        or "baseline fullført" in current_status_text.lower()
    )

    if not baseline_done:
        lo, hi = WEEK_VOLUME_TARGETS["baseline-uke.md"]
        return WeekPlanRef("baseline-uke", "ukeplan/baseline-uke.md", lo, hi)

    days = (as_of - PROJECT_START).days
    week_index = max(1, (days // 7) + 1)
    week_index = min(week_index, 4)
    fname = f"uke-{week_index:02d}.md"
    lo, hi = WEEK_VOLUME_TARGETS.get(fname, (5.0, 7.0))
    return WeekPlanRef(f"uke-{week_index:02d}", f"ukeplan/{fname}", lo, hi)


def _risk_flags(
    snapshot: TrainingSnapshot,
    week: WeekPlanRef,
    phase: str = "Base_0",
) -> list[str]:
    flags: list[str] = []
    h7 = snapshot.last_7_days.total_hours
    if phase.startswith("Base") and snapshot.last_7_days.activity_count == 0:
        flags.append("Høy kontinuitetsrisiko: ingen økter siste 7 dager i Intervals.")
    if h7 > week.hours_max * 1.2:
        flags.append(
            f"Volum ({h7:.1f} t/7d) over målområde ({week.hours_min:.0f}–{week.hours_max:.0f} t/uke) – vurder deload."
        )
    if snapshot.volume_change_pct_7d is not None and snapshot.volume_change_pct_7d > 40:
        flags.append(
            f"Bratt volumøkning ({snapshot.volume_change_pct_7d:+.0f}% vs forrige 7d) – skadefrihet først."
        )
    return flags


def _next_step(week: WeekPlanRef, snapshot: TrainingSnapshot, pva: Any) -> str:
    if snapshot.last_7_days.activity_count == 0:
        if week.label == "baseline-uke":
            return "Start baseline-testuke (se ukeplan) og logg alle økter i Intervals."
        return f"Følg {week.filename}; legg gro plan som events i Intervals denne uken."
    if pva.planned_event_count > 0 and pva.completed_activity_count == 0:
        return "Du har planlagte events men ingen loggede økter – synk klokke/Strava til Intervals."
    return f"Fortsett {week.label}; hold volum innen {week.hours_min:.0f}–{week.hours_max:.0f} t denne uken."


def _advanced_section(
    snapshot: TrainingSnapshot,
    bundle: dict[str, Any],
    start_week: date,
    today: date,
    phase: str,
) -> list[str]:
    lines: list[str] = []
    wellness = bundle.get("wellness") or []
    acwr = acwr_from_wellness(wellness)
    if acwr is not None:
        flag = ""
        if acwr > 1.5:
            flag = " (høy – vurder roligere)"
        elif acwr < 0.8:
            flag = " (lav – rom for mer)"
        lines.append(f"- ACWR (ATL/CTL): {acwr}{flag}")
    bal = discipline_balance_pct(snapshot.last_7_days)
    if bal:
        parts = [f"{k} {v}%" for k, v in sorted(bal.items())]
        lines.append(f"- Disiplinbalanse 7d: {', '.join(parts)}")
    cons = consistency_stats(bundle.get("activities") or [], today)
    lines.append(
        f"- Konsistens ({cons['activity_days']} treningsdager/28d): "
        f"~{cons['sessions_per_week']} dager/uke, streak {cons['current_streak_days']}d, "
        f"lengste pause {cons['longest_rest_gap_days']}d"
    )
    adh = plan_adherence(bundle.get("events") or [], bundle.get("activities") or [], start_week, today)
    if adh["planned_days"] > 0:
        lines.append(
            f"- Plan adherence: {adh['matched_days']}/{adh['planned_days']} planlagte dager med loggede økt"
        )
    tss_h = intensity_load_per_hour(bundle.get("activities") or [], start_week, today)
    if tss_h is not None:
        lines.append(f"- TSS/time (uke): {tss_h}")
    weeks_to_race = max(0, (RACE_DATE - today).days // 7)
    lines.append(f"- Race countdown: {weeks_to_race} uker til 20. aug 2027 · fase {phase}")
    return lines


def build_coach_brief(
    snapshot: TrainingSnapshot,
    bundle: dict[str, Any],
    current_status_text: str,
    week_override: str | None = None,
    phase: str = "Base_0",
    include_advanced: bool = False,
) -> str:
    today = snapshot.as_of
    days_to_race = (RACE_DATE - today).days
    week = resolve_week_plan(today, current_status_text, week_override)

    start_week = today - timedelta(days=6)
    pva = plan_vs_actual(
        bundle.get("events") or [],
        snapshot.last_7_days,
        start_week,
        today,
    )
    wellness_block = summarize_wellness_trends(bundle.get("wellness") or [])
    risks = _risk_flags(snapshot, week, phase)
    next_step = _next_step(week, snapshot, pva)

    lines = [
        "## COACH_BRIEF (deterministisk – bruk disse tallene)",
        f"- Dager til Lofoten Half Extreme 2027: {days_to_race}",
        f"- Fase (fra CURRENT_STATUS): {phase}",
        f"- Aktiv ukeplan: {week.label} ({week.filename})",
        f"- Volummål denne uken: {week.hours_min:.0f}–{week.hours_max:.0f} t",
        f"- Gjennomført siste 7 dager: {snapshot.last_7_days.total_hours:.1f} t "
        f"({snapshot.last_7_days.activity_count} økter)",
        f"- Plan vs faktisk (kalenderuke {start_week}–{today}): "
        f"{pva.planned_event_count} planlagte events (~{pva.planned_minutes:.0f} min), "
        f"{pva.completed_activity_count} loggede økter i perioden",
    ]
    if snapshot.volume_change_pct_7d is not None:
        lines.append(
            f"- Volumendring 7d vs forrige 7d: {snapshot.volume_change_pct_7d:+.0f}%"
        )
    if wellness_block:
        lines.append(f"- Belastning/wellness: {wellness_block}")
    if risks:
        lines.append("- Risiko:")
        for r in risks:
            lines.append(f"  - {r}")
    else:
        lines.append("- Risiko: ingen automatiske flagg (sjekk subjektivt)")
    lines.append(f"- Neste steg (anbefalt): {next_step}")
    if include_advanced:
        lines.append("")
        lines.append("### ADVANCED (deterministisk)")
        for row in _advanced_section(snapshot, bundle, start_week, today, phase):
            lines.append(row)
    lines.append("")
    lines.append("### Gjennomført (detalj)")
    lines.append(format_hours_table(snapshot.last_7_days))
    return "\n".join(lines)
