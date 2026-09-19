"""Outbound Slack DMs for proactive coach messages."""

from __future__ import annotations

import logging

from slack_sdk import WebClient

from coach_bot.config import Settings
from coach_bot.state_store import StateStore

logger = logging.getLogger(__name__)

MAX_CHUNK = 12000


def _chunks(text: str) -> list[str]:
    parts: list[str] = []
    while text:
        parts.append(text[:MAX_CHUNK])
        text = text[MAX_CHUNK:]
    return parts or [""]


class SlackNotifier:
    def __init__(self, client: WebClient, settings: Settings, state: StateStore) -> None:
        self._client = client
        self._settings = settings
        self._state = state

    def _open_dm(self, user_id: str) -> str:
        cached = self._state.get_dm_channel(user_id)
        if cached:
            return cached
        resp = self._client.conversations_open(users=user_id)
        channel_id = resp["channel"]["id"]
        self._state.set_dm_channel(user_id, channel_id)
        return channel_id

    def send_dm(self, user_id: str, text: str) -> None:
        channel = self._open_dm(user_id)
        for i, chunk in enumerate(_chunks(text)):
            body = chunk if i == 0 else f"(fortsettelse {i + 1})\n{chunk}"
            self._client.chat_postMessage(channel=channel, text=body)

    def broadcast(self, text: str) -> None:
        for user_id in self._settings.notify_user_id_set:
            try:
                self.send_dm(user_id, text)
            except Exception:
                logger.exception("Failed to notify user %s", user_id)
