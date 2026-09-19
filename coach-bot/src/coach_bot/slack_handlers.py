"""Slack DM handlers (Socket Mode)."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from slack_bolt import App
from slack_sdk import WebClient

from coach_bot.config import Settings
from coach_bot.errors import friendly_coach_error
from coach_bot.orchestrator import CoachOrchestrator

logger = logging.getLogger(__name__)


def _run_in_thread(
    client: WebClient,
    channel: str,
    thread_ts: str | None,
    fn: Callable[[], str],
) -> None:
    try:
        result = fn()
        client.chat_postMessage(
            channel=channel,
            text=result,
            thread_ts=thread_ts,
        )
    except Exception as e:
        logger.exception("Coach DM failed")
        client.chat_postMessage(
            channel=channel,
            text=friendly_coach_error(e),
            thread_ts=thread_ts,
        )


def register_handlers(app: App, orchestrator: CoachOrchestrator, settings: Settings) -> None:
    allowed = settings.allowed_user_id_set

    def check_user(user_id: str) -> bool:
        if not allowed:
            return True
        return user_id in allowed

    @app.event("message")
    def on_dm_message(event, client: WebClient, say):
        if event.get("channel_type") != "im":
            return
        if event.get("bot_id") or event.get("subtype"):
            return

        user_id = event.get("user") or ""
        if not check_user(user_id):
            say("Du har ikke tilgang til denne coach-boten.")
            return

        text = (event.get("text") or "").strip()
        if not text:
            return

        channel = event["channel"]
        thread_ts = event.get("thread_ts") or event.get("ts")

        try:
            client.reactions_add(channel=channel, timestamp=event["ts"], name="hourglass_flowing_sand")
        except Exception:
            pass

        def work() -> str:
            return orchestrator.run_chat(text)

        threading.Thread(
            target=_run_in_thread,
            args=(client, channel, thread_ts, work),
            daemon=True,
        ).start()
