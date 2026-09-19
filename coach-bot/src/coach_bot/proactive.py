"""Proactive Slack messages (morning / weekly briefing)."""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient

from coach_bot.config import Settings
from coach_bot.errors import friendly_coach_error
from coach_bot.orchestrator import CoachOrchestrator

logger = logging.getLogger(__name__)


def _open_dm_channel(client: WebClient, user_id: str) -> str:
    resp = client.conversations_open(users=user_id)
    return resp["channel"]["id"]


def _send_to_users(
    client: WebClient,
    user_ids: list[str],
    text: str,
    label: str,
) -> None:
    for uid in user_ids:
        try:
            channel = _open_dm_channel(client, uid)
            client.chat_postMessage(channel=channel, text=text)
        except Exception as e:
            logger.exception("%s failed for %s", label, uid)
            try:
                channel = _open_dm_channel(client, uid)
                client.chat_postMessage(
                    channel=channel,
                    text=f"{label} feilet: {friendly_coach_error(e)}",
                )
            except Exception:
                pass


def _send_morning_briefing(
    client: WebClient,
    orchestrator: CoachOrchestrator,
    user_ids: list[str],
) -> None:
    text = orchestrator.run_morning_briefing()
    _send_to_users(client, user_ids, text, "Morgenbriefing")


def _send_weekly_briefing(
    client: WebClient,
    orchestrator: CoachOrchestrator,
    user_ids: list[str],
) -> None:
    text = orchestrator.run_weekly_briefing()
    _send_to_users(client, user_ids, text, "Ukebriefing")


def start_proactive_schedulers(
    settings: Settings,
    client: WebClient,
    orchestrator: CoachOrchestrator,
) -> BackgroundScheduler | None:
    user_ids = list(settings.allowed_user_id_set)
    if not settings.morning_briefing_enabled and not settings.weekly_briefing_enabled:
        return None
    if not user_ids:
        logger.warning("Proactive briefing enabled but ALLOWED_SLACK_USER_IDS is empty")
        return None

    tz = ZoneInfo(settings.tz)
    scheduler = BackgroundScheduler(timezone=tz)

    if settings.morning_briefing_enabled:
        scheduler.add_job(
            _send_morning_briefing,
            trigger="cron",
            hour=settings.morning_briefing_hour,
            minute=settings.morning_briefing_minute,
            args=[client, orchestrator, user_ids],
            id="morning_briefing",
            replace_existing=True,
        )
        logger.info(
            "Morning briefing at %02d:%02d %s",
            settings.morning_briefing_hour,
            settings.morning_briefing_minute,
            settings.tz,
        )

    if settings.weekly_briefing_enabled:
        scheduler.add_job(
            _send_weekly_briefing,
            trigger="cron",
            day_of_week=settings.weekly_briefing_weekday,
            hour=settings.weekly_briefing_hour,
            minute=settings.weekly_briefing_minute,
            args=[client, orchestrator, user_ids],
            id="weekly_briefing",
            replace_existing=True,
        )
        logger.info(
            "Weekly briefing weekday=%s %02d:%02d %s",
            settings.weekly_briefing_weekday,
            settings.weekly_briefing_hour,
            settings.weekly_briefing_minute,
            settings.tz,
        )

    scheduler.start()
    return scheduler


def start_morning_scheduler(
    settings: Settings,
    client: WebClient,
    orchestrator: CoachOrchestrator,
) -> BackgroundScheduler | None:
    return start_proactive_schedulers(settings, client, orchestrator)
