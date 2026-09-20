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
from datetime import date, timedelta
from typing import Any, Callable

from coach_bot import atlas, knowledge, web_search

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
    github: Any = None
    sessions: Any = None
    user_id: str = ""
    tz: str = "Europe/Oslo"
    want_charts: bool = False
    staged_events: list[dict[str, Any]] = field(default_factory=list)
    staged_ops: list[dict[str, Any]] = field(default_factory=list)
    ops_preview: str = ""

    def today(self) -> date:
        if self.intervals is not None:
            return self.intervals.today()
        return date.today()


def tool_schemas(web_search_enabled: bool | None = None) -> list[dict[str, Any]]:
    """OpenAI tool/function schemas the model may call.

    ``web_search`` is only advertised when a provider key is configured, so the
    model doesn't waste a turn on an unavailable tool.
    """
    if web_search_enabled is None:
        web_search_enabled = web_search.is_enabled()
    schemas: list[dict[str, Any]] = [
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
                "name": "remember_fact",
                "description": (
                    "Lagre VARIG personlig fakta om William i Atlas (utstyr, preferanser, "
                    "helse, mål, hendelser). Bruk når han sier noe du skal huske senere "
                    "(f.eks. ny sykkel, skade, jobbreise, allergi). Ikke for dagens økt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "utstyr|preferanser|helse|mål|hendelse|notat",
                        },
                        "fact": {"type": "string", "description": "Kort presis setning."},
                    },
                    "required": ["category", "fact"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_personal_memory",
                "description": (
                    "Søk i Atlas etter det coach allerede vet om William (utstyr, vaner, "
                    "historikk). Bruk før du antar noe om ham."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Hva du vil huske/sjekke."}
                    },
                    "required": ["query"],
                },
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
        {
            "type": "function",
            "function": {
                "name": "adjust_load",
                "description": (
                    "Juster planlagt belastning i en periode med en prosent "
                    "(negativ = lettere, positiv = tyngre). F.eks. «gjør uka 20% "
                    "lettere» -> percent=-20. Endringer stages og krever «ja»."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "percent": {
                            "type": "number",
                            "description": "Endring i prosent, f.eks. -20 eller 15.",
                        },
                        "start_date": {"type": "string", "description": "ISO fra-dato (valgfri)"},
                        "end_date": {"type": "string", "description": "ISO til-dato (valgfri)"},
                    },
                    "required": ["percent"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "move_workout",
                "description": "Flytt planlagt(e) økt(er) fra én dato til en annen. Stages, krever «ja».",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_date": {"type": "string", "description": "ISO YYYY-MM-DD"},
                        "to_date": {"type": "string", "description": "ISO YYYY-MM-DD"},
                    },
                    "required": ["from_date", "to_date"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_workout",
                "description": "Fjern planlagt(e) økt(er) på en dato. Stages, krever «ja».",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "ISO YYYY-MM-DD"}
                    },
                    "required": ["date"],
                },
            },
        },
    ]
    if web_search_enabled:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": (
                        "Søk på nettet etter ferske eller uforutsette fakta som "
                        "ikke er i fagkunnskapsbasen (nytt utstyr, race-oppdateringer, "
                        "ny forskning). Bruk fagkunnskap først; web for det ukjente/nye."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            }
        )
    return schemas


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


