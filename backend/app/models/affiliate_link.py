import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, func, text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    destination_url: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    redirect_on_expire: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="affiliate_links")
    clicks: Mapped[list["LinkClick"]] = relationship("LinkClick", back_populates="affiliate_link", cascade="all, delete-orphan")


class LinkClick(Base):
    __tablename__ = "link_clicks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    affiliate_link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliate_links.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True)
    clicked_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referer: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    affiliate_link: Mapped["AffiliateLink"] = relationship("AffiliateLink", back_populates="clicks")
