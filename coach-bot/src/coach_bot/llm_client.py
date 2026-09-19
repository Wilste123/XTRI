"""LLM abstraction – OpenAI in V1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI

from coach_bot.config import Settings

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    path = _PROMPTS_DIR / "system.md"
    return path.read_text(encoding="utf-8")


class LlmClient(ABC):
    @abstractmethod
    def complete(self, user_message: str, command_hint: str) -> str:
        ...


class OpenAILlmClient(LlmClient):
    def __init__(self, settings: Settings) -> None:
        self._model = settings.coach_model
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._system = load_system_prompt()

    def complete(self, user_message: str, command_hint: str) -> str:
        instruction = {
            "status": (
                "Gi svar i strukturen LOFOTEN 2027 STATUS: Tid til konkurranse, "
                "nåværende treningsmengde, svømming/sykkel/løp/styrke status, "
                "aerob kapasitet, skade/risiko, siste test, neste milepæl, "
                "største utfordring, viktigste fokus neste 2–4 uker."
            ),
            "imorgen": (
                "Gi en kort morgen-/planmelding for I MORGEN: hva som er planlagt "
                "(fra events), belastning siste dager, anbefalt intensitet (RPE), "
                "og ev. forslag til bytte hvis CURRENT_STATUS eller data tilsier det."
            ),
            "ukestatus": (
                "Gi UKESTATUS med seksjonene: Gjennomført (timer og disipliner), "
                "Belastning, Hva gikk bra?, Hva gikk dårlig?, Risiko, "
                "Hva bør endres?, Neste uke (konkret forslag)."
            ),
        }.get(command_hint, "Svar som coach.")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system + "\n\n" + instruction},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content or "(tomt svar fra modell)"
