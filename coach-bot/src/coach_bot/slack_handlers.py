"""Slack DM chat, optional slash commands, and app mentions."""

from __future__ import annotations

import logging
import threading
from typing import Callable

import httpx
from slack_bolt import App
from slack_sdk import WebClient

from coach_bot.config import Settings
from coach_bot.orchestrator import CoachOrchestrator

logger = logging.getLogger(__name__)


def _post_response(response_url: str, text: str) -> None:
    chunks: list[str] = []
    max_len = 12000
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    for i, chunk in enumerate(chunks):
        payload = {
            "response_type": "in_channel",
            "text": chunk if i == 0 else f"(fortsettelse {i + 1})\n{chunk}",
            "replace_original": i == 0,
        }
        try:
            r = httpx.post(response_url, json=payload, timeout=30.0)
            r.raise_for_status()
        except Exception as e:
            logger.exception("Failed to post to response_url: %s", e)


def _run_async_response_url(response_url: str, fn: Callable[[], str]) -> None:
    try:
        result = fn()
        _post_response(response_url, result)
    except Exception as e:
        logger.exception("Coach command failed")
        _post_response(
            response_url,
            f"Coach feilet: {e!s}. Sjekk logger og .env (Intervals/OpenAI).",
        )


def _run_async_dm(
    client: WebClient,
    channel: str,
    thread_ts: str | None,
    fn: Callable[[], str],
) -> None:
    try:
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="Tenker – henter Intervals og repo…",
        )
        result = fn()
        client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=result)
    except Exception as e:
        logger.exception("Coach DM failed")
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Coach feilet: {e!s}. Sjekk logger og .env.",
        )


def register_handlers(
    app: App,
    orchestrator: CoachOrchestrator,
    settings: Settings,
) -> None:
    allowed = settings.allowed_user_id_set
    client = WebClient(token=settings.slack_bot_token)

    def check_user(user_id: str) -> str | None:
        if allowed and user_id not in allowed:
            return "Du har ikke tilgang til denne coach-boten."
        return None

    def run_in_thread(channel: str, thread_ts: str | None, runner: Callable[[], str]) -> None:
        threading.Thread(
            target=_run_async_dm,
            args=(client, channel, thread_ts, runner),
            daemon=True,
        ).start()

    @app.event("message")
    def handle_dm_message(event, say, logger):  # noqa: ARG001
        if event.get("channel_type") != "im":
            return
        if event.get("bot_id") or event.get("subtype"):
            return
        user_id = event.get("user", "")
        denied = check_user(user_id)
        if denied:
            say(denied)
            return
        text = (event.get("text") or "").strip()
        if not text:
            return
        channel = event["channel"]
        thread_ts = event.get("thread_ts") or event.get("ts")
        run_in_thread(channel, thread_ts, lambda: orchestrator.run_chat(text))

    if settings.slack_enable_mentions:

        @app.event("app_mention")
        def handle_mention(event, say):
            user_id = event.get("user", "")
            denied = check_user(user_id)
            if denied:
                say(denied)
                return
            raw = event.get("text") or ""
            text = raw.split(">", 1)[-1].strip() if ">" in raw else raw.strip()
            if not text:
                text = "Gi en kort status."
            channel = event["channel"]
            thread_ts = event.get("thread_ts") or event.get("ts")
            run_in_thread(channel, thread_ts, lambda: orchestrator.run_chat(text))

    if not settings.slack_enable_slash:
        return

    def deferred(ack, command, runner: Callable[[], str]) -> None:
        user_id = command.get("user_id", "")
        denied = check_user(user_id)
        if denied:
            ack(denied)
            return
        ack("Henter data fra Intervals og repo – et øyeblikk…")
        url = command["response_url"]
        threading.Thread(
            target=_run_async_response_url,
            args=(url, runner),
            daemon=True,
        ).start()

    @app.command("/status")
    def status_cmd(ack, command):
        deferred(ack, command, orchestrator.run_status)

    @app.command("/imorgen")
    def imorgen_cmd(ack, command):
        deferred(ack, command, orchestrator.run_imorgen)

    @app.command("/ukestatus")
    def ukestatus_cmd(ack, command):
        deferred(ack, command, orchestrator.run_ukestatus)
