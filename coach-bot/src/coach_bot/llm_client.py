"""LLM abstraction – OpenAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI

from coach_bot.config import Settings
from coach_bot.intent import Intent

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_INTENT_HINTS = {
    Intent.STATUS: "Gi LOFOTEN 2027 STATUS basert på COACH_BRIEF – ikke motsi tall der.",
    Intent.TOMORROW: "Fokus på i dag/i morgen fra events; si tydelig hvis plan mangler.",
    Intent.WEEK: "UKESTATUS: gjennomført, belastning, bra/dårlig, risiko, endringer, neste uke.",
    Intent.PAIN: "Ikke diagnostiser; vurder belastning fra data og anbefal lege ved behov.",
    Intent.RACE: "Race-strategi Lofoten Half Extreme; ikke Norseman-volum.",
    Intent.LOG: "Bekreft notat.",
    Intent.GENERAL: "Svar konkret; bruk COACH_BRIEF for tall.",
}


def load_system_prompt() -> str:
    path = _PROMPTS_DIR / "system.md"
    return path.read_text(encoding="utf-8")


class LlmClient(ABC):
    @abstractmethod
    def complete_chat(
        self,
        context: str,
        user_message: str,
        intent: Intent = Intent.GENERAL,
        history: str = "",
    ) -> str:
        ...


class OpenAILlmClient(LlmClient):
    def __init__(self, settings: Settings) -> None:
        self._model = settings.coach_model
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._system = load_system_prompt()

    def complete_chat(
        self,
        context: str,
        user_message: str,
        intent: Intent = Intent.GENERAL,
        history: str = "",
    ) -> str:
        hint = _INTENT_HINTS.get(intent, _INTENT_HINTS[Intent.GENERAL])
        user_content = context
        if history:
            user_content += f"\n\n## Siste samtale\n{history}\n"
        user_content += f"\n\n---\n\nBrukermelding:\n{user_message}"

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": self._system + "\n\n" + hint,
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content or "(tomt svar fra modell)"
