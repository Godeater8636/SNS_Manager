import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, ForeignKey, SmallInteger, Text, Numeric, func, text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    social_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("social_accounts.id"), nullable=False, index=True)
    parent_post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)
    thread_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    x_tweet_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="posts")
    social_account: Mapped["SocialAccount"] = relationship("SocialAccount", back_populates="posts")
    thread_children: Mapped[list["Post"]] = relationship("Post", foreign_keys=[parent_post_id])
    analytics: Mapped[list["PostAnalytics"]] = relationship("PostAnalytics", back_populates="post", cascade="all, delete-orphan")


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False, index=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retweets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmarks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    link_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    post: Mapped["Post"] = relationship("Post", back_populates="analytics")
