"""Supabase persistence for coach state, chat, and activity dedup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from coach_bot.config import Settings

logger = logging.getLogger(__name__)


class SupabaseStore:
    def __init__(self, settings: Settings) -> None:
        url = settings.supabase_url.strip()
        key = settings.supabase_service_role_key.strip()
        self._client: Client = create_client(url, key)

    @property
    def enabled(self) -> bool:
        return True

    def latest_status_md(self) -> str | None:
        try:
            resp = (
                self._client.table("coach_status_snapshots")
                .select("content_md")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if rows:
                return str(rows[0]["content_md"])
        except Exception:
            logger.exception("Supabase latest_status_md failed")
        return None

    def insert_status(
        self,
        content_md: str,
        *,
        source: str = "manual",
        created_by: str = "system",
        summary: str | None = None,
        phase: str | None = None,
        focus: str | None = None,
    ) -> None:
        row = {
            "content_md": content_md,
            "source": source,
            "created_by": created_by,
            "summary": summary,
            "phase": phase,
            "focus": focus,
        }
        self._client.table("coach_status_snapshots").insert(row).execute()

    def append_message(
        self,
        slack_user_id: str,
        role: str,
        content: str,
        *,
        message_kind: str | None = None,
        slack_channel_id: str | None = None,
        thread_ts: str | None = None,
    ) -> None:
        self._client.table("coach_messages").insert(
            {
                "slack_user_id": slack_user_id,
                "slack_channel_id": slack_channel_id,
                "thread_ts": thread_ts,
                "role": role,
                "content": content,
                "message_kind": message_kind,
            }
        ).execute()

    def recent_messages(self, slack_user_id: str, limit: int = 12) -> list[dict[str, Any]]:
        try:
            resp = (
                self._client.table("coach_messages")
                .select("role, content, created_at, message_kind")
                .eq("slack_user_id", slack_user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = list(resp.data or [])
            rows.reverse()
            return rows
        except Exception:
            logger.exception("Supabase recent_messages failed")
            return []

    def format_chat_context(self, slack_user_id: str, limit: int = 10) -> str:
        rows = self.recent_messages(slack_user_id, limit=limit)
        if not rows:
            return ""
        lines = ["## Siste Slack-samtale (database)"]
        for row in rows:
            role = row.get("role", "?")
            content = str(row.get("content", ""))[:800]
            lines.append(f"- **{role}:** {content}")
        return "\n".join(lines)

    def is_activity_bootstrapped(self) -> bool:
        val = self.get_state("activities_bootstrapped")
        return bool(val and val.get("done"))

    def bootstrap_activities(self, activity_ids: list[str]) -> None:
        if not activity_ids:
            self.set_state("activities_bootstrapped", {"done": True, "count": 0})
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {"intervals_activity_id": aid, "first_seen_at": now, "notified_at": now}
            for aid in activity_ids
        ]
        self._client.table("coach_activity_dedup").upsert(
            rows, on_conflict="intervals_activity_id"
        ).execute()
        self.set_state(
            "activities_bootstrapped",
            {"done": True, "count": len(activity_ids)},
        )

    def new_activity_ids(self, activity_ids: list[str]) -> list[str]:
        if not activity_ids:
            return []
        try:
            resp = (
                self._client.table("coach_activity_dedup")
                .select("intervals_activity_id")
                .in_("intervals_activity_id", activity_ids)
                .execute()
            )
            known = {str(r["intervals_activity_id"]) for r in (resp.data or [])}
        except Exception:
            logger.exception("Supabase activity lookup failed")
            known = set()
        return [aid for aid in activity_ids if aid not in known]

    def register_activity_seen(self, activity_id: str) -> None:
        self._client.table("coach_activity_dedup").upsert(
            {"intervals_activity_id": activity_id},
            on_conflict="intervals_activity_id",
        ).execute()

    def mark_activity_notified(self, activity_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._client.table("coach_activity_dedup").upsert(
            {
                "intervals_activity_id": activity_id,
                "notified_at": now,
            },
            on_conflict="intervals_activity_id",
        ).execute()

    def get_state(self, key: str) -> dict[str, Any] | None:
        try:
            resp = (
                self._client.table("coach_bot_state")
                .select("value")
                .eq("key", key)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if rows:
                val = rows[0].get("value")
                return val if isinstance(val, dict) else {}
        except Exception:
            logger.exception("Supabase get_state failed for %s", key)
        return None

    def set_state(self, key: str, value: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._client.table("coach_bot_state").upsert(
            {"key": key, "value": value, "updated_at": now},
            on_conflict="key",
        ).execute()

    def get_dm_channel(self, user_id: str) -> str | None:
        val = self.get_state(f"dm_channel:{user_id}")
        if val and val.get("channel_id"):
            return str(val["channel_id"])
        return None

    def set_dm_channel(self, user_id: str, channel_id: str) -> None:
        self.set_state(f"dm_channel:{user_id}", {"channel_id": channel_id})

    def seed_status_from_markdown(self, content_md: str, created_by: str = "import") -> bool:
        if self.latest_status_md():
            return False
        self.insert_status(content_md, source="import", created_by=created_by)
        return True


class NullSupabaseStore:
    """Fallback when Supabase env is missing."""

    enabled = False

    def latest_status_md(self) -> str | None:
        return None

    def format_chat_context(self, slack_user_id: str, limit: int = 10) -> str:
        return ""

    def append_message(self, *args, **kwargs) -> None:
        return None

    def insert_status(self, *args, **kwargs) -> None:
        return None

    def is_activity_bootstrapped(self) -> bool:
        return False

    def bootstrap_activities(self, activity_ids: list[str]) -> None:
        return None

    def new_activity_ids(self, activity_ids: list[str]) -> list[str]:
        return activity_ids

    def register_activity_seen(self, activity_id: str) -> None:
        return None

    def mark_activity_notified(self, activity_id: str) -> None:
        return None

    def get_dm_channel(self, user_id: str) -> str | None:
        return None

    def set_dm_channel(self, user_id: str, channel_id: str) -> None:
        return None

    def seed_status_from_markdown(self, content_md: str, created_by: str = "import") -> bool:
        return False


def build_supabase_store(settings: Settings) -> SupabaseStore | NullSupabaseStore:
    if not settings.supabase_enabled:
        return NullSupabaseStore()
    try:
        return SupabaseStore(settings)
    except Exception:
        logger.exception("Failed to init Supabase; using file-only mode")
        return NullSupabaseStore()
