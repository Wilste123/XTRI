from coach_bot.athlete_thresholds import AthleteThresholds, SportThresholds, parse_athlete_payload
from coach_bot.intervals_workout_syntax import estimate_workout_minutes, validate_workout_syntax
from coach_bot.workout_builder import build_workout, enrich_event_dict, infer_session_type


def test_parse_athlete_ftp():
    th = parse_athlete_payload({"icu_ftp": 250, "icu_lthr": 171, "max_heartrate": 190})
    assert th.ride.ftp == 250
    assert th.ride.lthr == 171
    assert "250" in th.format_block()


def test_validate_threshold_syntax():
    b = build_workout("threshold_ride")
    assert b is not None
    text = b.workout_text
    val = validate_workout_syntax(text)
    assert val.ok
    assert val.estimated_minutes >= 60
    assert "Warmup" in text
    assert "Active" in text
    assert text.count("- 8m 85%-90% HR") == 6
    assert "6x" not in text
    assert b.planned_load > 0


def test_estimate_repeat_block():
    text = """- 10m 65% HR

Main set 6x
- 8m 85% HR
- 3m recovery at 65% HR
"""
    assert estimate_workout_minutes(text) == 10 + 6 * (8 + 3)


def test_build_easy_ride():
    b = build_workout("easy_ride", duration_min=45)
    assert b is not None
    assert "45m" in b.workout_text
    assert b.sport_type == "Ride"


def test_infer_session_types():
    assert infer_session_type("20 min jevn løp test", "Run") == "test_run_20"
    assert infer_session_type("steady sykkel terskel", "Ride") == "threshold_ride"


def test_enrich_event_adds_syntax():
    ev = {
        "type": "Ride",
        "name": "steady sykkel 70 min",
        "description": "Terskel",
        "planned_duration": 4200,
    }
    out = enrich_event_dict(ev, phase="Base_0")
    assert "Warmup" in out["description"]
    assert out.get("moving_time", 0) > 0
    assert "Main set" in out["description"] or "65% HR" in out["description"]
