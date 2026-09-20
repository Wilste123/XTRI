"""End-to-end offline flow tests.

Drives the full CoachOrchestrator DM pipeline with fake Intervals + LLM (no
network), plus chart rendering and Slack delivery, to prove every documented
DM path actually runs. Repo reads/writes use a temp copy of LOFOTEN-2027.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from coach_bot.charts import render_ctl_atl_chart, render_discipline_week_chart
from coach_bot.config import Settings
from coach_bot.context_builder import ContextBuilder
from coach_bot.coach_reply import CoachReply
from coach_bot.intent import Intent
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.repo_reader import RepoReader
from coach_bot.repo_writer import RepoWriter
from coach_bot.session_store import SessionStore
from coach_bot.slack_post import deliver_coach_reply, post_coach_reply
from coach_bot.workout_extract import extract_workout_from_text

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 18)

_PROPOSAL = (
    "## Plan for i morgen\n"
    "### Anbefalt økt\n"
    "- **Type:** Sykkelintervall\n"
    "- **Varighet:** 1 time\n"
    "- 10 min oppvarming, 5 x 3 min, 10 min ned.\n"
)


class FakeLlm:
    """Deterministic stand-in for OpenAILlmClient."""

    def __init__(self) -> None:
        self.calls: list[Intent] = []

    def complete_chat(
        self,
        context,
        user_message,
        intent=Intent.GENERAL,
        history="",
        history_messages=None,
    ) -> str:
        self.calls.append(intent)
        if intent == Intent.TOMORROW:
            return _PROPOSAL
        return "## Oppsummering\nDu ligger greit an.\n\n## Neste steg\nHold volum."


class FakeIntervals:
    """Stand-in for IntervalsClient with the surface the coach uses."""

    def __init__(self, activities, wellness) -> None:
        self._activities = activities
        self._wellness = wellness
        self.created: list[dict] = []
        self.bulk: list[dict] = []

    def today(self) -> date:
        return TODAY

    def fetch_coach_bundle(self, activity_days: int = 28) -> dict:
        return {
            "activities": list(self._activities),
            "events": [],
            "wellness": list(self._wellness),
        }

    def create_event(self, event: dict) -> dict:
        self.created.append(event)
        return event

    def bulk_upsert_events(self, events: list[dict]) -> list[dict]:
        self.bulk.extend(events)
        return events

    def get_events(self, oldest, newest):
        return []

    def delete_event(self, event_id):
        self.deleted = getattr(self, "deleted", [])
        self.deleted.append(event_id)

    def ping(self) -> None:
        return None


class FakeWebClient:
    """Records Slack calls so delivery paths can be asserted offline."""

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.uploads: list[dict] = []

    def conversations_open(self, users):
        return {"channel": {"id": "D999"}}

    def chat_postMessage(self, **kwargs):
        self.messages.append(kwargs)
        return {"ts": f"1700.{len(self.messages)}"}

    def files_upload_v2(self, **kwargs):
        self.uploads.append(kwargs)
        return {"ok": True}

    def reactions_add(self, **kwargs):
        return {"ok": True}


def _load_activities():
    return json.loads((FIXTURES / "activities_sample.json").read_text())


def _wellness_rows():
    # Enough CTL/ATL points for a chart line (>= 2).
    base = [
        ("2026-09-12", 30, 34),
        ("2026-09-13", 31, 40),
        ("2026-09-14", 32, 38),
        ("2026-09-15", 33, 42),
        ("2026-09-16", 34, 41),
        ("2026-09-17", 35, 45),
        ("2026-09-18", 36, 39),
    ]
    return [{"id": d, "ctl": c, "atl": a} for d, c, a in base]


@pytest.fixture()
def orch(tmp_path):
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
    intervals = FakeIntervals(_load_activities(), _wellness_rows())
    repo = RepoReader(settings)
    context = ContextBuilder(intervals, repo, settings.tz)
    sessions = SessionStore(tmp_path / "sessions.db", settings.session_max_turns)
    llm = FakeLlm()
    orchestrator = CoachOrchestrator(
        context, llm, sessions, RepoWriter(settings), intervals=intervals, repo=repo
    )
    return {
        "orch": orchestrator,
        "intervals": intervals,
        "llm": llm,
        "settings": settings,
        "repo_dir": tmp_path / "LOFOTEN-2027",
    }


def test_reset_clears_history(orch):
    r = orch["orch"].run_chat("nullstill", user_id="U1")
    assert "nullstill" in r.text.lower()


@pytest.mark.parametrize(
    "msg",
    [
        "hvordan ligger jeg an?",
        "ukestatus",
        "hva skal jeg gjøre i morgen?",
        "gi meg en analyse",
        "det gjør vondt i kneet",
        "fortell om lofoten cutoff",
    ],
)
def test_chat_paths_produce_reply(orch, msg):
    r = orch["orch"].run_chat(msg, user_id="U1")
    assert isinstance(r, CoachReply)
    assert r.text and r.text.strip()
    # Coachens egne svar er ren mentor-tekst (ingen «tittelkort»-overskrifter).
    assert "##" not in r.text
    assert not r.text.lower().startswith("coach")


def test_status_and_week_attach_charts(orch):
    for msg in ("hvordan ligger jeg an?", "ukestatus"):
        r = orch["orch"].run_chat(msg, user_id="U1")
        assert r.image_paths, f"expected charts for '{msg}'"
        for p in r.image_paths:
            assert Path(p).is_file()


def test_log_writes_to_current_status(orch):
    r = orch["orch"].run_chat("logg: kne 3/10 etter løp", user_id="U1")
    assert "CURRENT_STATUS" in r.text
    txt = (orch["repo_dir"] / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    assert "kne 3/10 etter løp" in txt


def test_direct_single_workout_preview_then_confirm(orch):
    o = orch["orch"]
    preview = o.run_chat("legg inn sykkel 60 min i morgen", user_id="U1")
    assert "ja" in preview.text.lower()
    assert not orch["intervals"].created
    confirm = o.run_chat("ja", user_id="U1")
    assert "Lagt inn i Intervals" in confirm.text
    created = orch["intervals"].created
    assert len(created) == 1
    assert created[0]["type"] == "Ride"
    assert created[0]["planned_duration"] == 60 * 60
    assert created[0]["start_date_local"].startswith("2026-09-19")


def test_week_sync_preview_then_confirm(orch):
    o = orch["orch"]
    preview = o.run_chat("synk kalender", user_id="U2")
    # Forhåndsvisning vises (kompakt UX lister økter + «ja»-instruks); ingen skriv ennå.
    assert preview.text.strip()
    assert "ja" in preview.text.lower()
    assert "2026-09-14" not in preview.text
    assert "2026-09-18" in preview.text or "2026-09-19" in preview.text
    assert not orch["intervals"].bulk  # ingenting skrevet før bekreftelse
    confirm = o.run_chat("ja", user_id="U2")
    assert "Lagt inn" in confirm.text
    assert orch["intervals"].bulk  # nå er økter skrevet


def test_proposal_then_followup_commit(orch):
    o = orch["orch"]
    proposal = o.run_chat(
        "kan du legge inn en økt for i morgen i intervals?", user_id="U3"
    )
    assert "morgen" in proposal.text.lower()
    assert not orch["intervals"].created
    commit = o.run_chat("legg den inn i intervals", user_id="U3")
    assert "Lagt inn i Intervals" in commit.text
    assert len(orch["intervals"].created) == 1
    assert orch["intervals"].created[0]["type"] == "Ride"


def test_cancel_pending(orch):
    o = orch["orch"]
    o.run_chat("synk kalender", user_id="U4")
    r = o.run_chat("avbryt", user_id="U4")
    assert "Avbrutt" in r.text
    assert not orch["intervals"].bulk


def test_capabilities_charts_and_plan(orch):
    r = orch["orch"].run_chat(
        "kan du lage grafer og legge inn treningsplaner?", user_id="U5"
    )
    assert r.blocks
    assert r.image_paths  # grafer vedlagt
    # Forhåndsvisning av ukeplan lagt til
    assert "Forhåndsvisning" in r.text or "ukeplan" in r.text.lower()


def test_rosa_graf_without_week_sync_noise(orch):
    r = orch["orch"].run_chat(
        "kan du lage en rosa graf for uken som har gått?", user_id="U10"
    )
    assert "Ingen ukeplan" not in r.text
    assert r.image_paths


def test_sync_week_missing_file_message(tmp_path):
    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    shutil.copy(REPO_ROOT / "LOFOTEN-2027" / "CURRENT_STATUS.md", lof / "CURRENT_STATUS.md")
    settings = Settings(
        slack_bot_token="x",
        slack_app_token="x",
        slack_signing_secret="x",
        intervals_athlete_id="i1",
        intervals_api_key="k",
        openai_api_key="k",
        repo_root=tmp_path,
    )
    intervals = FakeIntervals(_load_activities(), _wellness_rows())
    repo = RepoReader(settings)
    o = CoachOrchestrator(
        ContextBuilder(intervals, repo, settings.tz),
        FakeLlm(),
        SessionStore(tmp_path / "s.db", 10),
        RepoWriter(settings),
        intervals=intervals,
        repo=repo,
    )
    r = o.run_chat("synk kalender", user_id="U11")
    assert "REPO_ROOT" in r.text or "fil mangler" in r.text.lower()


def test_deliver_briefings_via_slack(orch):
    client = FakeWebClient()
    orch["orch"].deliver_morning_briefing(client, "U1")
    orch["orch"].deliver_weekly_briefing(client, "U1")
    assert len(client.messages) >= 2
    # Ukebriefing legger ved grafer -> minst ett bildeopplasting
    assert client.uploads


def test_post_coach_reply_uploads_images(orch, tmp_path):
    client = FakeWebClient()
    png = render_discipline_week_chart(_load_activities(), TODAY)
    assert png is not None and png.is_file()
    reply = CoachReply(text="Test", image_paths=[png])
    ts = post_coach_reply(client, "D1", reply)
    assert ts is not None
    assert len(client.uploads) == 1
    assert not png.exists()  # ryddes opp etter opplasting


def test_charts_render_files():
    ctl = render_ctl_atl_chart(_wellness_rows())
    disc = render_discipline_week_chart(_load_activities(), TODAY)
    assert ctl is not None and ctl.is_file()
    assert disc is not None and disc.is_file()
    ctl.unlink(missing_ok=True)
    disc.unlink(missing_ok=True)


def test_extract_workout_external_id_is_stable():
    a = extract_workout_from_text(_PROPOSAL, as_of=TODAY)
    b = extract_workout_from_text(_PROPOSAL, as_of=TODAY)
    assert a is not None and b is not None
    assert a["external_id"] == b["external_id"]


class DenyingLlm(FakeLlm):
    """Simulates the model wrongly refusing to write to Intervals."""

    def complete_chat(self, *args, **kwargs) -> str:
        return (
            "Beklager misforståelsen. Jeg kan ikke direkte legge inn økten i "
            "Intervals.icu, men jeg kan gi deg instruksjoner."
        )


def test_reply_never_denies_ability(orch):
    # Bytt inn en LLM som fornekter evnen, og sjekk at coachen ikke sender det videre.
    orch["orch"]._llm = DenyingLlm()
    r = orch["orch"].run_chat("hvordan ligger jeg an?", user_id="U9")
    low = r.text.lower()
    assert "kan ikke" not in low
    assert "beklager misforståelsen" not in low
    # Skal i stedet tilby å legge inn økten.
    assert "legg" in low or "ja" in low


_PLAN_LLM_TEXT = (
    "Her er planen for de neste dagene:\n"
    "**19. september (i dag)**: Løpeøkt 45 min rolig.\n"
    "**20. september**: Sykle 1 time lav intensitet.\n"
    "**21. september**: Svøm 30 min teknikk.\n"
)


class PlanLlm(FakeLlm):
    def complete_chat(self, *args, **kwargs) -> str:
        return _PLAN_LLM_TEXT


class ToolCallingLlm(FakeLlm):
    """Simulates a model that calls tools (function calling) offline."""

    def complete_agentic(
        self,
        context,
        user_message,
        *,
        history_messages=None,
        tools=None,
        tool_executor=None,
        intent=Intent.GENERAL,
        max_iters=5,
    ) -> str:
        low = user_message.lower()
        if tool_executor and ("plan" in low or "uke" in low):
            tool_executor(
                "create_workouts",
                {
                    "workouts": [
                        {"date": "2026-09-20", "sport": "run", "duration_min": 45},
                        {"date": "2026-09-21", "sport": "bike", "duration_min": 60},
                        {"date": "2026-09-22", "sport": "swim", "duration_min": 30},
                    ]
                },
            )
            return "Her er et forslag til uken. Si ifra om du vil ha den inn."
        if tool_executor and ("vondt" in low or "skade" in low):
            facts = tool_executor("search_knowledge", {"query": user_message})
            return f"Basert på det jeg vet: {facts[:60]}"
        if tool_executor and ("graf" in low or "visuell" in low):
            tool_executor("render_charts", {})
            return "Her kommer grafene."
        return "Alt vel – hva vil du ta tak i?"


def test_ja_without_pending_skips_agentic(orch):
    o = orch["orch"]
    o._llm = ToolCallingLlm()
    r = o.run_chat("ja", user_id="U_NO_PENDING")
    assert "Ingen ventende plan" in r.text
    assert not orch["intervals"].bulk
    assert not o._sessions.get_pending("U_NO_PENDING")


def test_agentic_creates_plan_via_tool(orch):
    o = orch["orch"]
    o._llm = ToolCallingLlm()
    preview = o.run_chat("lag en plan for uken", user_id="UA")
    # Modellen kalte create_workouts -> økter staged + forhåndsvisning + affordance.
    assert preview.blocks
    assert "ja" in preview.text.lower()
    assert not orch["intervals"].bulk
    confirm = o.run_chat("ja", user_id="UA")
    assert "Lagt inn" in confirm.text
    assert len(orch["intervals"].bulk) == 3


def test_agentic_knowledge_lookup(orch):
    o = orch["orch"]
    o._llm = ToolCallingLlm()
    r = o.run_chat("jeg har vondt i kneet, hva gjør jeg?", user_id="UB")
    assert "kan ikke" not in r.text.lower()
    assert r.text.strip()


def test_agentic_charts_via_tool(orch):
    o = orch["orch"]
    o._llm = ToolCallingLlm()
    r = o.run_chat("vis formen min som graf", user_id="UC")
    # render_charts-verktøyet -> grafer vedlagt
    assert r.image_paths


def test_intervals_ops_commit_on_ja(orch):
    # Simuler at et verktøy har staged endringer (flytt + slett), så bekreft.
    o = orch["orch"]
    o._sessions.set_pending(
        "UZ",
        "intervals_ops",
        {
            "ops": [
                {"op": "upsert", "event": {"id": 1, "name": "Løp", "start_date_local": "2026-09-21T00:00:00"}},
                {"op": "delete", "id": 2, "label": "slett"},
            ]
        },
    )
    r = o.run_chat("ja", user_id="UZ")
    assert "oppdatert" in r.text.lower()
    assert orch["intervals"].bulk  # upsert utført
    assert getattr(orch["intervals"], "deleted", []) == [2]  # delete utført


def test_full_plan_write_from_chat(orch):
    o = orch["orch"]
    o._llm = PlanLlm()
    # Coachen foreslår en flerdagers plan i chatten ...
    o.run_chat("kan du lage en plan for de neste dagene?", user_id="UP")
    # ... og «legg inn hele planen» skal fange ALLE dagene, ikke bare én.
    preview = o.run_chat("legg inn hele planen", user_id="UP")
    assert preview.text.count("2026-09") >= 3
    assert not orch["intervals"].bulk  # ingen skriv før bekreftelse
    confirm = o.run_chat("ja", user_id="UP")
    assert "Lagt inn" in confirm.text
    assert len(orch["intervals"].bulk) == 3
