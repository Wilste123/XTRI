"""Coach orchestration for Slack DM."""

from __future__ import annotations

from coach_bot.context_builder import ContextBuilder
from coach_bot.intent import Intent, detect_intent, strip_log_prefix
from coach_bot.llm_client import LlmClient
from coach_bot.repo_writer import RepoWriter
from coach_bot.session_store import SessionStore


class CoachOrchestrator:
    def __init__(
        self,
        context: ContextBuilder,
        llm: LlmClient,
        sessions: SessionStore | None = None,
        repo_writer: RepoWriter | None = None,
    ) -> None:
        self._context = context
        self._llm = llm
        self._sessions = sessions
        self._repo_writer = repo_writer

    def run_chat(self, user_message: str, user_id: str = "") -> str:
        intent = detect_intent(user_message)

        if intent == Intent.LOG and self._repo_writer:
            note = strip_log_prefix(user_message)
            if not note:
                return "Skriv f.eks. `logg: kne 3/10 etter løp`."
            self._repo_writer.append_status_note(note)
            reply = f"Notert i CURRENT_STATUS: {note}"
            if self._sessions and user_id:
                self._sessions.append(user_id, "user", user_message)
                self._sessions.append(user_id, "assistant", reply)
            return reply

        history = ""
        if self._sessions and user_id:
            history = self._sessions.format_history(user_id)

        ctx = self._context.for_chat(user_message, intent=intent)
        reply = self._llm.complete_chat(ctx, user_message, intent=intent, history=history)

        if self._sessions and user_id:
            self._sessions.append(user_id, "user", user_message)
            self._sessions.append(user_id, "assistant", reply)

        return reply

    def run_morning_briefing(self) -> str:
        prompt = (
            "Gi en kort morgenmelding for I DAG og I MORGEN: plan fra events, "
            "belastning siste dager, anbefalt intensitet (RPE), og ett konkret fokus."
        )
        ctx = self._context.for_chat(prompt, intent=Intent.TOMORROW)
        return self._llm.complete_chat(ctx, prompt, intent=Intent.TOMORROW)

    def run_weekly_briefing(self) -> str:
        prompt = "Gi UKESTATUS: gjennomført, belastning, risiko, endringer, neste uke."
        ctx = self._context.for_chat(prompt, intent=Intent.WEEK)
        return self._llm.complete_chat(ctx, prompt, intent=Intent.WEEK)
