"""Poll Intervals for new activities and push coach feedback."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from coach_bot.config import Settings
from coach_bot.intervals_client import IntervalsClient, activity_id
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.slack_notifier import SlackNotifier
from coach_bot.state_store import StateStore

logger = logging.getLogger(__name__)


class ActivityWatcher:
    def __init__(
        self,
        settings: Settings,
        intervals: IntervalsClient,
        orchestrator: CoachOrchestrator,
        notifier: SlackNotifier,
        state: StateStore,
    ) -> None:
        self._settings = settings
        self._intervals = intervals
        self._orchestrator = orchestrator
        self._notifier = notifier
        self._state = state
        self._timer: threading.Timer | None = None
        self._stop = threading.Event()

    def _in_quiet_hours(self) -> bool:
        tz = ZoneInfo(self._settings.tz)
        now = datetime.now(tz)
        hour = now.hour
        start = self._settings.quiet_hours_start
        end = self._settings.quiet_hours_end
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def _recent_activity_ids(self) -> list[str]:
        today = self._intervals.today()
        oldest = today - timedelta(days=2)
        activities = self._intervals.get_activities(oldest, today)
        ids: list[str] = []
        for act in activities:
            aid = activity_id(act)
            if aid:
                ids.append(aid)
        return ids

    def bootstrap_if_needed(self) -> None:
        if self._state.is_bootstrapped():
            return
        ids = self._recent_activity_ids()
        self._state.mark_bootstrapped(ids)
        logger.info("Bootstrapped activity state with %s recent ids", len(ids))

    def poll_once(self) -> None:
        self.bootstrap_if_needed()
        ids = self._recent_activity_ids()
        new_ids = self._state.unseen_activity_ids(ids)
        if not new_ids:
            return
        if self._in_quiet_hours():
            logger.info("Skipping %s new activities during quiet hours", len(new_ids))
            return
        for aid in new_ids:
            try:
                text = self._orchestrator.run_post_workout(aid)
                header = f"*Ny økt registrert* (activity `{aid}`)\n\n"
                self._notifier.broadcast(header + text)
                self._state.mark_notified(aid)
            except Exception:
                logger.exception("Post-workout notify failed for %s", aid)

    def _tick(self) -> None:
        if self._stop.is_set():
            return
        try:
            self.poll_once()
        except Exception:
            logger.exception("Activity poll failed")
        self._schedule_next()

    def _schedule_next(self) -> None:
        if self._stop.is_set():
            return
        delay = max(1, self._settings.activity_poll_minutes) * 60
        self._timer = threading.Timer(delay, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def start(self) -> None:
        self.bootstrap_if_needed()
        self._schedule_next()
        logger.info(
            "Activity watcher every %s min",
            self._settings.activity_poll_minutes,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._timer:
            self._timer.cancel()
