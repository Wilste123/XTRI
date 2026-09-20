from coach_bot.context_builder import _format_events
from coach_bot.event_duration import event_duration_minutes, format_event_duration


def test_planned_duration_seconds_to_minutes():
    ev = {"name": "Sykkel", "planned_duration": 3600}
    assert event_duration_minutes(ev) == 60
    assert format_event_duration(ev) == ", 60 min"


def test_format_events_uses_planned_duration():
    text = _format_events(
        [{"start_date_local": "2026-09-21T00:00:00", "name": "Sykkelintervall", "planned_duration": 3600}]
    )
    assert "60 min" in text
    assert "360 min" not in text
