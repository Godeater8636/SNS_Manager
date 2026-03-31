import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


class AffiliateLinkCreate(BaseModel):
    name: str = Field(..., max_length=200)
    destination_url: str
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    expires_at: datetime | None = None
    redirect_on_expire: str | None = None


class AffiliateLinkUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    destination_url: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class AffiliateLinkResponse(BaseModel):
    id: uuid.UUID
    name: str
    destination_url: str
    short_url: str
    slug: str
    tags: list[str]
    description: str | None
    total_clicks: int
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DailyStat(BaseModel):
    date: str
    clicks: int


class LinkStats(BaseModel):
    total_clicks: int
    clicks_today: int
    clicks_this_week: int
    clicks_this_month: int
    daily_series: list[DailyStat]


class AffiliateLinkDetailResponse(BaseModel):
    link: AffiliateLinkResponse
    stats: LinkStats
