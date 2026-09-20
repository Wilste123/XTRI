"""Generate Intervals.icu workout description text from templates and context."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from coach_bot.athlete_thresholds import AthleteThresholds
from coach_bot.intervals_planner import _detect_type, estimate_planned_load
from coach_bot.intervals_event import finalize_workout_event
from coach_bot.intervals_workout_syntax import validate_workout_syntax

SESSION_TYPES = frozenset(
    {
        "threshold_ride",
        "easy_ride",
        "recovery_ride",
        "test_run_20",
        "test_swim_100",
        "brick_ride_run",
        "easy_run",
        "easy_swim",
        "strength",
    }
)


@dataclass
class BuiltWorkout:
    name: str
    sport_type: str
    workout_text: str
    coach_notes: str
    target: str
    duration_min: int
    planned_load: int
    description: str


def infer_session_type(workout_cell: str, sport_type: str) -> str | None:
    low = (workout_cell or "").lower()
    if sport_type == "Ride":
        if any(k in low for k in ("terskel", "steady sykkel", "ftp", "intervall")):
            return "threshold_ride"
        if "brick" in low or ("sykkel" in low and "løp" in low):
            return "brick_ride_run"
        if any(k in low for k in ("hvile", "recovery", "valgfritt")):
            return "recovery_ride"
        return "easy_ride"
    if sport_type == "Run":
        if "20 min" in low or "test" in low or "jevn løp" in low:
            return "test_run_20"
        if "brick" in low or "løp" in low:
            return "easy_run"
        return "easy_run"
    if sport_type == "Swim":
        if "100" in low or "8×" in low or "8x" in low:
            return "test_swim_100"
        return "easy_swim"
    if sport_type == "Workout" or "styrke" in low:
        return "strength"
    return None


def _template_threshold_ride(reps: int = 6, work_min: int = 8, rec_min: int = 3) -> str:
    # Intervals: eksplisitte steg per rep (ikke «6x»-shorthand i UI)
    lines = ["Warmup", f"- 25m 65% HR", "", "Active"]
    for _ in range(reps):
        lines.append(f"- {work_min}m 85%-90% HR")
        lines.append(f"- {rec_min}m 65%-70% HR")
    lines.extend(["", "Cooldown", "- 15m 55% HR"])
    return "\n".join(lines)


def _template_easy_ride(minutes: int = 45) -> str:
    return f"Warmup\n- {minutes}m Z2 HR"


def _template_recovery_ride(minutes: int = 35) -> str:
    return f"- {minutes}m 60%-65% HR"


def _template_test_run_20() -> str:
    return (
        "Warmup\n"
        "- 10m 65% HR\n\n"
        "Active\n"
        "- 20m 85%-90% HR\n\n"
        "Cooldown\n"
        "- 10m 60% HR"
    )


def _template_test_swim_100() -> str:
    lines = ["Warmup", "- 15m easy swim", "", "Active"]
    for _ in range(8):
        lines.append("- 100m 85% Pace")
        lines.append("- 20s rest")
    lines.extend(["", "Cooldown", "- 10m easy swim"])
    return "\n".join(lines)


def _template_brick(ride_min: int = 75, run_min: int = 12) -> str:
    return (
        f"- {ride_min}m Z2 HR\n\n"
        f"- {run_min}m 70%-75% HR"
    )


def _template_easy_run(minutes: int = 40) -> str:
    return f"- {minutes}m Z2 HR"


def _template_easy_swim(minutes: int = 45) -> str:
    return f"- {minutes}m easy swim"


def _template_strength(minutes: int = 25) -> str:
    return f"- {minutes}m RPE 4"


def build_workout(
    session_type: str,
    *,
    sport: str = "bike",
    duration_min: int | None = None,
    thresholds: AthleteThresholds | None = None,
    phase: str = "Base_0",
    skeleton_hint: str = "",
    reps: int | None = None,
) -> BuiltWorkout | None:
    """Build structured Intervals workout text from a session template."""
    st = (session_type or "").strip().lower()
    if st not in SESSION_TYPES:
        return None

    sport_l = sport.lower()
    if sport_l in ("bike", "sykkel", "ride"):
        sport_type = "Ride"
        target = "HR"
    elif sport_l in ("run", "løp", "lop"):
        sport_type = "Run"
        target = "HR"
    elif sport_l in ("swim", "svøm", "svom"):
        sport_type = "Swim"
        target = "PACE"
    else:
        sport_type = "Workout"
        target = "HR"

    th = thresholds
    ftp_note = ""
    if th and th.ride.ftp and st == "threshold_ride":
        ftp_note = (
            f"FTP i Intervals: {th.ride.ftp} W. "
            "Terskeldrag typisk 95–102% FTP; her styrt med % HR til soner er kalibrert."
        )

    workout_text = ""
    coach_notes = skeleton_hint.strip()[:400] if skeleton_hint else ""
    name = "Coach-økt"

    if st == "threshold_ride":
        r = reps or (6 if "base" in phase.lower() else 6)
        workout_text = _template_threshold_ride(reps=r)
        name = f"Terskel sykkel {r}×8 min"
        coach_notes = " · ".join(p for p in (coach_notes, ftp_note) if p)
    elif st == "easy_ride":
        mins = duration_min or 50
        workout_text = _template_easy_ride(mins)
        name = f"Rolig sykkel {mins} min"
    elif st == "recovery_ride":
        mins = min(duration_min or 35, 45)
        workout_text = _template_recovery_ride(mins)
        name = f"Recovery sykkel {mins} min"
    elif st == "test_run_20":
        workout_text = _template_test_run_20()
        name = "Løptest 20 min jevn"
    elif st == "test_swim_100":
        workout_text = _template_test_swim_100()
        name = "Svøm 8×100 teknikk"
    elif st == "brick_ride_run":
        workout_text = _template_brick(
            ride_min=min(duration_min or 75, 105),
            run_min=12,
        )
        name = "Brick sykkel + løp"
    elif st == "easy_run":
        mins = duration_min or 45
        workout_text = _template_easy_run(mins)
        name = f"Rolig løp {mins} min"
    elif st == "easy_swim":
        mins = duration_min or 45
        workout_text = _template_easy_swim(mins)
        name = f"Svøm {mins} min"
    elif st == "strength":
        mins = min(duration_min or 25, 35)
        workout_text = _template_strength(mins)
        name = f"Styrke {mins} min"
        sport_type = "Workout"

    val = validate_workout_syntax(workout_text)
    if not val.ok:
        return None
    dur = val.estimated_minutes or duration_min or 45
    load = estimate_planned_load(dur, 6.5 if "threshold" in st else 4.5)
    from coach_bot.intervals_workout_syntax import api_workout_description

    return BuiltWorkout(
        name=name[:80],
        sport_type=sport_type,
        workout_text=workout_text,
        coach_notes=coach_notes,
        target=target,
        duration_min=dur,
        planned_load=load,
        description=api_workout_description(workout_text)[:4000],
    )


def enrich_event_dict(
    event: dict[str, Any],
    *,
    thresholds: AthleteThresholds | None = None,
    phase: str = "Base_0",
    skeleton_hint: str = "",
) -> dict[str, Any]:
    """Add Intervals workout syntax to a calendar event if missing."""
    desc = str(event.get("description") or "")
    if _looks_like_syntax(desc):
        return event

    sport_type = str(event.get("type") or "Workout")
    hint = skeleton_hint or event.get("name") or desc
    session = infer_session_type(hint, sport_type)
    if not session:
        return event

    dur_min = max(15, int((event.get("planned_duration") or 2700) // 60))
    sport_key = {"Ride": "bike", "Run": "run", "Swim": "swim"}.get(sport_type, "bike")
    built = build_workout(
        session,
        sport=sport_key,
        duration_min=dur_min,
        thresholds=thresholds,
        phase=phase,
        skeleton_hint=hint,
    )
    if not built:
        return event

    out = dict(event)
    out["name"] = built.name
    out["description"] = built.description
    out["planned_duration"] = built.duration_min * 60
    if built.target:
        out["target"] = built.target
    return finalize_workout_event(out)


def enrich_events_list(
    events: list[dict[str, Any]],
    *,
    intervals: Any = None,
    repo: Any = None,
) -> list[dict[str, Any]]:
    thresholds = None
    phase = "Base_0"
    if intervals is not None:
        try:
            thresholds = intervals.get_athlete_thresholds()
        except Exception:
            thresholds = None
    if repo is not None:
        try:
            phase = repo.detect_phase()
        except Exception:
            pass
    out: list[dict[str, Any]] = []
    for ev in events:
        hint = str(ev.get("name") or "") + " " + str(ev.get("description") or "")
        out.append(
            enrich_event_dict(
                ev,
                thresholds=thresholds,
                phase=phase,
                skeleton_hint=hint[:500],
            )
        )
    return out


def _looks_like_syntax(text: str) -> bool:
    if not text:
        return False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("-") and re.search(r"\d+\s*(m|min|h)\b", s, re.I):
            return True
        if re.match(r"^\d+\s*x\s*$", s, re.I) or s.lower().startswith("main set"):
            return True
    return False
