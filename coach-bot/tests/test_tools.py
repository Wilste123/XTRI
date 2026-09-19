import json
from datetime import date

from coach_bot.tools import ToolContext, execute_tool


class _Sessions:
    def __init__(self):
        self.pending = {}

    def set_pending(self, user_id, action_type, payload):
        self.pending[user_id] = (action_type, payload)


class _Intervals:
    def today(self):
        return date(2026, 9, 19)


class _RepoWriter:
    def __init__(self):
        self.notes = []

    def append_status_note(self, note):
        self.notes.append(note)


def _ctx(**kw):
    base = dict(intervals=_Intervals(), sessions=_Sessions(), user_id="U1")
    base.update(kw)
    return ToolContext(**base)


def test_create_workouts_stages_week_and_sets_pending():
    ctx = _ctx()
    args = {
        "workouts": [
            {"date": "2026-09-20", "sport": "run", "duration_min": 45},
            {"date": "2026-09-21", "sport": "bike", "duration_min": 60},
            {"date": "2026-09-22", "sport": "swim", "duration_min": 30},
        ]
    }
    out = execute_tool("create_workouts", json.dumps(args), ctx)
    assert "venter" in out.lower() or "bekreft" in out.lower()
    assert len(ctx.staged_events) == 3
    action, payload = ctx.sessions.pending["U1"]
    assert action == "intervals_week"
    assert len(payload["events"]) == 3
    assert ctx.staged_events[0]["type"] == "Run"
    assert ctx.staged_events[1]["planned_duration"] == 60 * 60


def test_create_workouts_single_sets_single_pending():
    ctx = _ctx()
    args = {"workouts": [{"date": "2026-09-20", "sport": "run", "duration_min": 45}]}
    execute_tool("create_workouts", args, ctx)
    action, payload = ctx.sessions.pending["U1"]
    assert action == "intervals_single"
    assert payload["event"]["type"] == "Run"


def test_create_workouts_rejects_bad_dates():
    ctx = _ctx()
    args = {"workouts": [{"date": "ikke-en-dato", "sport": "run", "duration_min": 45}]}
    out = execute_tool("create_workouts", args, ctx)
    assert "ingen gyldige" in out.lower()
    assert not ctx.staged_events


def test_search_knowledge_tool():
    out = execute_tool("search_knowledge", {"query": "vondt i kneet"}, _ctx())
    assert out and "skade" in out.lower()


def test_render_charts_tool_sets_flag():
    ctx = _ctx()
    execute_tool("render_charts", {}, ctx)
    assert ctx.want_charts is True


def test_log_note_tool_writes():
    rw = _RepoWriter()
    ctx = _ctx(repo_writer=rw)
    out = execute_tool("log_note", {"note": "kne 3/10 etter løp"}, ctx)
    assert "notert" in out.lower()
    assert rw.notes == ["kne 3/10 etter løp"]


def test_unknown_tool_is_safe():
    assert "ukjent" in execute_tool("does_not_exist", {}, _ctx()).lower()
