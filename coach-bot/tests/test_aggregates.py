import json
from datetime import date

import pytest
from pathlib import Path

from coach_bot.aggregates import (
    build_training_snapshot,
    classify_sport,
    filter_events_for_date,
    summarize_period,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_activities():
    return json.loads((FIXTURES / "activities_sample.json").read_text())


def test_classify_sport():
    assert classify_sport({"type": "VirtualRide"}) == "bike"
    assert classify_sport({"type": "Run"}) == "run"
    assert classify_sport({"type": "Swim"}) == "swim"


def test_summarize_period_filters_dates():
    acts = load_activities()
    start = date(2026, 9, 16)
    end = date(2026, 9, 18)
    s = summarize_period(acts, start, end)
    assert s.activity_count == 3
    assert s.by_discipline_hours.get("run") == pytest.approx(2400 / 3600)
    assert s.by_discipline_hours.get("bike") == 1.0
    assert s.by_discipline_hours.get("swim") == pytest.approx(2700 / 3600)


def test_build_training_snapshot_volume_change():
    acts = load_activities()
    snap = build_training_snapshot(acts, tz="Europe/Oslo", as_of=date(2026, 9, 18))
    assert snap.last_7_days.activity_count >= 3
    assert snap.recent_activities[0]["type"] in ("run", "bike", "swim")


def test_filter_events_for_date():
    events = [
        {"start_date_local": "2026-09-19T08:00:00", "name": "Long ride"},
        {"start_date_local": "2026-09-20T08:00:00", "name": "Run"},
    ]
    assert len(filter_events_for_date(events, date(2026, 9, 20))) == 1
