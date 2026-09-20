from coach_bot.intent import (
    Intent,
    asks_capabilities,
    asks_for_charts,
    asks_for_plan_sync,
    asks_to_create_week_plan,
    detect_intent,
    strip_log_prefix,
    wants_week_plan_write,
)


def test_visual_request_is_chart():
    assert asks_for_charts("kan du lage en visuell fremstilling av tiden fremover")
    assert asks_for_charts("vis meg et diagram")


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


def test_rosa_graf_not_capabilities_with_plan():
    msg = "kan du lage en rosa graf for uken som har gått?"
    assert asks_for_charts(msg)
    assert not asks_for_plan_sync(msg)
    assert not asks_capabilities(msg)
    assert detect_intent(msg) == Intent.CHART


def test_lag_ukeplan_create_flag():
    msg = "lag en ukeplan og legg inn ukeplanen i intervals"
    assert asks_to_create_week_plan(msg)
    assert wants_week_plan_write(msg)


def test_ukeplan_sync_base0_not_capabilities_template():
    msg = "Kan du lage ukeplan neste 7 dager sync base0"
    assert wants_week_plan_write(msg) or asks_for_plan_sync(msg)
    assert not asks_capabilities(msg)
