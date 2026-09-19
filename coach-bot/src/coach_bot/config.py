from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str = ""
    slack_mode: str = "socket"
    slack_enable_slash: bool = False
    slack_enable_mentions: bool = False
    allowed_slack_user_ids: str = ""
    slack_notify_user_ids: str = ""

    repo_root: Path = Path("/Users/william/XTRI")

    intervals_athlete_id: str
    intervals_api_key: str
    intervals_base_url: str = "https://intervals.icu/api/v1"

    openai_api_key: str
    coach_model: str = "gpt-4o-mini"

    port: int = 8080
    tz: str = "Europe/Oslo"

    morning_brief_hour: int = 7
    morning_brief_minute: int = 0
    weekly_brief_enabled: bool = True
    weekly_brief_weekday: int = 6
    weekly_brief_hour: int = 18
    weekly_brief_minute: int = 0
    activity_poll_minutes: int = 15
    quiet_hours_start: int = 22
    quiet_hours_end: int = 6

    state_path: Path = Path("./data/coach_state.json")

    @field_validator("slack_mode")
    @classmethod
    def normalize_slack_mode(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_slack_mode(self) -> "Settings":
        if self.slack_mode == "socket" and not self.slack_app_token.strip():
            raise ValueError(
                "SLACK_APP_TOKEN is required when SLACK_MODE=socket "
                "(create app-level token with connections:write)"
            )
        return self

    @property
    def lofoten_dir(self) -> Path:
        return self.repo_root / "LOFOTEN-2027"

    @property
    def allowed_user_id_set(self) -> set[str]:
        if not self.allowed_slack_user_ids.strip():
            return set()
        return {u.strip() for u in self.allowed_slack_user_ids.split(",") if u.strip()}

    @property
    def notify_user_id_set(self) -> set[str]:
        raw = self.slack_notify_user_ids.strip()
        if raw:
            return {u.strip() for u in raw.split(",") if u.strip()}
        return self.allowed_user_id_set


@lru_cache
def get_settings() -> Settings:
    return Settings()
