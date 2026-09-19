from coach_bot.intent import (
    Intent,
    asks_capabilities,
    asks_for_plan_sync,
    detect_intent,
    strip_log_prefix,
    wants_week_plan_write,
)


def test_detect_status():
    assert detect_intent("hvordan ligger jeg an?") == Intent.STATUS


def test_detect_tomorrow():
    assert detect_intent("hva skal jeg gjøre i morgen?") == Intent.TOMORROW


def test_detect_week():
    assert detect_intent("ukestatus") == Intent.WEEK


def test_detect_log():
    assert detect_intent("logg: kne 3/10") == Intent.LOG
    assert strip_log_prefix("logg: kne 3/10") == "kne 3/10"


def test_grafer_og_treningsplan():
    msg = "kan du ikke lage grafer og legge inn treningsplaner?"
    assert asks_capabilities(msg)
    assert asks_for_plan_sync(msg)
    assert detect_intent(msg) == Intent.CHART


def test_week_plan_phrases():
    msg = "legg inn ukeplanen i intervals"
    assert asks_for_plan_sync(msg)
    assert wants_week_plan_write(msg)
