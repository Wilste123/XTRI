"""Coach orchestration per slash command."""

from __future__ import annotations

from coach_bot.context_builder import ContextBuilder
from coach_bot.llm_client import LlmClient


class CoachOrchestrator:
    def __init__(self, context: ContextBuilder, llm: LlmClient) -> None:
        self._context = context
        self._llm = llm

    def run_status(self) -> str:
        ctx = self._context.for_status()
        return self._llm.complete(ctx, "status")

    def run_imorgen(self) -> str:
        ctx = self._context.for_imorgen()
        return self._llm.complete(ctx, "imorgen")

    def run_ukestatus(self) -> str:
        ctx = self._context.for_ukestatus()
        return self._llm.complete(ctx, "ukestatus")
