import shutil
from datetime import date
from pathlib import Path

from coach_bot.config import Settings
from coach_bot.intervals_planner import (
    coach_external_id,
    events_from_repo_plan,
    parse_single_workout_request,
    parse_week_plan_table,
)
from coach_bot.repo_reader import RepoReader

BASELINE = Path(__file__).resolve().parents[2] / "LOFOTEN-2027" / "ukeplan" / "baseline-uke.md"

SAMPLE = """
| Dag | Økt | Varighet |
| --- | --- | ---: |
| Man | Styrke A | 35 min |
| Tir | Løp 40 min lett | 40 min |
| Søn | Fri | 0 min |
"""


def test_parse_week_plan_table():
    events = parse_week_plan_table(SAMPLE, date(2026, 9, 14))
    assert len(events) == 2
    assert events[0]["type"] in ("Workout", "Run")


def test_parse_single_workout():
    ev = parse_single_workout_request("legg inn løp 45 min på tirsdag", date(2026, 9, 16))
    assert ev is not None
    assert ev["planned_duration"] == 45 * 60


def test_parse_real_baseline_week():
    md = BASELINE.read_text(encoding="utf-8")
    events = parse_week_plan_table(md, date(2026, 9, 14))
    assert len(events) >= 6
    names = " ".join(e["name"].lower() for e in events)
    assert "løp" in names or "jogg" in names or "jevn" in names


def test_events_from_repo_plan_forward_from_today(tmp_path):
    lof = tmp_path / "LOFOTEN-2027" / "ukeplan"
    lof.mkdir(parents=True)
    shutil.copy(BASELINE, lof / "baseline-uke.md")
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
    as_of = date(2026, 9, 20)
    events = events_from_repo_plan(repo, as_of, skip_past=True)
    assert len(events) >= 6
    dates = sorted((e["start_date_local"] or "")[:10] for e in events)
    assert dates[0] >= "2026-09-20"
    assert dates[0] != "2026-09-14"
    for e in events:
        assert e.get("load") or e.get("icu_training_load")
        d = date.fromisoformat((e["start_date_local"] or "")[:10])
        assert e["external_id"] == coach_external_id(d, e["type"])


def test_events_from_repo_plan_respects_start_date(tmp_path):
    lof = tmp_path / "LOFOTEN-2027" / "ukeplan"
    lof.mkdir(parents=True)
    shutil.copy(BASELINE, lof / "baseline-uke.md")
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
    start = date(2026, 9, 22)
    events = events_from_repo_plan(
        repo, date(2026, 9, 20), start_date=start, skip_past=True
    )
    assert (events[0]["start_date_local"] or "").startswith("2026-09-22")
