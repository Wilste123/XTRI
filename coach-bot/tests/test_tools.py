import json
from datetime import date

from coach_bot import atlas
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


def test_create_workouts_session_type_threshold():
    ctx = _ctx()
    args = {
        "workouts": [
            {
                "date": "2026-09-22",
                "sport": "bike",
                "duration_min": 90,
                "session_type": "threshold_ride",
            }
        ]
    }
    execute_tool("create_workouts", args, ctx)
    ev = ctx.staged_events[0]
    assert "Main set" in ev["description"]
    assert ev["type"] == "Ride"
    assert ev.get("target") == "HR"


def test_build_workout_tool():
    from coach_bot.athlete_thresholds import AthleteThresholds, SportThresholds

    ctx = _ctx()

    class _ThIntervals(_Intervals):
        def get_athlete_thresholds(self):
            return AthleteThresholds(ride=SportThresholds(ftp=260, lthr=168))

    ctx.intervals = _ThIntervals()
    out = execute_tool(
        "build_workout", {"session_type": "threshold_ride", "sport": "bike"}, ctx
    )
    assert "Main set" in out
    assert "260" in out


def test_create_workouts_caps_duration():
    ctx = _ctx()
    args = {"workouts": [{"date": "2026-09-20", "sport": "bike", "duration_min": 300}]}
    execute_tool("create_workouts", args, ctx)
    assert ctx.staged_events[0]["planned_duration"] == 240 * 60


def test_remember_fact_tool(tmp_path):
    from coach_bot.repo_reader import RepoReader
    from coach_bot.config import Settings

    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    (lof / "CURRENT_STATUS.md").write_text("# Status\n", encoding="utf-8")

    class FakeSettings:
        repo_root = tmp_path
        lofoten_dir = lof
        coach_week_override = ""

    repo = RepoReader(FakeSettings())  # type: ignore[arg-type]
    ctx = ToolContext(repo=repo)
    out = execute_tool(
        "remember_fact",
        {"category": "utstyr", "fact": "Kjøpte Wahoo Elemnt ROAM"},
        ctx,
    )
    assert "Lagret" in out
    assert "Wahoo" in atlas.read_atlas(lof)


def test_search_personal_memory_tool(tmp_path):
    from coach_bot.repo_reader import RepoReader

    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    atlas.append_fact(lof, "helse", "Dårlig høyre kne i nedoverbakke")

    class FakeSettings:
        repo_root = tmp_path
        lofoten_dir = lof
        coach_week_override = ""

    repo = RepoReader(FakeSettings())  # type: ignore[arg-type]
    out = execute_tool("search_personal_memory", {"query": "kne"}, ToolContext(repo=repo))
    assert "kne" in out.lower()


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
