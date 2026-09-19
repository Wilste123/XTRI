"""SQLite conversation memory per Slack user."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SessionStore:
    def __init__(self, db_path: Path, max_turns: int = 10) -> None:
        self._path = db_path
        self._max_turns = max_turns
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_turns_user ON turns(user_id, id DESC)"
            )

    def append(self, user_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO turns (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content[:8000]),
            )
            conn.execute(
                """
                DELETE FROM turns WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM turns WHERE user_id = ? ORDER BY id DESC LIMIT ?
                )
                """,
                (user_id, user_id, self._max_turns * 2),
            )

    def format_history(self, user_id: str, max_chars: int = 1500) -> str:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM turns WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, self._max_turns * 2),
            ).fetchall()
        if not rows:
            return ""
        lines: list[str] = []
        for row in reversed(rows):
            lines.append(f"{row['role']}: {row['content'][:400]}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            return text[-max_chars:]
        return text
