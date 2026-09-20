"""Extract durable facts from a DM turn and append to Atlas."""

from __future__ import annotations

import json
import logging
import re
from datetime import date

from openai import OpenAI

from coach_bot import atlas
from coach_bot.config import Settings
from coach_bot.github_repo import GitHubRepoSync

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """Du er en assistent som trekker ut VARIGE fakta om William (utøver) fra én Slack-utveksling.
Returner JSON: {"facts": [{"category": "utstyr|preferanser|helse|mål|hendelse|notat", "text": "kort setning"}]}
Regler:
- Kun fakta William uttrykkelig deler eller som er tydelig varige (ny sykkel, skade, preferanse, jobb/reise, utstyr, allergi, osv.).
- IKKE treningsplan for én dag, IKKE generelle coach-råd, IKKE tall fra Intervals med mindre han sier det som personlig fakta.
- Maks 3 facts. Tom liste hvis ingenting varig.
- Skriv facts på norsk, korte og presise."""


def extract_facts(client: OpenAI, model: str, user_message: str, assistant_message: str) -> list[dict[str, str]]:
    user_message = (user_message or "").strip()
    assistant_message = (assistant_message or "").strip()
    if len(user_message) < 8:
        return []
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _EXTRACT_PROMPT},
                {
                    "role": "user",
                    "content": f"William:\n{user_message[:3000]}\n\nCoach:\n{assistant_message[:3000]}",
                },
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        facts = data.get("facts") or []
        out: list[dict[str, str]] = []
        for item in facts[:3]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text or len(text) < 4:
                continue
            cat = str(item.get("category") or "notat")
            out.append({"category": cat, "text": text})
        return out
    except Exception:
        logger.exception("memory extract failed")
        return []


class MemoryLearner:
    def __init__(self, settings: Settings, github: GitHubRepoSync | None = None) -> None:
        self._enabled = settings.memory_auto_learn
        self._lofoten = settings.lofoten_dir
        self._github = github
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.coach_model

    def learn_from_turn(self, user_message: str, assistant_message: str) -> list[str]:
        if not self._enabled:
            return []
        if re.match(r"^\s*logg\s*:", user_message, re.I):
            return []
        facts = extract_facts(self._client, self._model, user_message, assistant_message)
        messages: list[str] = []
        for item in facts:
            msg = atlas.persist_fact(
                self._lofoten,
                item["category"],
                item["text"],
                github=self._github,
                on_date=date.today(),
            )
            if msg.startswith("Lagret"):
                messages.append(msg)
        return messages
