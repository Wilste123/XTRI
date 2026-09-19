"""Tests for coach state persistence."""

from pathlib import Path

from coach_bot.state_store import StateStore


def test_bootstrap_and_new_activity(tmp_path: Path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    assert not store.is_bootstrapped()
    store.mark_bootstrapped(["1", "2"])
    assert store.is_bootstrapped()
    assert store.unseen_activity_ids(["1", "2"]) == []
    assert store.unseen_activity_ids(["1", "2", "3"]) == ["3"]
    store.mark_notified("3")
    assert store.unseen_activity_ids(["1", "2", "3"]) == []
