"""Extension ports for V2+ (stubs)."""

from __future__ import annotations

from typing import Protocol


class TrainingDataProvider(Protocol):
    def fetch_activities(self, oldest: str, newest: str) -> list: ...


class PlanProvider(Protocol):
    def fetch_events(self, oldest: str, newest: str) -> list: ...


class ProjectMemory(Protocol):
    def read_text(self, path: str) -> str: ...


class Notifier(Protocol):
    def send(self, user_id: str, text: str) -> None: ...


class Scheduler(Protocol):
    """V3: cron morning briefing."""

    def register_daily(self, hour: int, minute: int, callback: object) -> None: ...
