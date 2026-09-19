"""Read project memory from LOFOTEN-2027 markdown files."""

from __future__ import annotations

from pathlib import Path

from coach_bot.config import Settings


class RepoReader:
    def __init__(self, settings: Settings) -> None:
        self._root = settings.lofoten_dir

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

    def bundle_for_coach(self) -> dict[str, str]:
        return {
            "current_status": self.current_status(),
            "masterplan_excerpt": self.masterplan_excerpt(),
            "dagens_niva_excerpt": self.dagens_niva_excerpt(),
        }
