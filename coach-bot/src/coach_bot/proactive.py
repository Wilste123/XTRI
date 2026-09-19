"""Proactive Slack messages (morning briefing)."""

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


def _send_morning_briefing(
    client: WebClient,
    orchestrator: CoachOrchestrator,
    user_ids: list[str],
) -> None:
    for uid in user_ids:
        try:
            channel = _open_dm_channel(client, uid)
            text = orchestrator.run_morning_briefing()
            client.chat_postMessage(channel=channel, text=text)
        except Exception as e:
            logger.exception("Morning briefing failed for %s", uid)
            try:
                channel = _open_dm_channel(client, uid)
                client.chat_postMessage(
                    channel=channel,
                    text=f"Morgenbriefing feilet: {friendly_coach_error(e)}",
                )
            except Exception:
                pass


def start_morning_scheduler(
    settings: Settings,
    client: WebClient,
    orchestrator: CoachOrchestrator,
) -> BackgroundScheduler | None:
    if not settings.morning_briefing_enabled:
        return None

    user_ids = list(settings.allowed_user_id_set)
    if not user_ids:
        logger.warning("MORNING_BRIEFING_ENABLED but ALLOWED_SLACK_USER_IDS is empty")
        return None

    tz = ZoneInfo(settings.tz)
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        _send_morning_briefing,
        trigger="cron",
        hour=settings.morning_briefing_hour,
        minute=settings.morning_briefing_minute,
        args=[client, orchestrator, user_ids],
        id="morning_briefing",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Morning briefing scheduled at %02d:%02d %s",
        settings.morning_briefing_hour,
        settings.morning_briefing_minute,
        settings.tz,
    )
    return scheduler
