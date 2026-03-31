import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("social_accounts.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    search_keyword: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False, default="*/30 * * * *")
    total_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_executed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_execute_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="tasks")
    social_account: Mapped["SocialAccount"] = relationship("SocialAccount", back_populates="tasks")
    logs: Mapped[list["TaskLog"]] = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False, index=True)
    target_x_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_tweet_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="logs")
