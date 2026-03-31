import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    amount_jpy: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="JPY")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="payments")
    plan: Mapped["Plan"] = relationship("Plan")
