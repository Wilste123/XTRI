"""Send coach messages to Slack DMs (proactive + manual briefing)."""

from __future__ import annotations

import logging
from typing import Any

from slack_sdk import WebClient

from coach_bot.errors import friendly_coach_error

logger = logging.getLogger(__name__)


def open_dm_channel(client: WebClient, user_id: str) -> str:
    resp = client.conversations_open(users=user_id)
    return resp["channel"]["id"]


def post_dm(
    client: WebClient,
    user_id: str,
    text: str,
    *,
    blocks: list[dict[str, Any]] | None = None,
    label: str = "Melding",
) -> str | None:
    """Post to user DM. Returns message ts on success."""
    try:
        channel = open_dm_channel(client, user_id)
        kwargs: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            kwargs["blocks"] = blocks
        resp = client.chat_postMessage(**kwargs)
        ts = resp.get("ts")
        logger.info(
            "%s sent user_id=%s channel=%s message_ts=%s",
            label,
            user_id,
            channel,
            ts,
        )
        return ts
    except Exception as e:
        logger.exception("%s failed for user_id=%s", label, user_id)
        try:
            channel = open_dm_channel(client, user_id)
            client.chat_postMessage(
                channel=channel,
                text=f"{label} feilet: {friendly_coach_error(e)}",
            )
        except Exception:
            pass
        return None


def post_dm_to_users(
    client: WebClient,
    user_ids: list[str],
    text: str,
    *,
    blocks: list[dict[str, Any]] | None = None,
    label: str = "Melding",
) -> None:
    for uid in user_ids:
        post_dm(client, uid, text, blocks=blocks, label=label)
