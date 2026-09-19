"""Post CoachReply to Slack (text, blocks, images)."""

from __future__ import annotations

import logging
from pathlib import Path

from slack_sdk import WebClient

from coach_bot.coach_reply import CoachReply
from coach_bot.slack_delivery import open_dm_channel

logger = logging.getLogger(__name__)


def deliver_coach_reply(
    client: WebClient,
    user_id: str,
    reply: CoachReply,
    *,
    label: str = "Coach",
    thread_ts: str | None = None,
) -> str | None:
    channel = open_dm_channel(client, user_id)
    kwargs: dict = {"channel": channel, "text": reply.text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    if reply.blocks:
        kwargs["blocks"] = reply.blocks
    resp = client.chat_postMessage(**kwargs)
    ts = resp.get("ts")
    for img in reply.image_paths:
        _upload_image(client, channel, img, thread_ts=ts)
        _safe_unlink(img)
    logger.info("%s delivered user_id=%s message_ts=%s images=%s", label, user_id, ts, len(reply.image_paths))
    return ts


def post_coach_reply(
    client: WebClient,
    channel: str,
    reply: CoachReply,
    *,
    thread_ts: str | None = None,
) -> str | None:
    kwargs: dict = {"channel": channel, "text": reply.text, "thread_ts": thread_ts}
    if reply.blocks:
        kwargs["blocks"] = reply.blocks
    resp = client.chat_postMessage(**kwargs)
    ts = resp.get("ts")
    for img in reply.image_paths:
        _upload_image(client, channel, img, thread_ts=ts)
        _safe_unlink(img)
    return ts


def _upload_image(client: WebClient, channel: str, path: Path, thread_ts: str | None = None) -> None:
    try:
        client.files_upload_v2(
            channel=channel,
            file=str(path),
            title=path.name,
            thread_ts=thread_ts,
        )
    except Exception:
        logger.exception("Image upload failed for %s", path)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
