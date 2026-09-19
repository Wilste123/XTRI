"""Persistent state for activity dedup and DM channel cache."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {
                "bootstrapped": False,
                "seen_activity_ids": [],
                "notified_activity_ids": [],
                "dm_channels": {},
            }
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        data.setdefault("bootstrapped", False)
        data.setdefault("seen_activity_ids", [])
        data.setdefault("notified_activity_ids", [])
        data.setdefault("dm_channels", {})
        return data

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def is_bootstrapped(self) -> bool:
        with self._lock:
            return bool(self._load()["bootstrapped"])

    def mark_bootstrapped(self, activity_ids: list[str]) -> None:
        with self._lock:
            data = self._load()
            seen = set(data["seen_activity_ids"])
            seen.update(activity_ids)
            data["seen_activity_ids"] = sorted(seen)
            data["bootstrapped"] = True
            self._save(data)

    def unseen_activity_ids(self, current_ids: list[str]) -> list[str]:
        with self._lock:
            data = self._load()
            seen = set(data["seen_activity_ids"])
            notified = set(data["notified_activity_ids"])
            return [i for i in current_ids if i not in seen and i not in notified]

    def mark_notified(self, activity_id: str) -> None:
        with self._lock:
            data = self._load()
            seen = set(data["seen_activity_ids"])
            notified = set(data["notified_activity_ids"])
            seen.add(activity_id)
            notified.add(activity_id)
            data["seen_activity_ids"] = sorted(seen)
            data["notified_activity_ids"] = sorted(notified)
            self._save(data)

    def get_dm_channel(self, user_id: str) -> str | None:
        with self._lock:
            ch = self._load()["dm_channels"].get(user_id)
            return str(ch) if ch else None

    def set_dm_channel(self, user_id: str, channel_id: str) -> None:
        with self._lock:
            data = self._load()
            data["dm_channels"][user_id] = channel_id
            self._save(data)
