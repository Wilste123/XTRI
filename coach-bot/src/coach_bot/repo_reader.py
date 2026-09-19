"""Read project memory from LOFOTEN-2027 markdown files."""

from __future__ import annotations

import re
from pathlib import Path

from coach_bot.config import Settings
from coach_bot.coach_insights import WeekPlanRef, resolve_week_plan


class RepoReader:
    def __init__(self, settings: Settings) -> None:
        self._root = settings.lofoten_dir
        self._week_override = settings.coach_week_override

    def has_current_status(self) -> bool:
        return (self._root / "CURRENT_STATUS.md").is_file()

    def read(self, relative: str, max_chars: int | None = None) -> str:
        path = self._root / relative
        if not path.is_file():
            return f"(fil mangler: {relative})"
        text = path.read_text(encoding="utf-8")
        if max_chars and len(text) > max_chars:
            return text[:max_chars] + "\n\n…(truncated)"
        return text

    def masterplan_excerpt(self, max_chars: int = 3500) -> str:
        return self.read("00_MASTERPLAN.md", max_chars=max_chars)

    def current_status(self) -> str:
        return self.read("CURRENT_STATUS.md", max_chars=4000)

    def dagens_niva_excerpt(self, max_chars: int = 2000) -> str:
        return self.read("03_DAGENS_NIVA.md", max_chars=max_chars)

    def program_excerpt(self, max_chars: int = 2500) -> str:
        return self.read("04_TRENINGSPROGRAM.md", max_chars=max_chars)

    def test_results_excerpt(self, max_chars: int = 2000) -> str:
        return self.read("06_TESTRESULTATER.md", max_chars=max_chars)

    def week_plan_excerpt(self, as_of_date=None, max_chars: int = 4000) -> str:
        from datetime import date

        today = as_of_date or date.today()
        ref = self.active_training_week(today)
        return self.read(ref.filename, max_chars=max_chars)

    def active_training_week(self, as_of_date=None) -> WeekPlanRef:
        from datetime import date

        today = as_of_date or date.today()
        return resolve_week_plan(
            today,
            self.current_status(),
            self._week_override or None,
        )

    def detect_phase(self) -> str:
        text = self.current_status()
        m = re.search(r"\*\*Fase:\*\*\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return "Base_0"

    def bundle_for_coach(self) -> dict[str, str]:
        return {
            "current_status": self.current_status(),
            "masterplan_excerpt": self.masterplan_excerpt(),
            "dagens_niva_excerpt": self.dagens_niva_excerpt(),
            "program_excerpt": self.program_excerpt(),
            "test_results_excerpt": self.test_results_excerpt(),
        }
