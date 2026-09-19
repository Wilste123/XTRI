"""LLM abstraction – OpenAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI

from coach_bot.config import Settings

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    path = _PROMPTS_DIR / "system.md"
    return path.read_text(encoding="utf-8")

_CHAT_INSTRUCTION = """
Brukeren skriver i Slack DM. Tolk intensjon fra meldingen (status, ukestatus, plan i morgen, fri sparring).

Struktur når det passer:
- **Status / form:** LOFOTEN 2027 STATUS – tid til race, volum, disipliner, risiko, fokus 2–4 uker.
- **Uke:** Gjennomført, belastning, bra/dårlig, risiko, endringer, neste uke.
- **I morgen / i dag:** plan fra events + anbefaling; si tydelig hvis plan mangler.

Svar kort når spørsmålet er enkelt; utdyp når brukeren ber om analyse.
"""


class LlmClient(ABC):
    @abstractmethod
    def complete_chat(self, context: str, user_message: str) -> str:
        ...


class OpenAILlmClient(LlmClient):
    def __init__(self, settings: Settings) -> None:
        self._model = settings.coach_model
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._system = load_system_prompt()

    def complete_chat(self, context: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": self._system + "\n\n" + _CHAT_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": f"{context}\n\n---\n\nBrukermelding:\n{user_message}",
                },
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content or "(tomt svar fra modell)"
