from datetime import date

from coach_bot.workout_extract import (
    asks_workout_for_calendar,
    extract_workout_from_text,
    is_commit_message,
    wants_intervals_write,
)

PROPOSAL = """
## Plan for i morgen (2026-09-20)
### Anbefalt økt
- **Type:** Sykkelintervall
- **Varighet:** 1 time
- 10 min oppvarming, 5 x 3 min intervaller, 10 min nedkjøring
"""


def test_commit_phrases():
    assert is_commit_message("legg den inn i intervals")
    assert is_commit_message("ja")
    assert wants_intervals_write("legge inn en økt for i morgen i intervals")


def test_asks_workout_for_calendar():
    msg = "Kan du legge inn en økt for i morgen i intervals?"
    assert asks_workout_for_calendar(msg)


def test_extract_from_proposal():
    ev = extract_workout_from_text(PROPOSAL, as_of=date(2026, 9, 19))
    assert ev is not None
    assert ev["type"] == "Ride"
    assert ev["planned_duration"] == 60 * 60
    assert (ev["start_date_local"] or "").startswith("2026-09-20")
