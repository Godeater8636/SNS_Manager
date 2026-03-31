import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.affiliate_link import AffiliateLink, LinkClick
from app.schemas.affiliate_link import (
    AffiliateLinkCreate, AffiliateLinkUpdate,
    AffiliateLinkResponse, AffiliateLinkDetailResponse,
    LinkStats, DailyStat,
)
from app.schemas.common import SuccessResponse, PaginatedData
from app.core.security import generate_slug
from app.core.exceptions import NotFoundException, ConflictException
from app.config import settings

router = APIRouter(tags=["affiliate-links"])


def _to_response(link: AffiliateLink) -> AffiliateLinkResponse:
    return AffiliateLinkResponse(
        id=link.id,
        name=link.name,
        destination_url=link.destination_url,
        short_url=f"{settings.APP_BASE_URL}/l/{link.slug}",
        slug=link.slug,
        tags=link.tags or [],
        description=link.description,
        total_clicks=link.total_clicks,
        expires_at=link.expires_at,
        is_active=link.is_active,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get("/affiliate-links")
async def list_links(
    tags: list[str] | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[AffiliateLinkResponse]]:
    conditions = [AffiliateLink.user_id == current_user.id]
    if search:
        conditions.append(AffiliateLink.name.ilike(f"%{search}%"))
    if tags:
        conditions.append(AffiliateLink.tags.overlap(tags))

    result = await db.execute(
        select(AffiliateLink).where(and_(*conditions))
        .order_by(AffiliateLink.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    links = result.scalars().all()
    count_result = await db.execute(select(AffiliateLink).where(and_(*conditions)))
    total = len(count_result.scalars().all())

    return SuccessResponse(data=PaginatedData(
        items=[_to_response(l) for l in links],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page or 1,
    ))


@router.post("/affiliate-links", status_code=201)
async def create_link(
    body: AffiliateLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AffiliateLinkResponse]:
    # Generate unique slug
    for _ in range(5):
        slug = generate_slug(8)
        existing = await db.execute(select(AffiliateLink).where(AffiliateLink.slug == slug))
        if not existing.scalar_one_or_none():
            break
    else:
        raise ConflictException("スラッグの生成に失敗しました。再試行してください")

    link = AffiliateLink(
        user_id=current_user.id,
        name=body.name,
        destination_url=body.destination_url,
        slug=slug,
        tags=body.tags,
        description=body.description,
        expires_at=body.expires_at,
        redirect_on_expire=body.redirect_on_expire,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return SuccessResponse(data=_to_response(link))


@router.get("/affiliate-links/{link_id}")
async def get_link(
    link_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AffiliateLinkDetailResponse]:
    result = await db.execute(
        select(AffiliateLink).where(
            AffiliateLink.id == link_id,
            AffiliateLink.user_id == current_user.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundException("アフィリエイトリンク")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    def _count_clicks(since: datetime) -> int:
        return sum(1 for c in link.clicks if c.clicked_at >= since)

    daily_series: list[DailyStat] = []
    for days_ago in range(29, -1, -1):
        day = today_start - timedelta(days=days_ago)
        next_day = day + timedelta(days=1)
        count = sum(1 for c in link.clicks if day <= c.clicked_at < next_day)
        daily_series.append(DailyStat(date=day.strftime("%Y-%m-%d"), clicks=count))

    stats = LinkStats(
        total_clicks=link.total_clicks,
        clicks_today=_count_clicks(today_start),
        clicks_this_week=_count_clicks(week_start),
        clicks_this_month=_count_clicks(month_start),
        daily_series=daily_series,
    )
    return SuccessResponse(data=AffiliateLinkDetailResponse(link=_to_response(link), stats=stats))


@router.patch("/affiliate-links/{link_id}")
async def update_link(
    link_id: uuid.UUID,
    body: AffiliateLinkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AffiliateLinkResponse]:
    result = await db.execute(
        select(AffiliateLink).where(
            AffiliateLink.id == link_id,
            AffiliateLink.user_id == current_user.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundException("アフィリエイトリンク")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(link, field, value)

    return SuccessResponse(data=_to_response(link))


@router.delete("/affiliate-links/{link_id}", status_code=204)
async def delete_link(
    link_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AffiliateLink).where(
            AffiliateLink.id == link_id,
            AffiliateLink.user_id == current_user.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundException("アフィリエイトリンク")
    await db.delete(link)


@router.get("/l/{slug}")
async def redirect_link(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public short URL redirect endpoint."""
    result = await db.execute(select(AffiliateLink).where(AffiliateLink.slug == slug))
    link = result.scalar_one_or_none()
    if not link or not link.is_active:
        return RedirectResponse(url="/404", status_code=302)

    now = datetime.now(timezone.utc)
    if link.expires_at and now > link.expires_at:
        dest = link.redirect_on_expire or "/expired"
        return RedirectResponse(url=dest, status_code=302)

    # Record click
    ip = request.client.host if request.client else None
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    ua = request.headers.get("user-agent", "")
    ua_hash = hashlib.sha256(ua.encode()).hexdigest() if ua else None

    click = LinkClick(
        affiliate_link_id=link.id,
        ip_hash=ip_hash,
        user_agent_hash=ua_hash,
        referer=request.headers.get("referer"),
    )
    db.add(click)
    link.total_clicks += 1
    await db.flush()

    return RedirectResponse(url=link.destination_url, status_code=302)
