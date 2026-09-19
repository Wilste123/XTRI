from datetime import date
from pathlib import Path

from coach_bot.config import Settings
from coach_bot.repo_writer import RepoWriter


def test_append_status_note(tmp_path, monkeypatch):
    lofoten = tmp_path / "LOFOTEN-2027"
    lofoten.mkdir()
    (lofoten / "CURRENT_STATUS.md").write_text(
        "# Status\n\n## Kort notat (valgfritt)\n\nEksisterende.\n",
        encoding="utf-8",
    )
    settings = Settings(
        slack_bot_token="x",
        slack_app_token="x",
        slack_signing_secret="x",
        intervals_athlete_id="i1",
        intervals_api_key="k",
        openai_api_key="k",
        repo_root=tmp_path,
    )
    RepoWriter(settings).append_status_note("kne 3/10", on_date=date(2026, 9, 19))
    text = (lofoten / "CURRENT_STATUS.md").read_text()
    assert "2026-09-19" in text
    assert "kne 3/10" in text
