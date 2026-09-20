"""Startup checks for LOFOTEN-2027 week plan files."""

from __future__ import annotations

import logging
from datetime import date

from coach_bot.config import Settings
from coach_bot.intervals_planner import _monday_of_week, parse_week_plan_table
from coach_bot.repo_reader import RepoReader

logger = logging.getLogger(__name__)


def check_week_plan(repo: RepoReader, settings: Settings) -> None:
    """Log warning if active ukeplan cannot be parsed into events."""
    ref = repo.active_training_week(date.today())
    md = repo.read(ref.filename)
    if md.startswith("(fil mangler"):
        logger.warning(
            "Ukeplan utilgjengelig: %s (REPO_ROOT=%s, lofoten_dir=%s). "
            "På Fly: ikke sett REPO_ROOT via secrets – bruk /app fra fly.toml.",
            ref.filename,
            settings.repo_root,
            settings.lofoten_dir,
        )
        return
    week_start = _monday_of_week(date.today())
    events = parse_week_plan_table(md, week_start)
    if not events:
        logger.warning(
            "Ukeplan %s parse=0 events (REPO_ROOT=%s). Sjekk tabellformat i markdown.",
            ref.filename,
            settings.effective_repo_root,
        )
    else:
        logger.info(
            "Ukeplan OK: %s → %d økter (REPO_ROOT=%s)",
            ref.filename,
            len(events),
            settings.effective_repo_root,
        )