def _parse_iso(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _planned_events_in_range(ctx: ToolContext, start: date, end: date) -> list[dict[str, Any]]:
    if ctx.intervals is None:
        return []
    try:
        evs = ctx.intervals.get_events(start, end)
    except Exception:  # pragma: no cover - defensive
        return []
    out = []
    for e in evs or []:
        d = _parse_iso((e.get("start_date_local") or e.get("start_date") or "")[:10])
        if d is not None and start <= d <= end:
            out.append(e)
    return out


def _event_duration_seconds(e: dict[str, Any]) -> int:
    for k in ("planned_duration", "moving_time", "duration"):
        v = e.get(k)
        if v:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 0


def _stage_ops(ctx: ToolContext, ops: list[dict[str, Any]], preview: str) -> None:
    ctx.staged_ops = ops
    ctx.ops_preview = preview
    if ctx.sessions and ctx.user_id:
        ctx.sessions.set_pending(ctx.user_id, "intervals_ops", {"ops": ops})


def _tool_adjust_load(args: dict[str, Any], ctx: ToolContext) -> str:
    try:
        percent = float(args.get("percent"))
    except (TypeError, ValueError):
        return "Trenger en prosent (f.eks. -20)."
    today = ctx.today()
    start = _parse_iso(args.get("start_date")) or today
    end = _parse_iso(args.get("end_date")) or (start + timedelta(days=6))
    evs = _planned_events_in_range(ctx, start, end)
    if not evs:
        return f"Fant ingen planlagte økter i {start}–{end} å justere."
    factor = 1 + percent / 100.0
    ops: list[dict[str, Any]] = []
    lines: list[str] = []
    for e in evs:
        dur = _event_duration_seconds(e)
        if dur <= 0:
            continue
        new = max(300, int(round(dur * factor / 60.0)) * 60)
        patched = dict(e)
        patched["planned_duration"] = new
        ops.append({"op": "upsert", "event": patched})
        lines.append(
            f"- {(e.get('start_date_local') or '')[:10]}: {e.get('name')}: "
            f"{dur // 60}→{new // 60} min"
        )
    if not ops:
        return "Fant ingen økter med varighet å justere."
    preview = "\n".join(lines)
    _stage_ops(ctx, ops, preview)
    retning = "lettere" if percent < 0 else "tyngre"
    return (
        f"Klargjort {len(ops)} økter {abs(percent):.0f}% {retning} "
        f"(IKKE lagret ennå – venter på «ja»):\n{preview}"
    )


def _tool_move_workout(args: dict[str, Any], ctx: ToolContext) -> str:
    frm = _parse_iso(args.get("from_date"))
    to = _parse_iso(args.get("to_date"))
    if not frm or not to:
        return "Trenger gyldig fra- og til-dato (YYYY-MM-DD)."
    evs = _planned_events_in_range(ctx, frm, frm)
    if not evs:
        return f"Fant ingen planlagt økt {frm} å flytte."
    ops: list[dict[str, Any]] = []
    lines: list[str] = []
    for e in evs:
        patched = dict(e)
        patched["start_date_local"] = f"{to.isoformat()}T00:00:00"
        ops.append({"op": "upsert", "event": patched})
        lines.append(f"- {e.get('name')}: {frm} → {to}")
    preview = "\n".join(lines)
    _stage_ops(ctx, ops, preview)
    return f"Klargjort flytting (venter på «ja»):\n{preview}"


def _tool_delete_workout(args: dict[str, Any], ctx: ToolContext) -> str:
    d = _parse_iso(args.get("date"))
    if not d:
        return "Trenger gyldig dato (YYYY-MM-DD)."
    evs = _planned_events_in_range(ctx, d, d)
    if not evs:
        return f"Fant ingen planlagt økt {d} å slette."
    ops: list[dict[str, Any]] = []
    lines: list[str] = []
    for e in evs:
        eid = e.get("id")
        if eid is None:
            continue
        ops.append({"op": "delete", "id": eid, "label": f"{d}: {e.get('name')}"})
        lines.append(f"- slett {d}: {e.get('name')}")
    if not ops:
        return "Fant ingen økt med id å slette."
    preview = "\n".join(lines)
    _stage_ops(ctx, ops, preview)
    return f"Klargjort sletting (venter på «ja»):\n{preview}"


def _tool_web_search(args: dict[str, Any], ctx: ToolContext) -> str:
    return web_search.search_web(args.get("query") or "")


def _tool_remember_fact(args: dict[str, Any], ctx: ToolContext) -> str:
    if ctx.repo is None:
        return "Kan ikke lagre – repo mangler."
    return atlas.persist_fact(
        ctx.repo._root,
        args.get("category") or "notat",
        args.get("fact") or "",
        github=ctx.github,
    )


def _tool_search_personal_memory(args: dict[str, Any], ctx: ToolContext) -> str:
    if ctx.repo is None:
        return "(repo mangler)"
    return atlas.search_text(args.get("query") or "", ctx.repo._root, top_k=5)


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
    "remember_fact": _tool_remember_fact,
    "search_personal_memory": _tool_search_personal_memory,
    "get_training_summary": _tool_get_training_summary,
    "get_week_plan": _tool_get_week_plan,
    "render_charts": _tool_render_charts,
    "log_note": _tool_log_note,
    "create_workouts": _tool_create_workouts,
    "adjust_load": _tool_adjust_load,
    "move_workout": _tool_move_workout,
    "delete_workout": _tool_delete_workout,
    "web_search": _tool_web_search,
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
