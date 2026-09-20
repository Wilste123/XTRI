import os
import shutil
from datetime import date
from pathlib import Path

from coach_bot import web_search
from coach_bot.config import Settings
from coach_bot.repo_reader import RepoReader
from coach_bot.tools import ToolContext, execute_tool, tool_schemas

REPO_ROOT = Path(__file__).resolve().parents[2]


class _Sessions:
    def __init__(self):
        self.pending = {}

    def set_pending(self, user_id, action_type, payload):
        self.pending[user_id] = (action_type, payload)

    def get_pending(self, user_id):
        return self.pending.get(user_id)


class _Intervals:
    def __init__(self, events):
        self._events = events
        self.deleted = []
        self.upserted = []

    def today(self):
        return date(2026, 9, 20)

    def get_events(self, oldest, newest):
        return self._events

    def bulk_upsert_events(self, events):
        self.upserted.extend(events)
        return events

    def delete_event(self, event_id):
        self.deleted.append(event_id)


def _ctx(events):
    return ToolContext(intervals=_Intervals(events), sessions=_Sessions(), user_id="U1")


def test_adjust_load_scales_and_stages():
    events = [
        {"id": 1, "start_date_local": "2026-09-20T00:00:00", "name": "Løp", "planned_duration": 3600},
        {"id": 2, "start_date_local": "2026-09-21T00:00:00", "name": "Sykkel", "planned_duration": 6000},
    ]
    ctx = _ctx(events)
    out = execute_tool("adjust_load", {"percent": -20}, ctx)
    assert "lettere" in out.lower()
    assert len(ctx.staged_ops) == 2
    # 3600s (60min) -20% -> 48 min = 2880s
    upsert0 = ctx.staged_ops[0]["event"]
    assert upsert0["planned_duration"] == 48 * 60
    assert ctx.sessions.pending["U1"][0] == "intervals_ops"


def test_move_workout_stages_upsert_new_date():
    events = [{"id": 5, "start_date_local": "2026-09-20T00:00:00", "name": "Langtur"}]
    ctx = _ctx(events)
    out = execute_tool("move_workout", {"from_date": "2026-09-20", "to_date": "2026-09-21"}, ctx)
    assert "flytting" in out.lower()
    ev = ctx.staged_ops[0]["event"]
    assert ev["start_date_local"].startswith("2026-09-21")


def test_delete_workout_stages_delete():
    events = [{"id": 9, "start_date_local": "2026-09-20T00:00:00", "name": "Svøm"}]
    ctx = _ctx(events)
    out = execute_tool("delete_workout", {"date": "2026-09-20"}, ctx)
    assert "sletting" in out.lower()
    assert ctx.staged_ops[0] == {"op": "delete", "id": 9, "label": "2026-09-20: Svøm"}


def test_delete_workout_range_next_week():
    events = [
        {"id": 1, "category": "WORKOUT", "start_date_local": "2026-09-21T00:00:00", "name": "A"},
        {"id": 2, "category": "WORKOUT", "start_date_local": "2026-09-23T00:00:00", "name": "B"},
        {"id": 3, "category": "WORKOUT", "start_date_local": "2026-09-24T00:00:00", "name": "C"},
        {"id": 9, "category": "NOTE", "start_date_local": "2026-09-22T00:00:00", "name": "Note"},
    ]
    ctx = _ctx(events)
    out = execute_tool("delete_workout", {"period": "next_week"}, ctx)
    assert "3 økt" in out or "3 økter" in out.lower() or len(ctx.staged_ops) == 3
    assert len(ctx.staged_ops) == 3
    assert {op["id"] for op in ctx.staged_ops} == {1, 2, 3}


def test_delete_workout_start_end_range():
    events = [
        {"id": 1, "category": "WORKOUT", "start_date_local": "2026-09-20T00:00:00", "name": "A"},
        {"id": 2, "category": "WORKOUT", "start_date_local": "2026-09-25T00:00:00", "name": "B"},
    ]
    ctx = _ctx(events)
    execute_tool(
        "delete_workout",
        {"start_date": "2026-09-21", "end_date": "2026-09-24"},
        ctx,
    )
    assert len(ctx.staged_ops) == 0
    execute_tool(
        "delete_workout",
        {"start_date": "2026-09-20", "end_date": "2026-09-26"},
        ctx,
    )
    assert len(ctx.staged_ops) == 2


def test_delete_workout_filters_by_sport():
    events = [
        {"id": 1, "type": "Ride", "start_date_local": "2026-09-21T00:00:00", "name": "Sykkelintervall"},
        {"id": 2, "type": "Run", "start_date_local": "2026-09-21T00:00:00", "name": "Løp 75 min"},
    ]
    ctx = _ctx(events)
    execute_tool("delete_workout", {"date": "2026-09-21", "sport": "sykkel"}, ctx)
    assert len(ctx.staged_ops) == 1
    assert ctx.staged_ops[0]["id"] == 1


def test_adjust_load_no_events():
    ctx = _ctx([])
    out = execute_tool("adjust_load", {"percent": -10}, ctx)
    assert "synk kalender" in out.lower()


def test_adjust_load_repo_fallback(tmp_path):
    shutil.copytree(REPO_ROOT / "LOFOTEN-2027", tmp_path / "LOFOTEN-2027")
    settings = Settings(
        slack_bot_token="x",
        slack_app_token="x",
        slack_signing_secret="x",
        intervals_athlete_id="i1",
        intervals_api_key="k",
        openai_api_key="k",
        repo_root=tmp_path,
    )
    repo = RepoReader(settings)
    ctx = ToolContext(intervals=_Intervals([]), repo=repo, sessions=_Sessions(), user_id="U1")
    out = execute_tool("adjust_load", {"percent": -20}, ctx)
    assert "repo" in out.lower()
    assert ctx.sessions.pending["U1"][0] == "intervals_week"


def test_web_search_unconfigured(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert not web_search.is_enabled()
    out = web_search.search_web("nye karbo-geler 2027")
    assert "ikke konfigurert" in out.lower()


def test_web_search_tool_advertised_only_when_enabled(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    names = {s["function"]["name"] for s in tool_schemas()}
    assert "web_search" not in names
    names_on = {s["function"]["name"] for s in tool_schemas(web_search_enabled=True)}
    assert "web_search" in names_on


def test_web_search_format_results():
    data = {
        "answer": "Kort svar.",
        "results": [{"title": "T", "content": "Innhold", "url": "http://x"}],
    }
    out = web_search.format_results(data)
    assert "Kort svar" in out and "http://x" in out
