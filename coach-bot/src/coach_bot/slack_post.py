"""Post CoachReply to Slack (text, blocks, images)."""

from __future__ import annotations

import logging
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from coach_bot.coach_reply import CoachReply
from coach_bot.slack_delivery import open_dm_channel

logger = logging.getLogger(__name__)

_UPLOAD_SCOPE_HINT = (
    "Graf kunne ikke lastes opp. Legg til bot-scope *files:write* i Slack-appen, "
    "reinstaller appen i workspace, og oppdater SLACK_BOT_TOKEN."
)


def post_coach_reply(
    client: WebClient,
    channel: str,
    reply: CoachReply,
    *,
    thread_ts: str | None = None,
) -> str | None:
    kwargs: dict = {"channel": channel, "text": reply.text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    if reply.blocks:
        kwargs["blocks"] = reply.blocks
    resp = client.chat_postMessage(**kwargs)
    ts = resp.get("ts")
    upload_note = _upload_images(client, channel, reply.image_paths, thread_ts=ts)
    if upload_note:
        reply.text = f"{reply.text}\n\n{upload_note}".strip()
        try:
            client.chat_postMessage(
                channel=channel,
                text=upload_note,
                thread_ts=ts or thread_ts,
            )
        except Exception:
            logger.exception("Failed to post chart upload notice")
    return ts


def deliver_coach_reply(
    client: WebClient,
    user_id: str,
    reply: CoachReply,
    *,
    label: str = "Coach",
    thread_ts: str | None = None,
) -> str | None:
    channel = open_dm_channel(client, user_id)
    ts = post_coach_reply(client, channel, reply, thread_ts=thread_ts)
    logger.info(
        "%s delivered user_id=%s message_ts=%s images=%s",
        label,
        user_id,
        ts,
        len(reply.image_paths),
    )
    return ts


def _upload_images(
    client: WebClient,
    channel: str,
    paths: list[Path],
    thread_ts: str | None = None,
) -> str | None:
    if not paths:
        return None
    failed = 0
    scope_error = False
    for path in paths:
        try:
            client.files_upload_v2(
                channel=channel,
                file=str(path),
                title=path.name,
                thread_ts=thread_ts,
            )
        except SlackApiError as e:
            failed += 1
            err = str(e.response.get("error", "")) if e.response else str(e)
            logger.exception("Image upload failed for %s: %s", path, err)
            if err in ("missing_scope", "not_allowed_token_type", "access_denied"):
                scope_error = True
        except Exception:
            failed += 1
            logger.exception("Image upload failed for %s", path)
        finally:
            _safe_unlink(path)
    if failed == 0:
        return None
    if scope_error:
        return _UPLOAD_SCOPE_HINT
    return f"Kunne ikke laste opp {failed} graf(er). Sjekk Slack-app og logger."


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
