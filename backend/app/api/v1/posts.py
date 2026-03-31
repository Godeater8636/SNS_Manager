import csv
import io
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.post import Post, PostAnalytics
from app.models.social_account import SocialAccount
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse,
    PostCreateResponse, CsvImportResponse,
)
from app.schemas.common import SuccessResponse, PaginatedData
from app.core.exceptions import NotFoundException, ForbiddenException, ValidationException

router = APIRouter(prefix="/posts", tags=["posts"])

ALLOWED_STATUSES = {"draft", "scheduled", "posting", "posted", "failed", "cancelled"}


def _to_response(post: Post) -> PostResponse:
    return PostResponse.model_validate(post)


@router.get("")
async def list_posts(
    status: str | None = Query(None),
    social_account_id: uuid.UUID | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[PostResponse]]:
    conditions = [Post.user_id == current_user.id, Post.parent_post_id.is_(None)]
    if status:
        conditions.append(Post.status == status)
    if social_account_id:
        conditions.append(Post.social_account_id == social_account_id)
    if from_dt:
        conditions.append(Post.scheduled_at >= from_dt)
    if to_dt:
        conditions.append(Post.scheduled_at <= to_dt)

    result = await db.execute(
        select(Post).where(and_(*conditions))
        .order_by(Post.scheduled_at.desc().nullslast(), Post.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    posts = result.scalars().all()

    count_result = await db.execute(select(Post).where(and_(*conditions)))
    total = len(count_result.scalars().all())

    return SuccessResponse(data=PaginatedData(
        items=[_to_response(p) for p in posts],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page or 1,
    ))


@router.post("", status_code=201)
async def create_post(
    body: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PostCreateResponse]:
    # Validate social account ownership
    acc_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == body.social_account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    if not acc_result.scalar_one_or_none():
        raise NotFoundException("Xアカウント")

    created_posts: list[Post] = []
    parent_id = None

    for i, item in enumerate(body.thread):
        status = "scheduled" if body.scheduled_at else "draft"
        post = Post(
            user_id=current_user.id,
            social_account_id=body.social_account_id,
            parent_post_id=parent_id,
            thread_order=i + 1,
            content=item.content,
            media_urls=item.media_urls,
            scheduled_at=body.scheduled_at,
            status=status,
        )
        db.add(post)
        await db.flush()
        await db.refresh(post)
        if i == 0:
            parent_id = post.id
        created_posts.append(post)

    return SuccessResponse(data=PostCreateResponse(posts=[_to_response(p) for p in created_posts]))


@router.get("/export-csv")
async def export_csv(
    social_account_id: uuid.UUID | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Post.user_id == current_user.id, Post.status == "posted"]
    if social_account_id:
        conditions.append(Post.social_account_id == social_account_id)
    if from_dt:
        conditions.append(Post.posted_at >= from_dt)
    if to_dt:
        conditions.append(Post.posted_at <= to_dt)

    result = await db.execute(select(Post).where(and_(*conditions)).order_by(Post.posted_at.desc()))
    posts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["post_id", "content", "scheduled_at", "posted_at", "status",
                     "impressions", "likes", "retweets", "replies", "link_clicks", "engagement_rate"])

    for post in posts:
        latest_analytics = None
        if post.analytics:
            latest_analytics = sorted(post.analytics, key=lambda a: a.fetched_at, reverse=True)[0]
        writer.writerow([
            str(post.id), post.content[:100], post.scheduled_at, post.posted_at, post.status,
            latest_analytics.impressions if latest_analytics else 0,
            latest_analytics.likes if latest_analytics else 0,
            latest_analytics.retweets if latest_analytics else 0,
            latest_analytics.replies if latest_analytics else 0,
            latest_analytics.link_clicks if latest_analytics else 0,
            latest_analytics.engagement_rate if latest_analytics else 0,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=posts_analytics.csv"},
    )


@router.post("/import-csv")
async def import_csv(
    social_account_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[CsvImportResponse]:
    acc_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    if not acc_result.scalar_one_or_none():
        raise NotFoundException("Xアカウント")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            scheduled_at = None
            if row.get("scheduled_at"):
                scheduled_at = datetime.fromisoformat(row["scheduled_at"])
            post = Post(
                user_id=current_user.id,
                social_account_id=social_account_id,
                content=row["content"],
                scheduled_at=scheduled_at,
                status="scheduled" if scheduled_at else "draft",
            )
            db.add(post)
            created += 1
        except Exception as e:
            errors.append({"row": row_num, "message": str(e)})

    await db.flush()
    return SuccessResponse(data=CsvImportResponse(created=created, failed=len(errors), errors=errors))


@router.get("/{post_id}")
async def get_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PostResponse]:
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundException("投稿")
    return SuccessResponse(data=_to_response(post))


@router.patch("/{post_id}")
async def update_post(
    post_id: uuid.UUID,
    body: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PostResponse]:
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundException("投稿")
    if post.status not in ("draft", "scheduled"):
        raise ForbiddenException("投稿済みまたは実行中の投稿は編集できません")

    if body.content is not None:
        post.content = body.content
    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
        post.status = "scheduled"
    if body.media_urls is not None:
        post.media_urls = body.media_urls

    return SuccessResponse(data=_to_response(post))


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundException("投稿")

    if post.status == "posted":
        post.status = "cancelled"
    else:
        await db.delete(post)
