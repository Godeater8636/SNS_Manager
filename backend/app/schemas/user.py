import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class PlanInfo(BaseModel):
    name: str
    display_name: str
    price_jpy: int
    max_accounts: int
    max_posts_month: int | None
    can_automate: bool
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    timezone: str
    is_active: bool
    plan: PlanInfo | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    timezone: str | None = None


class TotpSetupResponse(BaseModel):
    secret: str
    qr_url: str


class TotpVerifyRequest(BaseModel):
    code: str
