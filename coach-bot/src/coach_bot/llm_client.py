"""LLM abstraction – OpenAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI

from coach_bot.config import Settings
from coach_bot.intent import Intent

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_INTENT_HINTS = {
    Intent.STATUS: (
        "Gi William en ærlig følelse av hvor han står, forankret i COACH_BRIEF: hva som er "
        "bra, hva han bør passe på. Naturlig prosa som en mentor – ingen overskrifter eller maler."
    ),
    Intent.TOMORROW: (
        "Snakk om i dag/i morgen. Foreslå én konkret økt (type, varighet, struktur) han kan si "
        "ja til – du legger den inn i Intervals etterpå. Aldri be ham gjøre det manuelt."
    ),
    Intent.WEEK: (
        "Oppsummer uken som en coach: gjennomført, belastning, hva som gikk bra/dårlig, og hva "
        "neste uke bør handle om. Bruk tallene i COACH_BRIEF, naturlig prosa."
    ),
    Intent.PAIN: "Ta smerten på alvor uten å diagnostisere. Vurder belastningen fra dataene, foreslå justering, anbefal fagperson ved behov.",
    Intent.RACE: "Snakk race-strategi for Lofoten Half Extreme (ikke Norseman-volum). Konkret og jordnær.",
    Intent.LOG: "Bekreft kort og menneskelig at du har notert det.",
    Intent.GENERAL: "Vanlig samtale. Svar konkret, referer til det dere har snakket om, bruk COACH_BRIEF for tall.",
    Intent.ANALYSIS: "Gå litt dypere på ADVANCED-tallene i COACH_BRIEF og hva de betyr – forklar som en mentor, ikke som en rapport.",
    Intent.SYNC_WEEK: "Hjelp med kalender-sync; aldri påstå at økter er lagt inn før det er bekreftet.",
    Intent.CHART: (
        "Grafene (CTL/ATL, disiplinvolum) legges ved denne meldingen automatisk. "
        "Kommenter kort hva de forteller; aldri si at du ikke kan lage grafer."
    ),
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
        history_messages: list[dict[str, str]] | None = None,
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
        history_messages: list[dict[str, str]] | None = None,
    ) -> str:
        hint = _INTENT_HINTS.get(intent, _INTENT_HINTS[Intent.GENERAL])
        temp = 0.55 if intent == Intent.GENERAL else 0.35

        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system + "\n\n" + hint},
        ]
        if history_messages:
            for m in history_messages:
                role = m.get("role", "user")
                if role not in ("user", "assistant"):
                    continue
                messages.append({"role": role, "content": m["content"][:4000]})
        else:
            user_content = context
            if history:
                user_content += f"\n\n## Siste samtale\n{history}\n"
            user_content += f"\n\n---\n\nBrukermelding:\n{user_message}"
            messages.append({"role": "user", "content": user_content})
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temp,
            )
            content = response.choices[0].message.content
            return content or "(tomt svar fra modell)"

        messages.append(
            {
                "role": "user",
                "content": f"{context}\n\n---\n\nBrukermelding:\n{user_message}",
            }
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temp,
        )
        content = response.choices[0].message.content
        return content or "(tomt svar fra modell)"
