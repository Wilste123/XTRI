from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    slack_bot_token: str
    slack_signing_secret: str
    allowed_slack_user_ids: str = ""

    repo_root: Path = Path("/Users/william/XTRI")

    intervals_athlete_id: str
    intervals_api_key: str
    intervals_base_url: str = "https://intervals.icu/api/v1"

    openai_api_key: str
    coach_model: str = "gpt-4o-mini"

    port: int = 3000
    tz: str = "Europe/Oslo"

    @property
    def lofoten_dir(self) -> Path:
        return self.repo_root / "LOFOTEN-2027"

    @property
    def allowed_user_id_set(self) -> set[str]:
        if not self.allowed_slack_user_ids.strip():
            return set()
        return {u.strip() for u in self.allowed_slack_user_ids.split(",") if u.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
