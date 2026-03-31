import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False)
    plan_started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    stripe_sub_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Tokyo")
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="users")
    social_accounts: Mapped[list["SocialAccount"]] = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    affiliate_links: Mapped[list["AffiliateLink"]] = relationship("AffiliateLink", back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
