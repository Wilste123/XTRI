"""Write subjective notes to LOFOTEN-2027 (minimal)."""

from __future__ import annotations

from datetime import date

from coach_bot.config import Settings


class RepoWriter:
    def __init__(self, settings: Settings) -> None:
        self._status_path = settings.lofoten_dir / "CURRENT_STATUS.md"

    def append_status_note(self, note: str, on_date: date | None = None) -> None:
        if not self._status_path.is_file():
            raise FileNotFoundError(str(self._status_path))
        d = on_date or date.today()
        line = f"- {d.isoformat()}: {note.strip()}\n"
        text = self._status_path.read_text(encoding="utf-8")
        marker = "## Kort notat (valgfritt)"
        if marker not in text:
            text = text.rstrip() + f"\n\n{marker}\n\n{line}"
        else:
            parts = text.split(marker, 1)
            rest = parts[1]
            if "\n## " in rest:
                before, after = rest.split("\n## ", 1)
                rest = before.rstrip() + "\n" + line + "\n## " + after
            else:
                rest = rest.rstrip() + "\n" + line
            text = parts[0] + marker + rest
        self._status_path.write_text(text, encoding="utf-8")
