"""HTTP client for intervals.icu API."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from coach_bot.config import Settings


class IntervalsClient:
    def __init__(self, settings: Settings) -> None:
        self._athlete_id = settings.intervals_athlete_id
        self._base = settings.intervals_base_url.rstrip("/")
        self._tz = settings.tz
        self._client = httpx.Client(
            base_url=self._base,
            auth=("API_KEY", settings.intervals_api_key),
            timeout=60.0,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def _date_param(self, d: date) -> str:
        return d.isoformat()

    def get_activities(
        self,
        oldest: date,
        newest: date,
        fields: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "oldest": self._date_param(oldest),
            "newest": self._date_param(newest),
        }
        if fields:
            params["fields"] = fields
        r = self._client.get(
            f"/athlete/{self._athlete_id}/activities",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("activities") or data.get("data") or []

    def get_events(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        params = {
            "oldest": self._date_param(oldest),
            "newest": self._date_param(newest),
        }
        r = self._client.get(
            f"/athlete/{self._athlete_id}/events.json",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("events") or data.get("data") or []

    def get_wellness(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        params = {
            "oldest": self._date_param(oldest),
            "newest": self._date_param(newest),
        }
        r = self._client.get(
            f"/athlete/{self._athlete_id}/wellness.json",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("wellness") or data.get("data") or []

    def today(self) -> date:
        return datetime.now(ZoneInfo(self._tz)).date()

    def fetch_coach_bundle(self, activity_days: int = 28) -> dict[str, Any]:
        today = self.today()
        oldest_act = today - timedelta(days=activity_days - 1)
        oldest_ev = today - timedelta(days=14)
        newest_ev = today + timedelta(days=14)

        activities = self.get_activities(oldest_act, today)
        events = self.get_events(oldest_ev, newest_ev)
        wellness = self.get_wellness(today - timedelta(days=27), today)

        return {
            "activities": activities,
            "events": events,
            "wellness": wellness,
        }
