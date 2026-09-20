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


_TOOL_GUIDE = (
    "Du har verktøy – bruk dem aktivt i stedet for bare å beskrive:\n"
    "- build_workout / create_workouts: detaljerte Intervals-økter (syntax som "
    "workout builder: «- 25m 65% HR», «Main set 6x», recovery-linjer). "
    "Bruk session_type (threshold_ride, test_run_20, …) eller workout_text. "
    "get_athlete_thresholds for FTP/LTHR. get_week_plan er skeleton/hensikt – "
    "du er treneren som fyller struktur. Staging → «ja» for commit.\n"
    "- adjust_load: juster planlagt belastning i en periode med prosent (f.eks. "
    "«gjør uka 20% lettere» -> percent=-20).\n"
    "- move_workout / delete_workout: flytt eller fjern planlagte økter. "
    "«Slett alle neste uke»: delete_workout med period=next_week (ett kall, "
    "alle dager). Eller start_date+end_date. En dag: date=YYYY-MM-DD. "
    "Valgfri sport/name_contains.\n"
    "- search_knowledge: slå opp fagkunnskap (trening/skade/ernæring/race) FØR du "
    "gir faglige råd – vær presis, på nivå med en topptrener, ikke overfladisk.\n"
    "- web_search (hvis tilgjengelig): for ferske/uforutsette fakta som ikke er i "
    "kunnskapsbasen (nytt utstyr, race-oppdateringer, ny forskning).\n"
    "- render_charts: når han vil se en graf eller visuell fremstilling.\n"
    "- log_note: når han rapporterer smerte/søvn/form som bør noteres.\n"
    "- remember_fact: lagre varig personlig fakta (ny sykkel, preferanse, skadehistorikk).\n"
    "- search_personal_memory: sjekk Atlas før du antar noe om William.\n"
    "Alle kalender-endringer krever «ja» før de utføres. Aldri si at du «ikke "
    "kan» noe av dette – bruk verktøyet."
)


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

    def complete_agentic(
        self,
        context: str,
        user_message: str,
        *,
        history_messages: list[dict[str, str]] | None = None,
        tools: list[dict] | None = None,
        tool_executor=None,
        intent: Intent = Intent.GENERAL,
        max_iters: int = 5,
    ) -> str:
        """Default: no tool support – behave like plain chat."""
        return self.complete_chat(
            context, user_message, intent=intent, history_messages=history_messages
        )


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

    def complete_agentic(
        self,
        context: str,
        user_message: str,
        *,
        history_messages: list[dict[str, str]] | None = None,
        tools: list[dict] | None = None,
        tool_executor=None,
        intent: Intent = Intent.GENERAL,
        max_iters: int = 5,
    ) -> str:
        hint = _INTENT_HINTS.get(intent, _INTENT_HINTS[Intent.GENERAL])
        system = f"{self._system}\n\n{hint}\n\n{_TOOL_GUIDE}"
        messages: list[dict] = [{"role": "system", "content": system}]
        if history_messages:
            for m in history_messages:
                role = m.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": m["content"][:4000]})
        messages.append(
            {
                "role": "user",
                "content": f"{context}\n\n---\n\nBrukermelding:\n{user_message}",
            }
        )

        if not tools or tool_executor is None:
            resp = self._client.chat.completions.create(
                model=self._model, messages=messages, temperature=0.5
            )
            return resp.choices[0].message.content or "(tomt svar fra modell)"

        for _ in range(max_iters):
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.5,
            )
            msg = resp.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:
                return msg.content or "(tomt svar fra modell)"
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                result = tool_executor(tc.function.name, tc.function.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)[:6000],
                    }
                )

        resp = self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=0.5
        )
        return resp.choices[0].message.content or "(tomt svar fra modell)"
