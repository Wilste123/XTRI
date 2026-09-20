from datetime import date
from pathlib import Path

from coach_bot.intervals_planner import parse_single_workout_request, parse_week_plan_table

BASELINE = Path(__file__).resolve().parents[2] / "LOFOTEN-2027" / "ukeplan" / "baseline-uke.md"

SAMPLE = """
| Dag | Økt | Varighet |
| --- | --- | ---: |
| Man | Styrke A | 35 min |
| Tir | Løp 40 min lett | 40 min |
| Søn | Fri | 0 min |
"""


def test_parse_week_plan_table():
    events = parse_week_plan_table(SAMPLE, date(2026, 9, 14))
    assert len(events) == 2
    assert events[0]["type"] in ("Workout", "Run")


def test_parse_single_workout():
    ev = parse_single_workout_request("legg inn løp 45 min på tirsdag", date(2026, 9, 16))
    assert ev is not None
    assert ev["planned_duration"] == 45 * 60


def test_parse_real_baseline_week():
    md = BASELINE.read_text(encoding="utf-8")
    events = parse_week_plan_table(md, date(2026, 9, 14))
    assert len(events) >= 6
    names = " ".join(e["name"].lower() for e in events)
    assert "løp" in names or "jogg" in names or "jevn" in names
