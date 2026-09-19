"""Aggregate intervals.icu activities for coach context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def classify_sport(activity: dict[str, Any]) -> str:
    raw = (activity.get("type") or activity.get("sport_type") or "").lower()
    if "swim" in raw:
        return "swim"
    if "run" in raw:
        return "run"
    if "ride" in raw or "bike" in raw or "virtual" in raw:
        return "bike"
    if "weight" in raw or "strength" in raw or "gym" in raw:
        return "strength"
    return "other"


def activity_duration_seconds(activity: dict[str, Any]) -> int:
    for key in ("moving_time", "elapsed_time", "duration"):
        val = activity.get(key)
        if val is not None:
            return int(val)
    return 0


@dataclass
class PeriodSummary:
    start: date
    end: date
    total_hours: float = 0.0
    by_discipline_hours: dict[str, float] = field(default_factory=dict)
    activity_count: int = 0


@dataclass
class TrainingSnapshot:
    tz: str
    as_of: date
    last_7_days: PeriodSummary
    previous_7_days: PeriodSummary
    last_28_days: PeriodSummary
    recent_activities: list[dict[str, Any]]
    volume_change_pct_7d: float | None


def summarize_period(
    activities: list[dict[str, Any]],
    start: date,
    end: date,
) -> PeriodSummary:
    by_disc: dict[str, float] = {}
    total_sec = 0
    count = 0
    for act in activities:
        d = _parse_date(act.get("start_date_local") or act.get("start_date"))
        if d is None or d < start or d > end:
            continue
        sec = activity_duration_seconds(act)
        if sec <= 0:
            continue
        disc = classify_sport(act)
        by_disc[disc] = by_disc.get(disc, 0.0) + sec / 3600.0
        total_sec += sec
        count += 1
    return PeriodSummary(
        start=start,
        end=end,
        total_hours=total_sec / 3600.0,
        by_discipline_hours=by_disc,
        activity_count=count,
    )


def build_training_snapshot(
    activities: list[dict[str, Any]],
    tz: str = "Europe/Oslo",
    as_of: date | None = None,
    recent_limit: int = 5,
) -> TrainingSnapshot:
    today = as_of or datetime.now(ZoneInfo(tz)).date()
    end_7 = today
    start_7 = today - timedelta(days=6)
    start_prev_7 = today - timedelta(days=13)
    end_prev_7 = today - timedelta(days=7)
    start_28 = today - timedelta(days=27)

    last_7 = summarize_period(activities, start_7, end_7)
    prev_7 = summarize_period(activities, start_prev_7, end_prev_7)
    last_28 = summarize_period(activities, start_28, end_7)

    change_pct: float | None = None
    if prev_7.total_hours > 0:
        change_pct = ((last_7.total_hours - prev_7.total_hours) / prev_7.total_hours) * 100.0
    elif last_7.total_hours > 0:
        change_pct = 100.0

    sorted_acts = sorted(
        activities,
        key=lambda a: a.get("start_date_local") or a.get("start_date") or "",
        reverse=True,
    )
    recent: list[dict[str, Any]] = []
    for act in sorted_acts:
        if len(recent) >= recent_limit:
            break
        sec = activity_duration_seconds(act)
        if sec <= 0:
            continue
        recent.append(
            {
                "date": (act.get("start_date_local") or act.get("start_date") or "")[:10],
                "type": classify_sport(act),
                "name": act.get("name") or act.get("type"),
                "hours": round(sec / 3600.0, 2),
                "tss": act.get("icu_training_load") or act.get("training_load"),
                "avg_hr": act.get("average_heartrate") or act.get("avg_hr"),
                "avg_watts": act.get("average_watts") or act.get("icu_average_watts"),
            }
        )

    return TrainingSnapshot(
        tz=tz,
        as_of=today,
        last_7_days=last_7,
        previous_7_days=prev_7,
        last_28_days=last_28,
        recent_activities=recent,
        volume_change_pct_7d=change_pct,
    )


def format_hours_table(summary: PeriodSummary) -> str:
    lines = [f"Periode {summary.start} – {summary.end}: {summary.total_hours:.1f} t totalt ({summary.activity_count} økter)"]
    for disc in ("swim", "bike", "run", "strength", "other"):
        h = summary.by_discipline_hours.get(disc, 0.0)
        if h > 0:
            lines.append(f"  - {disc}: {h:.1f} t")
    return "\n".join(lines)


def filter_events_for_date(events: list[dict[str, Any]], target: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in events:
        d = _parse_date(ev.get("start_date_local") or ev.get("start_date"))
        if d == target:
            out.append(ev)
    return out


def filter_events_in_range(
    events: list[dict[str, Any]], start: date, end: date
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in events:
        d = _parse_date(ev.get("start_date_local") or ev.get("start_date"))
        if d is not None and start <= d <= end:
            out.append(ev)
    return out


@dataclass
class PlanVsActual:
    start: date
    end: date
    planned_event_count: int
    planned_minutes: float
    completed_activity_count: int
    completed_hours: float


def _event_minutes(ev: dict[str, Any]) -> float:
    for key in ("moving_time", "duration", "planned_duration"):
        val = ev.get(key)
        if val is not None:
            v = float(val)
            return v / 60.0 if v > 500 else v
    return 0.0


def plan_vs_actual(
    events: list[dict[str, Any]],
    period: PeriodSummary,
    start: date,
    end: date,
) -> PlanVsActual:
    week_events = filter_events_in_range(events, start, end)
    planned_mins = sum(_event_minutes(ev) for ev in week_events)
    return PlanVsActual(
        start=start,
        end=end,
        planned_event_count=len(week_events),
        planned_minutes=planned_mins,
        completed_activity_count=period.activity_count,
        completed_hours=period.total_hours,
    )


def acwr_from_wellness(rows: list[dict[str, Any]]) -> float | None:
    """Acute:chronic workload ratio (ATL/CTL) from latest wellness row."""
    if not rows:
        return None
    last = rows[-1]
    ctl = last.get("ctl") or last.get("fitness")
    atl = last.get("atl") or last.get("fatigue")
    if ctl is None or atl is None:
        return None
    c, a = float(ctl), float(atl)
    if c <= 0:
        return None
    return round(a / c, 2)


def discipline_balance_pct(summary: PeriodSummary) -> dict[str, float]:
    total = summary.total_hours
    if total <= 0:
        return {}
    return {k: round((v / total) * 100.0, 1) for k, v in summary.by_discipline_hours.items()}


def consistency_stats(
    activities: list[dict[str, Any]],
    as_of: date,
    lookback_days: int = 28,
) -> dict[str, Any]:
    start = as_of - timedelta(days=lookback_days - 1)
    dates: set[date] = set()
    for act in activities:
        d = _parse_date(act.get("start_date_local") or act.get("start_date"))
        if d is None or d < start or d > as_of:
            continue
        if activity_duration_seconds(act) > 0:
            dates.add(d)
    sorted_dates = sorted(dates)
    longest_gap = 0
    if len(sorted_dates) >= 2:
        for i in range(1, len(sorted_dates)):
            gap = (sorted_dates[i] - sorted_dates[i - 1]).days - 1
            longest_gap = max(longest_gap, gap)
    streak = 0
    d = as_of
    while d >= start:
        if d in dates:
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    weeks = max(1, lookback_days // 7)
    return {
        "activity_days": len(dates),
        "sessions_per_week": round(len(dates) / weeks, 1),
        "longest_rest_gap_days": longest_gap,
        "current_streak_days": streak,
    }


def plan_adherence(
    events: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    start: date,
    end: date,
) -> dict[str, int]:
    week_events = filter_events_in_range(events, start, end)
    act_dates: set[date] = set()
    for act in activities:
        d = _parse_date(act.get("start_date_local") or act.get("start_date"))
        if d is not None and start <= d <= end and activity_duration_seconds(act) > 0:
            act_dates.add(d)
    matched = 0
    for ev in week_events:
        d = _parse_date(ev.get("start_date_local") or ev.get("start_date"))
        if d is not None and d in act_dates:
            matched += 1
    return {
        "planned_days": len(week_events),
        "matched_days": matched,
        "unmatched_planned": max(0, len(week_events) - matched),
    }


def intensity_load_per_hour(activities: list[dict[str, Any]], start: date, end: date) -> float | None:
    total_sec = 0
    total_tss = 0.0
    for act in activities:
        d = _parse_date(act.get("start_date_local") or act.get("start_date"))
        if d is None or d < start or d > end:
            continue
        sec = activity_duration_seconds(act)
        if sec <= 0:
            continue
        tss = act.get("icu_training_load") or act.get("training_load")
        if tss is not None:
            total_tss += float(tss)
        total_sec += sec
    if total_sec <= 0 or total_tss <= 0:
        return None
    hours = total_sec / 3600.0
    return round(total_tss / hours, 1)


def summarize_wellness_trends(rows: list[dict[str, Any]], limit: int = 7) -> str:
    if not rows:
        return ""
    recent = rows[-limit:]
    last = recent[-1]
    ctl = last.get("ctl") or last.get("fitness")
    atl = last.get("atl") or last.get("fatigue")
    ramp = last.get("rampRate") or last.get("ramp_rate")
    parts: list[str] = []
    if ctl is not None:
        parts.append(f"CTL={ctl}")
    if atl is not None:
        parts.append(f"ATL={atl}")
    if ramp is not None:
        parts.append(f"ramp={ramp}")
    if not parts:
        return "wellness uten CTL/ATL i Intervals"
    return ", ".join(parts)
