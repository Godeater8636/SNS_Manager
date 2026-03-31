import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, SmallInteger, func, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("user_id", "x_username", name="uq_social_accounts_user_username"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="x")
    x_username: Mapped[str] = mapped_column(String(50), nullable=False)
    x_display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Twikit credentials (AES-256-GCM encrypted)
    encrypted_password: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_cookies: Mapped[str | None] = mapped_column(String, nullable=True)
    encryption_key_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # BAN avoidance parameters
    daily_like_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    daily_follow_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    action_min_interval_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    action_max_interval_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    active_hours_start: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=7)
    active_hours_end: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=23)
    burst_size: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    burst_rest_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    session_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    daily_likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_follows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_reset_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="social_accounts")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="social_account")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="social_account")
