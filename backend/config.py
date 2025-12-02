from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration pulled from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    twitch_client_id: Optional[str] = Field(None, alias="TWITCH_CLIENT_ID")
    twitch_client_secret: Optional[str] = Field(None, alias="TWITCH_CLIENT_SECRET")
    twitch_app_token: Optional[str] = Field(None, alias="TWITCH_APP_TOKEN")
    twitch_chat_oauth_token: Optional[str] = Field(
        None, alias="TWITCH_CHAT_OAUTH_TOKEN"
    )
    twitch_bot_username: str = Field("justinfan12345", alias="TWITCH_BOT_USERNAME")

    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    redis_use_ssl: bool = Field(False, alias="REDIS_USE_SSL")

    max_messages: int = Field(10_000, alias="MAX_MESSAGES", ge=100)
    update_interval_ms: int = Field(
        500, alias="UPDATE_INTERVAL", description="Broadcast cadence in ms"
    )
    session_ttl_seconds: int = Field(
        2 * 60 * 60, alias="SESSION_TTL", description="Redis TTL per session"
    )
    default_duration_seconds: int = Field(60, alias="DEFAULT_DURATION", ge=10)
    max_duration_seconds: int = Field(5 * 60, alias="MAX_DURATION", ge=30)
    message_sample_rate: int = Field(1, alias="MESSAGE_SAMPLE_RATE", ge=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        "INFO", alias="LOG_LEVEL"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance to avoid repeated reads."""

    return Settings()
