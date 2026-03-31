import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class TaskCreate(BaseModel):
    social_account_id: uuid.UUID
    task_type: Literal["auto_like", "auto_follow", "auto_unfollow"]
    search_keyword: str | None = Field(default=None, max_length=500)
    target_username: str | None = Field(default=None, max_length=50)
    is_enabled: bool = False
    cron_expression: str = "*/30 * * * *"


class TaskUpdate(BaseModel):
    search_keyword: str | None = Field(default=None, max_length=500)
    target_username: str | None = Field(default=None, max_length=50)
    is_enabled: bool | None = None
    cron_expression: str | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    social_account_id: uuid.UUID
    task_type: str
    search_keyword: str | None
    target_username: str | None
    is_enabled: bool
    cron_expression: str
    total_executed: int
    total_success: int
    total_failed: int
    last_executed_at: datetime | None
    next_execute_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskLogResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    executed_at: datetime
    target_x_user_id: str | None
    target_tweet_id: str | None
    action: str
    error_message: str | None
    response_time_ms: int | None

    model_config = {"from_attributes": True}
