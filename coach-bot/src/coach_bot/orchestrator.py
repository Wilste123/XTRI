"""Coach orchestration for Slack DM."""

from __future__ import annotations

from coach_bot.context_builder import ContextBuilder
from coach_bot.llm_client import LlmClient


class CoachOrchestrator:
    def __init__(self, context: ContextBuilder, llm: LlmClient) -> None:
        self._context = context
        self._llm = llm

    def run_chat(self, user_message: str) -> str:
        ctx = self._context.for_chat()
        return self._llm.complete_chat(ctx, user_message)

    def run_morning_briefing(self) -> str:
        ctx = self._context.for_chat()
        prompt = (
            "Gi en kort morgenmelding for I DAG og I MORGEN: plan fra events, "
            "belastning siste dager, anbefalt intensitet (RPE), og ett konkret fokus."
        )
        return self._llm.complete_chat(ctx, prompt)
