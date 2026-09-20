from coach_bot.intervals_event import finalize_workout_event
from coach_bot.intervals_workout_syntax import api_workout_description, extract_workout_syntax


_THRESHOLD = """Warmup
- 25m 65% HR

6x
- 8m 85%-90% HR
- 3m 65%-70% HR

Cooldown
- 15m 55% HR
"""


def test_api_description_strips_coach_prose():
    mixed = _THRESHOLD + "\n\n20 min effektiv nedkjøring. Lett tråkk."
    assert "nedkjøring" not in api_workout_description(mixed)
    assert "Warmup" in api_workout_description(mixed)


def test_finalize_sets_load_and_moving_time():
    ev = finalize_workout_event(
        {
            "category": "WORKOUT",
            "type": "Ride",
            "description": _THRESHOLD,
            "name": "Test",
        }
    )
    assert ev["description"].startswith("Warmup")
    assert ev.get("moving_time", 0) > 0
    assert ev.get("icu_training_load", 0) > 0
    assert ev.get("target") == "HR"
    assert ev.get("workout_doc") == {}


def test_extract_workout_syntax_keeps_sections():
    s = extract_workout_syntax(_THRESHOLD)
    assert "Warmup" in s
    assert "6x" in s
    assert "Cooldown" in s
