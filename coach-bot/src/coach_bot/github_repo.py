"""Optional GitHub Contents API sync for LOFOTEN-2027 files (Fly + git SoT)."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from coach_bot.config import Settings

logger = logging.getLogger(__name__)

_SYNC_PATHS = (
    "LOFOTEN-2027/11_ATLAS.md",
    "LOFOTEN-2027/CURRENT_STATUS.md",
    "LOFOTEN-2027/08_UTSTYR.md",
    "LOFOTEN-2027/01_OM_WILLIAM.md",
    "LOFOTEN-2027/03_DAGENS_NIVA.md",
)


class GitHubRepoSync:
    def __init__(self, settings: Settings) -> None:
        self._token = settings.github_token.strip()
        self._repo = settings.github_repo.strip()
        self._branch = settings.github_branch.strip() or "main"
        self._root = settings.repo_root
        self._enabled = bool(self._token and self._repo)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def pull_sync_files(self) -> list[str]:
        """Download key markdown files into REPO_ROOT. Returns paths updated."""
        if not self._enabled:
            return []
        updated: list[str] = []
        with httpx.Client(timeout=30.0) as client:
            for rel in _SYNC_PATHS:
                try:
                    r = client.get(
                        f"https://api.github.com/repos/{self._repo}/contents/{rel}",
                        params={"ref": self._branch},
                        headers=self._headers(),
                    )
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    data = r.json()
                    if data.get("encoding") != "base64":
                        continue
                    raw = base64.b64decode(data["content"])
                    dest = self._root / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(raw)
                    updated.append(rel)
                except Exception:
                    logger.exception("GitHub pull failed for %s", rel)
        return updated

    def commit_file(self, repo_relative: str, content: str, message: str) -> bool:
        """Create or update a file in the GitHub repo."""
        if not self._enabled:
            return False
        path = repo_relative.replace("\\", "/").lstrip("/")
        if not path.startswith("LOFOTEN-2027/"):
            path = f"LOFOTEN-2027/{path.removeprefix('LOFOTEN-2027/')}"

        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        url = f"https://api.github.com/repos/{self._repo}/contents/{path}"
        with httpx.Client(timeout=30.0) as client:
            sha = None
            gr = client.get(url, params={"ref": self._branch}, headers=self._headers())
            if gr.status_code == 200:
                sha = gr.json().get("sha")
            payload: dict = {
                "message": message,
                "content": encoded,
                "branch": self._branch,
            }
            if sha:
                payload["sha"] = sha
            pr = client.put(url, json=payload, headers=self._headers())
            if pr.status_code not in (200, 201):
                logger.error("GitHub commit failed %s: %s", pr.status_code, pr.text[:500])
                return False
        return True

    def commit_lofoten_file(self, lofoten_relative: str, content: str, message: str) -> bool:
        rel = lofoten_relative.replace("\\", "/").lstrip("/")
        return self.commit_file(f"LOFOTEN-2027/{rel}", content, message)

    def publish_local(self, local_path: Path, commit_message: str) -> bool:
        try:
            rel = local_path.relative_to(self._root / "LOFOTEN-2027")
        except ValueError:
            return False
        text = local_path.read_text(encoding="utf-8")
        return self.commit_lofoten_file(str(rel), text, commit_message)
