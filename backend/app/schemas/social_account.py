import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SocialAccountCreate(BaseModel):
    x_username: str
    password: str
    daily_like_limit: int = Field(default=200, ge=0, le=500)
    daily_follow_limit: int = Field(default=100, ge=0, le=400)
    action_min_interval_sec: int = Field(default=30, ge=10, le=300)
    action_max_interval_sec: int = Field(default=90, ge=10, le=600)
    active_hours_start: int = Field(default=7, ge=0, le=23)
    active_hours_end: int = Field(default=23, ge=0, le=23)
    burst_size: int = Field(default=10, ge=1, le=50)
    burst_rest_sec: int = Field(default=300, ge=60, le=3600)


class SocialAccountUpdate(BaseModel):
    daily_like_limit: int | None = Field(default=None, ge=0, le=500)
    daily_follow_limit: int | None = Field(default=None, ge=0, le=400)
    action_min_interval_sec: int | None = Field(default=None, ge=10, le=300)
    action_max_interval_sec: int | None = Field(default=None, ge=10, le=600)
    active_hours_start: int | None = Field(default=None, ge=0, le=23)
    active_hours_end: int | None = Field(default=None, ge=0, le=23)
    burst_size: int | None = Field(default=None, ge=1, le=50)
    burst_rest_sec: int | None = Field(default=None, ge=60, le=3600)
    is_active: bool | None = None


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    x_username: str
    x_display_name: str | None
    platform: str
    is_active: bool
    last_login_at: datetime | None
    session_expires_at: datetime | None
    daily_likes_count: int
    daily_follows_count: int
    daily_like_limit: int
    daily_follow_limit: int
    action_min_interval_sec: int
    action_max_interval_sec: int
    active_hours_start: int
    active_hours_end: int
    burst_size: int
    burst_rest_sec: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionRefreshResponse(BaseModel):
    session_expires_at: datetime | None
