from datetime import date

from coach_bot.aggregates import acwr_from_wellness, consistency_stats, plan_adherence

from pathlib import Path
import json

FIXTURES = Path(__file__).parent / "fixtures"


def test_acwr():
    ratio = acwr_from_wellness([{"ctl": 40, "atl": 50}])
    assert ratio == 1.25


def test_consistency_and_adherence():
    acts = json.loads((FIXTURES / "activities_sample.json").read_text())
    stats = consistency_stats(acts, date(2026, 9, 18))
    assert stats["activity_days"] >= 1
    adh = plan_adherence([], acts, date(2026, 9, 12), date(2026, 9, 18))
    assert adh["planned_days"] == 0
