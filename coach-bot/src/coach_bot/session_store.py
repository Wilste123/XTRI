"""SQLite conversation memory and pending actions per Slack user."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_actions (
                    user_id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
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

    def clear(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM turns WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM pending_actions WHERE user_id = ?", (user_id,))

    def get_messages(self, user_id: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM turns WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows[-(self._max_turns * 2) :]]

    def format_history(self, user_id: str, max_chars: int = 1500) -> str:
        msgs = self.get_messages(user_id)
        if not msgs:
            return ""
        lines = [f"{m['role']}: {m['content'][:400]}" for m in msgs]
        text = "\n".join(lines)
        if len(text) > max_chars:
            return text[-max_chars:]
        return text

    def set_pending(self, user_id: str, action_type: str, payload: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pending_actions (user_id, action_type, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    action_type=excluded.action_type,
                    payload_json=excluded.payload_json,
                    created_at=CURRENT_TIMESTAMP
                """,
                (user_id, action_type, json.dumps(payload)),
            )

    def pop_pending(self, user_id: str) -> tuple[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT action_type, payload_json FROM pending_actions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            conn.execute("DELETE FROM pending_actions WHERE user_id = ?", (user_id,))
        return row["action_type"], json.loads(row["payload_json"])

    def has_pending(self, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM pending_actions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def get_pending(self, user_id: str) -> tuple[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT action_type, payload_json FROM pending_actions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return row["action_type"], json.loads(row["payload_json"])

    def last_assistant_message(self, user_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT content FROM turns
                WHERE user_id = ? AND role = 'assistant'
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        return row["content"] if row else None
