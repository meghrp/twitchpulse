from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .config import get_settings

settings = get_settings()


class StartSessionRequest(BaseModel):
    channel: str = Field(..., min_length=2, max_length=25, pattern=r"^[a-zA-Z0-9_]+$")
    duration_seconds: int = Field(
        default=settings.default_duration_seconds,
        ge=10,
        le=settings.max_duration_seconds,
    )
    sample_rate: int = Field(default=settings.message_sample_rate, ge=1, le=20)

    @field_validator("channel")
    @classmethod
    def normalize_channel(cls, value: str) -> str:
        return value.lower()


class StartSessionResponse(BaseModel):
    session_id: str
    status: Literal["active", "complete", "error"]
    channel: str
    duration_seconds: int
    started_at: datetime
    expires_at: datetime


class StopSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=10)


class SessionStatsResponse(BaseModel):
    session_id: str
    channel: str
    message_count: int
    chatter_count: int
    messages_per_minute: int
    top_chatters: list
    top_emotes: list
    sentiment: dict

