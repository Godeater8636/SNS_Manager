import uuid
from datetime import datetime
from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    price_jpy: int
    max_accounts: int
    max_posts_month: int | None
    can_automate: bool

    model_config = {"from_attributes": True}


class SubscribeRequest(BaseModel):
    plan_name: str
    payment_method_id: str


class SubscribeResponse(BaseModel):
    subscription_id: str
    status: str
    current_period_end: datetime | None
    client_secret: str | None = None


class ChangePlanRequest(BaseModel):
    new_plan_name: str


class CancelResponse(BaseModel):
    cancel_at: datetime | None
    message: str


class PaymentResponse(BaseModel):
    id: uuid.UUID
    plan_id: int
    amount_jpy: int
    currency: str
    status: str
    paid_at: datetime | None
    period_start: datetime | None
    period_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
