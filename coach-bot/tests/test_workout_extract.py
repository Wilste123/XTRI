from datetime import date

from coach_bot.workout_extract import (
    asks_workout_for_calendar,
    extract_week_plan_from_assistant,
    extract_week_plan_from_markdown_table,
    extract_week_plan_from_text,
    extract_workout_from_text,
    is_commit_message,
    is_commit_only_message,
    wants_full_plan,
    wants_intervals_write,
)

_MULTI_DAY_PLAN = """Her er planen for de neste dagene:
**19. september (i dag)**: Løpeøkt 45 min rolig.
**20. september**: Sykle 1 time lav intensitet.
**21. september**: Svøm 30 min teknikk.
**24. september**: Sykle 1.5 time med korte intervaller.
"""

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


def test_commit_typos_accepted():
    for t in ("js", "jaa", "jepp", "kjør", "ja takk", "ok"):
        assert is_commit_message(t), t


def test_wants_full_plan():
    assert wants_full_plan("legg inn hele planen")
    assert wants_full_plan("kan du legge inn disse i intervals?")
    assert not wants_full_plan("legg den inn i intervals")


def test_extract_week_plan_multiple_days():
    events = extract_week_plan_from_text(_MULTI_DAY_PLAN, as_of=date(2026, 9, 19))
    by_date = {e["start_date_local"][:10]: e for e in events}
    assert len(events) == 4
    assert by_date["2026-09-19"]["type"] == "Run"
    # «Sykle 1 time» -> Ride 60 min (ikke Workout/Coach-økt)
    assert by_date["2026-09-20"]["type"] == "Ride"
    assert by_date["2026-09-20"]["planned_duration"] == 60 * 60
    assert by_date["2026-09-21"]["type"] == "Swim"
    # «Sykle 1.5 time» -> 90 min (ikke 300)
    assert by_date["2026-09-24"]["planned_duration"] == 90 * 60


def test_extract_week_plan_needs_two_days():
    single = "**20. september**: Løp 45 min."
    assert len(extract_week_plan_from_text(single, as_of=date(2026, 9, 19))) == 1


_BASE0_TABLE = """
Ukeplan (2026-09-21 – 2026-09-27)

| Dag | Økt | Varighet | Intensitet | Hensikt |
| --- | --- | ---: | --- | --- |
| Man | Hvilepuls noteres. Valgfritt: lett styrke 20 min (aktivering) | 0–30 min | RPE 3–4 | Referanse |
| Tir | Oppvarming · **20 min jevn løp** (test) · nedjogg | 45–55 min | RPE 6–7 | Løp |
| Ons | drill · **8×100 m** · svøm | 45–60 min | RPE 5–7 | Svøm |
| Tor | Hvile **eller** sykkel 30–45 min rolig | 0–45 min | RPE 3–4 | Recovery |
| Fre | **20 min steady sykkel** | 60–75 min | RPE 6–7 | Sykkel |
| Lør | Sykkel 60–90 min · **10–15 min løp** (brick) | 75–105 min | RPE 4–5 | Brick |
| Søn | Fri / rolig gåtur | — | — | Rest |

Denne planen holder seg innenfor volummålet på 3–5 timer for uken.
"""


def test_extract_markdown_table_week_not_single_300min_sykkel():
    events = extract_week_plan_from_markdown_table(
        _BASE0_TABLE, as_of=date(2026, 9, 20)
    )
    assert len(events) >= 4
    dates = {(e["start_date_local"] or "")[:10] for e in events}
    assert "2026-09-22" in dates
    assert all(e["planned_duration"] <= 240 * 60 for e in events)
    bad = extract_workout_from_text(_BASE0_TABLE, as_of=date(2026, 9, 20))
    assert bad is None or bad["planned_duration"] < 300 * 60


def test_legg_den_inn_not_commit_only():
    assert not is_commit_only_message("legg den inn i intervalls")


def test_extract_week_plan_from_assistant_prefers_table():
    events = extract_week_plan_from_assistant(_BASE0_TABLE, as_of=date(2026, 9, 20))
    assert len(events) >= 4
