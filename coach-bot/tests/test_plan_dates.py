from datetime import date

from coach_bot.plan_dates import parse_plan_start_date


def test_parse_start_planen_dd_mm():
    as_of = date(2026, 9, 20)
    assert parse_plan_start_date("start planen 20-09", as_of) == date(2026, 9, 20)


def test_parse_iso_in_message():
    assert parse_plan_start_date("synk fra 2026-09-22", date(2026, 9, 20)) == date(
        2026, 9, 22
    )


def test_no_date_returns_none():
    assert parse_plan_start_date("synk kalender", date(2026, 9, 20)) is None
