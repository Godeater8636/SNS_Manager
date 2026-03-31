import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ThreadItem(BaseModel):
    content: str = Field(..., max_length=280)
    media_urls: list[str] | None = Field(default=None, max_length=4)


class PostCreate(BaseModel):
    social_account_id: uuid.UUID
    scheduled_at: datetime | None = None
    thread: list[ThreadItem] = Field(..., min_length=1, max_length=25)

    @field_validator("thread")
    @classmethod
    def validate_thread(cls, v: list[ThreadItem]) -> list[ThreadItem]:
        if not v:
            raise ValueError("投稿内容を1つ以上入力してください")
        return v


class PostUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=280)
    scheduled_at: datetime | None = None
    media_urls: list[str] | None = None


class PostResponse(BaseModel):
    id: uuid.UUID
    social_account_id: uuid.UUID
    parent_post_id: uuid.UUID | None
    thread_order: int
    content: str
    media_urls: list[str] | None
    scheduled_at: datetime | None
    posted_at: datetime | None
    status: str
    x_tweet_id: str | None
    retry_count: int
    is_template: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PostCreateResponse(BaseModel):
    posts: list[PostResponse]


class CsvImportResponse(BaseModel):
    created: int
    failed: int
    errors: list[dict]


class PostAnalyticsResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    fetched_at: datetime
    impressions: int
    likes: int
    retweets: int
    replies: int
    quotes: int
    bookmarks: int
    link_clicks: int
    engagement_rate: float | None

    model_config = {"from_attributes": True}
