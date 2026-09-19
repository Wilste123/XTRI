"""LLM tools (function calling) for the coach.

Instead of writing a plan as prose and re-parsing it, the model calls these
tools and hands us structured data directly. Read tools run immediately and
feed results back to the model; write tools are *staged* and require the user
to confirm ("ja") before anything is created in Intervals – keeping the
human-in-the-loop safety from the project decisions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from coach_bot import knowledge

logger = logging.getLogger(__name__)

_SPORT_TO_TYPE = {
    "run": "Run",
    "løp": "Run",
    "lop": "Run",
    "jogg": "Run",
    "bike": "Ride",
    "ride": "Ride",
    "sykkel": "Ride",
    "sykle": "Ride",
    "swim": "Swim",
    "svøm": "Swim",
    "svom": "Swim",
    "strength": "Workout",
    "styrke": "Workout",
    "walk": "Walk",
    "gåtur": "Walk",
}


@dataclass
class ToolContext:
    """Services + per-turn side-effect collectors for tool execution."""

    intervals: Any = None
    repo: Any = None
    context: Any = None
    repo_writer: Any = None
    sessions: Any = None
    user_id: str = ""
    tz: str = "Europe/Oslo"
    want_charts: bool = False
    staged_events: list[dict[str, Any]] = field(default_factory=list)

    def today(self) -> date:
        if self.intervals is not None:
            return self.intervals.today()
        return date.today()


def tool_schemas() -> list[dict[str, Any]]:
    """OpenAI tool/function schemas the model may call."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": (
                    "Slå opp faglig kunnskap (trening, skade, ernæring, "
                    "Lofoten-race) for å forankre råd. Bruk ved spørsmål om "
                    "hvordan/hvorfor, skade, smerte, kosthold, fueling, pacing."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Hva du vil vite."}
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_training_summary",
                "description": (
                    "Hent Williams treningsstatus: COACH_BRIEF med volum, plan "
                    "vs faktisk, belastning (CTL/ATL/ACWR), fase og dager til race."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_week_plan",
                "description": "Hent den aktive ukeplanen fra prosjektrepoet.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "render_charts",
                "description": (
                    "Legg ved grafer (form CTL/ATL og disiplinvolum) i svaret. "
                    "Bruk når William ber om visuell fremstilling/graf/figur."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "log_note",
                "description": "Noter en subjektiv observasjon i CURRENT_STATUS (f.eks. smerte, søvn, form).",
                "parameters": {
                    "type": "object",
                    "properties": {"note": {"type": "string"}},
                    "required": ["note"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_workouts",
                "description": (
                    "Foreslå å legge én eller flere økter i Intervals-kalenderen. "
                    "Øktene stages og opprettes FØRST når William bekrefter med «ja». "
                    "Oppgi konkrete datoer (YYYY-MM-DD)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workouts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {
                                        "type": "string",
                                        "description": "ISO-dato YYYY-MM-DD",
                                    },
                                    "sport": {
                                        "type": "string",
                                        "enum": [
                                            "run",
                                            "bike",
                                            "swim",
                                            "strength",
                                            "walk",
                                        ],
                                    },
                                    "duration_min": {"type": "integer"},
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["date", "sport", "duration_min"],
                            },
                        }
                    },
                    "required": ["workouts"],
                },
            },
        },
    ]


def _event_from_tool_workout(w: dict[str, Any]) -> dict[str, Any] | None:
    raw_date = str(w.get("date") or "").strip()[:10]
    try:
        d = date.fromisoformat(raw_date)
    except ValueError:
        return None
    sport = _SPORT_TO_TYPE.get(str(w.get("sport") or "").lower(), "Workout")
    try:
        mins = int(w.get("duration_min") or 45)
    except (TypeError, ValueError):
        mins = 45
    mins = max(5, min(mins, 600))
    name = (w.get("name") or "").strip() or f"{sport} {mins} min"
    desc = (w.get("description") or name).strip()[:500]
    return {
        "category": "WORKOUT",
        "type": sport,
        "start_date_local": f"{d.isoformat()}T00:00:00",
        "name": name[:80],
        "description": desc,
        "planned_duration": mins * 60,
        "external_id": f"lofoten-coach-tool-{d.isoformat()}-{sport.lower()}",
    }


def _tool_create_workouts(args: dict[str, Any], ctx: ToolContext) -> str:
    workouts = args.get("workouts") or []
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for w in workouts:
        ev = _event_from_tool_workout(w)
        if ev and ev["start_date_local"] not in seen:
            events.append(ev)
            seen.add(ev["start_date_local"])
    if not events:
        return "Ingen gyldige økter (mangler dato/idrett)."
    ctx.staged_events = events
    if ctx.sessions and ctx.user_id:
        action = "intervals_week" if len(events) > 1 else "intervals_single"
        if action == "intervals_single":
            ctx.sessions.set_pending(ctx.user_id, "intervals_single", {"event": events[0]})
        else:
            ctx.sessions.set_pending(ctx.user_id, "intervals_week", {"events": events})
    lines = "\n".join(
        f"- {e['start_date_local'][:10]}: {e['name']}" for e in events
    )
    return (
        f"{len(events)} økt(er) klargjort for Intervals (IKKE opprettet ennå – "
        f"venter på at William bekrefter med «ja»):\n{lines}"
    )


def _tool_search_knowledge(args: dict[str, Any], ctx: ToolContext) -> str:
    return knowledge.search_text(args.get("query") or "", top_k=3)


def _tool_get_training_summary(args: dict[str, Any], ctx: ToolContext) -> str:
    if ctx.context is None:
        return "(ingen treningsdata tilgjengelig)"
    from coach_bot.intent import Intent

    return ctx.context.for_chat("status", intent=Intent.STATUS)


def _tool_get_week_plan(args: dict[str, Any], ctx: ToolContext) -> str:
    if ctx.repo is None:
        return "(ingen ukeplan tilgjengelig)"
    return ctx.repo.week_plan_excerpt()


def _tool_render_charts(args: dict[str, Any], ctx: ToolContext) -> str:
    ctx.want_charts = True
    return "Grafer legges ved svaret (CTL/ATL og disiplinvolum)."


def _tool_log_note(args: dict[str, Any], ctx: ToolContext) -> str:
    note = (args.get("note") or "").strip()
    if not note:
        return "Tomt notat."
    if ctx.repo_writer is None:
        return "Kan ikke skrive notat nå."
    try:
        ctx.repo_writer.append_status_note(note)
        return f"Notert i CURRENT_STATUS: {note}"
    except Exception as e:  # pragma: no cover - defensive
        return f"Klarte ikke å notere: {e}"


_HANDLERS: dict[str, Callable[[dict[str, Any], ToolContext], str]] = {
    "search_knowledge": _tool_search_knowledge,
    "get_training_summary": _tool_get_training_summary,
    "get_week_plan": _tool_get_week_plan,
    "render_charts": _tool_render_charts,
    "log_note": _tool_log_note,
    "create_workouts": _tool_create_workouts,
}


def execute_tool(name: str, arguments: str | dict[str, Any], ctx: ToolContext) -> str:
    """Run a tool by name with JSON (or dict) arguments; never raises."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            args = {}
    else:
        args = arguments or {}
    handler = _HANDLERS.get(name)
    if not handler:
        return f"Ukjent verktøy: {name}"
    try:
        return handler(args, ctx)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Tool %s failed", name)
        return f"Verktøyet {name} feilet: {e}"
