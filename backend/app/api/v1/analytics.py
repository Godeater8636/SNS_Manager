import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.post import Post, PostAnalytics
from app.models.affiliate_link import AffiliateLink, LinkClick
from app.schemas.analytics import (
    DashboardResponse, DashboardSummary,
    TopPost, TopLink, DailyDataPoint,
)
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(
    social_account_id: uuid.UUID | None = Query(None),
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[DashboardResponse]:
    days = int(period.rstrip("d"))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Fetch posted posts in period
    post_conditions = [Post.user_id == current_user.id, Post.status == "posted"]
    if social_account_id:
        post_conditions.append(Post.social_account_id == social_account_id)
    post_conditions.append(Post.posted_at >= since)

    posts_result = await db.execute(select(Post).where(and_(*post_conditions)))
    posts = posts_result.scalars().all()

    # Aggregate analytics
    total_impressions = 0
    total_likes = 0
    total_retweets = 0
    total_link_clicks = 0
    top_posts: list[TopPost] = []

    for post in posts:
        if post.analytics:
            latest = sorted(post.analytics, key=lambda a: a.fetched_at, reverse=True)[0]
            total_impressions += latest.impressions
            total_likes += latest.likes
            total_retweets += latest.retweets
            total_link_clicks += latest.link_clicks
            top_posts.append(TopPost(
                post_id=str(post.id),
                content=post.content[:60],
                impressions=latest.impressions,
                engagement_rate=float(latest.engagement_rate or 0),
            ))

    top_posts.sort(key=lambda p: p.impressions, reverse=True)
    avg_er = sum(p.engagement_rate for p in top_posts) / len(top_posts) if top_posts else 0.0

    # Top links
    links_result = await db.execute(
        select(AffiliateLink).where(AffiliateLink.user_id == current_user.id)
        .order_by(AffiliateLink.total_clicks.desc()).limit(5)
    )
    top_links = [
        TopLink(link_id=str(l.id), name=l.name, clicks=l.total_clicks)
        for l in links_result.scalars().all()
    ]

    # Daily series
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_series: list[DailyDataPoint] = []
    for day_offset in range(days - 1, -1, -1):
        day = today - timedelta(days=day_offset)
        next_day = day + timedelta(days=1)
        day_posts = [p for p in posts if p.posted_at and day <= p.posted_at < next_day]
        day_impressions = 0
        day_link_clicks = 0
        day_likes = 0
        day_retweets = 0
        for p in day_posts:
            if p.analytics:
                a = sorted(p.analytics, key=lambda x: x.fetched_at, reverse=True)[0]
                day_impressions += a.impressions
                day_link_clicks += a.link_clicks
                day_likes += a.likes
                day_retweets += a.retweets
        daily_series.append(DailyDataPoint(
            date=day.strftime("%Y-%m-%d"),
            impressions=day_impressions,
            link_clicks=day_link_clicks,
            likes=day_likes,
            retweets=day_retweets,
        ))

    return SuccessResponse(data=DashboardResponse(
        summary=DashboardSummary(
            total_impressions=total_impressions,
            total_likes=total_likes,
            total_retweets=total_retweets,
            total_link_clicks=total_link_clicks,
            avg_engagement_rate=round(avg_er, 2),
        ),
        top_posts=top_posts[:5],
        top_links=top_links,
        daily_series=daily_series,
    ))
