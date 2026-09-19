from coach_bot.intent import Intent, detect_intent, strip_log_prefix


def test_detect_status():
    assert detect_intent("hvordan ligger jeg an?") == Intent.STATUS


def test_detect_tomorrow():
    assert detect_intent("hva skal jeg gjøre i morgen?") == Intent.TOMORROW


def test_detect_week():
    assert detect_intent("ukestatus") == Intent.WEEK


def test_detect_log():
    assert detect_intent("logg: kne 3/10") == Intent.LOG
    assert strip_log_prefix("logg: kne 3/10") == "kne 3/10"
