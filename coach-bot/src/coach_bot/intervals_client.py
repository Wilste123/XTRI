"""HTTP client for intervals.icu API."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from coach_bot.config import Settings

logger = logging.getLogger(__name__)


class IntervalsClient:
    def __init__(self, settings: Settings) -> None:
        self._athlete_id = settings.intervals_athlete_id
        self._base = settings.intervals_base_url.rstrip("/")
        self._tz = settings.tz
        self._cache_ttl = settings.intervals_cache_ttl_seconds
        self._cache_key: tuple[int, date] | None = None
        self._cache_at: float = 0.0
        self._cache_bundle: dict[str, Any] | None = None
        self._cache_athlete: dict[str, Any] | None = None
        self._cache_athlete_at: float = 0.0
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

    def ping(self) -> None:
        """Lightweight auth check."""
        today = self.today()
        self.get_activities(today, today)

    def today(self) -> date:
        return datetime.now(ZoneInfo(self._tz)).date()

    def _fetch_bundle_uncached(self, activity_days: int) -> dict[str, Any]:
        today = self.today()
        oldest_act = today - timedelta(days=activity_days - 1)
        oldest_ev = today - timedelta(days=14)
        newest_ev = today + timedelta(days=14)
        wellness_oldest = today - timedelta(days=27)

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_act = pool.submit(self.get_activities, oldest_act, today)
            f_ev = pool.submit(self.get_events, oldest_ev, newest_ev)
            f_well = pool.submit(self.get_wellness, wellness_oldest, today)
            activities = f_act.result()
            events = f_ev.result()
            wellness = f_well.result()

        return {
            "activities": activities,
            "events": events,
            "wellness": wellness,
        }

    def fetch_coach_bundle(self, activity_days: int = 28) -> dict[str, Any]:
        today = self.today()
        key = (activity_days, today)
        now = time.monotonic()
        if (
            self._cache_bundle is not None
            and self._cache_key == key
            and (now - self._cache_at) < self._cache_ttl
        ):
            return self._cache_bundle

        bundle = self._fetch_bundle_uncached(activity_days)
        self._cache_key = key
        self._cache_at = now
        self._cache_bundle = bundle
        return bundle

    def invalidate_cache(self) -> None:
        self._cache_bundle = None
        self._cache_key = None
        self._cache_at = 0.0
        self._cache_athlete = None
        self._cache_athlete_at = 0.0

    def get_athlete(self) -> dict[str, Any]:
        """Fetch athlete profile (FTP, LTHR, etc.)."""
        now = time.monotonic()
        if self._cache_athlete is not None and (now - self._cache_athlete_at) < self._cache_ttl:
            return self._cache_athlete
        r = self._client.get(f"/athlete/{self._athlete_id}")
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            self._cache_athlete = data
        else:
            self._cache_athlete = {"data": data}
        self._cache_athlete_at = now
        return self._cache_athlete

    def get_athlete_thresholds(self):
        from coach_bot.athlete_thresholds import parse_athlete_payload

        return parse_athlete_payload(self.get_athlete())

    def bulk_upsert_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not events:
            return []
        from coach_bot.intervals_event import finalize_workout_events

        payload = finalize_workout_events(events)
        r = self._client.post(
            f"/athlete/{self._athlete_id}/events/bulk",
            params={"upsert": "true", "resolve": "true"},
            json=payload,
        )
        r.raise_for_status()
        self.invalidate_cache()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("events") or data.get("data") or []

    def delete_event(self, event_id: Any) -> None:
        r = self._client.delete(f"/athlete/{self._athlete_id}/events/{event_id}")
        r.raise_for_status()
        self.invalidate_cache()

    def create_event(self, event: dict[str, Any]) -> dict[str, Any]:
        created = self.bulk_upsert_events([event])
        if created:
            return created[0]
        r = self._client.post(
            f"/athlete/{self._athlete_id}/events",
            json=event,
        )
        r.raise_for_status()
        self.invalidate_cache()
        return r.json()
