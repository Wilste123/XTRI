from datetime import date

from coach_bot.aggregates import build_training_snapshot, plan_vs_actual
from coach_bot.coach_insights import build_coach_brief, resolve_week_plan
from pathlib import Path
import json

FIXTURES = Path(__file__).parent / "fixtures"


def load_activities():
    return json.loads((FIXTURES / "activities_sample.json").read_text())


def test_resolve_baseline_when_not_done():
    status = "baseline ikke fullført ennå"
    ref = resolve_week_plan(date(2026, 9, 19), status)
    assert ref.label == "baseline-uke"


def test_plan_vs_actual_counts():
    acts = load_activities()
    snap = build_training_snapshot(acts, as_of=date(2026, 9, 18))
    pva = plan_vs_actual([], snap.last_7_days, date(2026, 9, 12), date(2026, 9, 18))
    assert pva.completed_activity_count >= 1


def test_coach_brief_contains_days_to_race():
    acts = load_activities()
    snap = build_training_snapshot(acts, as_of=date(2026, 9, 18))
    brief = build_coach_brief(
        snap,
        {"events": [], "wellness": [{"ctl": 20, "atl": 25}]},
        "baseline ikke fullført",
    )
    assert "COACH_BRIEF" in brief
    assert "Dager til Lofoten" in brief
    assert "CTL=20" in brief


def test_coach_brief_advanced_section():
    acts = load_activities()
    snap = build_training_snapshot(acts, as_of=date(2026, 9, 18))
    brief = build_coach_brief(
        snap,
        {"events": [], "wellness": [{"ctl": 20, "atl": 25}], "activities": acts},
        "baseline ikke fullført",
        include_advanced=True,
    )
    assert "ADVANCED" in brief
    assert "ACWR" in brief
