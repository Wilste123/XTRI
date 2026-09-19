"""Coach orchestration – chat, proactive, and legacy slash flows."""

from __future__ import annotations

from typing import Any

from coach_bot.context_builder import ContextBuilder
from coach_bot.intervals_client import IntervalsClient
from coach_bot.llm_client import LlmClient
from coach_bot.supabase_store import NullSupabaseStore, SupabaseStore


class CoachOrchestrator:
    def __init__(
        self,
        context: ContextBuilder,
        llm: LlmClient,
        intervals: IntervalsClient,
        db: SupabaseStore | NullSupabaseStore | None = None,
    ) -> None:
        self._context = context
        self._llm = llm
        self._intervals = intervals
        self._db = db or NullSupabaseStore()

    def run_status(self) -> str:
        ctx = self._context.for_status()
        return self._llm.complete(ctx, "status")

    def run_imorgen(self) -> str:
        ctx = self._context.for_imorgen()
        return self._llm.complete(ctx, "imorgen")

    def run_ukestatus(self) -> str:
        ctx = self._context.for_ukestatus()
        return self._llm.complete(ctx, "ukestatus")

    def run_chat(self, user_message: str, slack_user_id: str | None = None) -> str:
        ctx = self._context.for_chat(user_message)
        if slack_user_id and self._db.enabled:
            extra = self._db.format_chat_context(slack_user_id)
            if extra:
                ctx = ctx + "\n\n" + extra
        return self._llm.complete(ctx, "chat")

    def run_morning_brief(self) -> str:
        ctx = self._context.for_morning_brief()
        return self._llm.complete(ctx, "morning_brief")

    def run_weekly_brief(self) -> str:
        ctx = self._context.for_ukestatus()
        text = self._llm.complete(ctx, "ukestatus")
        if self._db.enabled:
            self._db.insert_status(
                text,
                source="coach_weekly",
                created_by="system",
                summary="Ukentlig coach-oppsummering",
            )
        return text

    def run_post_workout(self, activity_id: str, activity: dict[str, Any] | None = None) -> str:
        if activity is None:
            try:
                activity = self._intervals.get_activity(activity_id)
            except Exception:
                activity = {"id": activity_id, "note": "Kunne ikke hente full aktivitet fra API"}
        ctx = self._context.for_post_workout(activity)
        return self._llm.complete(ctx, "post_workout")

    @property
    def db(self) -> SupabaseStore | NullSupabaseStore:
        return self._db
