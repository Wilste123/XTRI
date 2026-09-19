"""Tests for activity id extraction."""

from coach_bot.intervals_client import activity_id


def test_activity_id_prefers_id():
    assert activity_id({"id": 123, "icu_activity_id": 456}) == "123"


def test_activity_id_fallback():
    assert activity_id({"icu_activity_id": 789}) == "789"


def test_activity_id_missing():
    assert activity_id({}) == ""
