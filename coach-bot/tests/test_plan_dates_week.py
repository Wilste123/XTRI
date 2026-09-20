from datetime import date

from coach_bot.plan_dates import calendar_week_range


def test_next_week_from_sunday():
    # 2026-09-20 is Sunday → neste uke = man 21. – søn 27.
    start, end = calendar_week_range(date(2026, 9, 20), "next_week")
    assert start == date(2026, 9, 21)
    assert end == date(2026, 9, 27)
