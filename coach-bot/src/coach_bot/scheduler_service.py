"""Scheduled proactive coach messages."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from coach_bot.config import Settings
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.slack_notifier import SlackNotifier

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(
        self,
        settings: Settings,
        orchestrator: CoachOrchestrator,
        notifier: SlackNotifier,
    ) -> None:
        self._settings = settings
        self._orchestrator = orchestrator
        self._notifier = notifier
        self._scheduler = BackgroundScheduler(timezone=settings.tz)

    def _send_morning(self) -> None:
        try:
            text = self._orchestrator.run_morning_brief()
            self._notifier.broadcast(f"*God morgen – dagens coach*\n\n{text}")
        except Exception:
            logger.exception("Morning brief failed")

    def _send_weekly(self) -> None:
        try:
            text = self._orchestrator.run_weekly_brief()
            self._notifier.broadcast(f"*Ukentlig oppsummering*\n\n{text}")
        except Exception:
            logger.exception("Weekly brief failed")

    def start(self) -> None:
        self._scheduler.add_job(
            self._send_morning,
            CronTrigger(
                hour=self._settings.morning_brief_hour,
                minute=self._settings.morning_brief_minute,
            ),
            id="morning_brief",
            replace_existing=True,
        )
        if self._settings.weekly_brief_enabled:
            self._scheduler.add_job(
                self._send_weekly,
                CronTrigger(
                    day_of_week=self._settings.weekly_brief_weekday,
                    hour=self._settings.weekly_brief_hour,
                    minute=self._settings.weekly_brief_minute,
                ),
                id="weekly_brief",
                replace_existing=True,
            )
        self._scheduler.start()
        logger.info(
            "Scheduler: morning %02d:%02d %s",
            self._settings.morning_brief_hour,
            self._settings.morning_brief_minute,
            self._settings.tz,
        )

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
