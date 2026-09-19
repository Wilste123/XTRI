"""Project memory: repo markdown + Supabase snapshots."""

from __future__ import annotations

from coach_bot.repo_reader import RepoReader
from coach_bot.supabase_store import NullSupabaseStore, SupabaseStore


class ProjectMemory:
    def __init__(
        self,
        repo: RepoReader,
        db: SupabaseStore | NullSupabaseStore,
    ) -> None:
        self._repo = repo
        self._db = db

    def current_status(self) -> str:
        if self._db.enabled:
            latest = self._db.latest_status_md()
            if latest:
                return latest[:4000]
        return self._repo.current_status()

    def masterplan_excerpt(self, max_chars: int = 3500) -> str:
        return self._repo.masterplan_excerpt(max_chars=max_chars)

    def dagens_niva_excerpt(self, max_chars: int = 2000) -> str:
        return self._repo.dagens_niva_excerpt(max_chars=max_chars)

    def bundle_for_coach(self) -> dict[str, str]:
        return {
            "current_status": self.current_status(),
            "masterplan_excerpt": self.masterplan_excerpt(),
            "dagens_niva_excerpt": self.dagens_niva_excerpt(),
        }

    def seed_supabase_from_repo(self) -> bool:
        if not self._db.enabled:
            return False
        return self._db.seed_status_from_markdown(
            self._repo.read("CURRENT_STATUS.md"),
            created_by="repo_import",
        )

    def import_status_from_repo(self) -> None:
        if not self._db.enabled:
            return
        content = self._repo.read("CURRENT_STATUS.md")
        self._db.insert_status(
            content,
            source="import",
            created_by="repo_sync",
            summary="Sync fra CURRENT_STATUS.md",
        )
