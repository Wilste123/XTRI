from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    slack_bot_token: str
    slack_app_token: str
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

    intervals_cache_ttl_seconds: int = 180

    morning_briefing_enabled: bool = False
    morning_briefing_hour: int = 7
    morning_briefing_minute: int = 0

    weekly_briefing_enabled: bool = False
    weekly_briefing_weekday: int = 6
    weekly_briefing_hour: int = 18
    weekly_briefing_minute: int = 0

    coach_week_override: str = ""
    session_max_turns: int = 10
    session_db_path: Path = Path("data/sessions.db")

    admin_briefing_secret: str = ""
    intervals_max_bulk_events: int = 14

    @field_validator(
        "slack_bot_token",
        "slack_app_token",
        "slack_signing_secret",
        "intervals_athlete_id",
        "intervals_api_key",
        "openai_api_key",
        "allowed_slack_user_ids",
        mode="before",
    )
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

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
