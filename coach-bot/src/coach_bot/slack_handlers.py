"""Slack DM handlers (Socket Mode)."""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Callable

from slack_bolt import App
from slack_sdk import WebClient

from coach_bot.config import Settings
from coach_bot.errors import friendly_coach_error
from coach_bot.coach_reply import CoachReply
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.slack_post import post_coach_reply

logger = logging.getLogger(__name__)

_ANY_TEXT = re.compile(r".+", re.DOTALL)


def _is_dm(event: dict[str, Any]) -> bool:
    if event.get("channel_type") == "im":
        return True
    channel = event.get("channel") or ""
    return isinstance(channel, str) and channel.startswith("D")


def _run_in_thread(
    client: WebClient,
    channel: str,
    thread_ts: str | None,
    fn: Callable[[], CoachReply],
) -> None:
    try:
        result = fn()
        post_coach_reply(client, channel, result, thread_ts=thread_ts)
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

    @app.middleware
    def log_events(body, next):
        if body.get("type") == "events_api":
            ev = body.get("event") or {}
            logger.info(
                "Slack event: type=%s channel=%s channel_type=%s user=%s subtype=%s",
                ev.get("type"),
                ev.get("channel"),
                ev.get("channel_type"),
                ev.get("user"),
                ev.get("subtype"),
            )
        return next()

    def handle_dm_text(event: dict[str, Any], client: WebClient, say) -> None:
        if not _is_dm(event):
            logger.debug("Ignored non-DM message channel=%s", event.get("channel"))
            return
        if event.get("bot_id") or event.get("subtype"):
            logger.debug("Ignored bot/subtype message subtype=%s", event.get("subtype"))
            return

        user_id = event.get("user") or ""
        if not check_user(user_id):
            say("Du har ikke tilgang til denne coach-boten.")
            return

        text = (event.get("text") or "").strip()
        if not text:
            return

        channel = event["channel"]
        # Ikke bruk message ts som thread_ts i vanlig DM – svar kan bli skjult i tråd
        thread_ts = event.get("thread_ts")

        logger.info("DM from %s: %s", user_id, text[:80])

        if text.lower() in ("ping", "test"):
            say("Pong – coach-bot er på og mottar DM.")
            return

        say("Henter data fra Intervals og repo – et øyeblikk…")

        try:
            client.reactions_add(
                channel=channel,
                timestamp=event["ts"],
                name="hourglass_flowing_sand",
            )
        except Exception:
            pass

        def work() -> CoachReply:
            return orchestrator.run_chat(text, user_id=user_id)

        threading.Thread(
            target=_run_in_thread,
            args=(client, channel, thread_ts, work),
            daemon=True,
        ).start()

    @app.message(_ANY_TEXT)
    def on_message_shortcut(message, client: WebClient, say):
        handle_dm_text(message, client, say)
