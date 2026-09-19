"""Slack slash command handlers."""

from __future__ import annotations

import logging
import threading
from typing import Callable

import httpx
from slack_bolt import App

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
            "response_type": "in_channel" if i == 0 else "in_channel",
            "text": chunk if i == 0 else f"(fortsettelse {i + 1})\n{chunk}",
            "replace_original": i == 0,
        }
        try:
            r = httpx.post(response_url, json=payload, timeout=30.0)
            r.raise_for_status()
        except Exception as e:
            logger.exception("Failed to post to response_url: %s", e)


def _run_async(response_url: str, fn: Callable[[], str]) -> None:
    try:
        result = fn()
        _post_response(response_url, result)
    except Exception as e:
        logger.exception("Coach command failed")
        _post_response(
            response_url,
            f"Coach feilet: {e!s}. Sjekk logger og .env (Intervals/OpenAI).",
        )


def register_handlers(app: App, orchestrator: CoachOrchestrator, settings: Settings) -> None:
    allowed = settings.allowed_user_id_set

    def check_user(user_id: str) -> str | None:
        if allowed and user_id not in allowed:
            return "Du har ikke tilgang til denne coach-boten."
        return None

    def deferred(ack, command, runner: Callable[[], str]) -> None:
        user_id = command.get("user_id", "")
        denied = check_user(user_id)
        if denied:
            ack(denied)
            return
        ack("Henter data fra Intervals og repo – et øyeblikk…")
        url = command["response_url"]
        threading.Thread(
            target=_run_async,
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
