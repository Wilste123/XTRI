from coach_bot.slack_handlers import RecentEvents, event_key


def test_recent_events_dedupes():
    seen = RecentEvents()
    assert seen.seen("abc") is False  # first time
    assert seen.seen("abc") is True  # duplicate
    assert seen.seen("def") is False


def test_recent_events_ignores_empty_key():
    seen = RecentEvents()
    assert seen.seen(None) is False
    assert seen.seen(None) is False  # None is never considered a duplicate


def test_recent_events_evicts_oldest():
    seen = RecentEvents(capacity=2)
    assert seen.seen("a") is False
    assert seen.seen("b") is False
    assert seen.seen("c") is False  # cache now {b, c}; "a" evicted
    assert seen.seen("a") is False  # "a" was evicted -> treated as new; evicts "b"
    assert seen.seen("c") is True  # "c" still remembered


def test_event_key_prefers_client_msg_id():
    assert event_key({"client_msg_id": "x", "ts": "1.2", "channel": "D1"}) == "x"


def test_event_key_falls_back_to_channel_ts():
    assert event_key({"ts": "1700.5", "channel": "D1"}) == "D1:1700.5"


def test_event_key_none_when_no_ids():
    assert event_key({}) is None
