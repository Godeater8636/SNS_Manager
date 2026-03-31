from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_jpy: Mapped[int] = mapped_column(Integer, nullable=False)
    max_accounts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_posts_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    can_automate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="plan")
