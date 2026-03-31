import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.plan import Plan
from app.schemas.social_account import (
    SocialAccountCreate, SocialAccountUpdate,
    SocialAccountResponse, SessionRefreshResponse,
)
from app.schemas.common import SuccessResponse, PaginatedData
from app.core.security import encrypt
from app.core.exceptions import NotFoundException, PlanLimitException, ConflictException
from app.config import settings

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


def _to_response(acc: SocialAccount) -> SocialAccountResponse:
    return SocialAccountResponse.model_validate(acc)


@router.get("")
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[SocialAccountResponse]]:
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id)
    )
    accounts = result.scalars().all()
    items = [_to_response(a) for a in accounts]
    return SuccessResponse(data=PaginatedData(items=items, total=len(items), page=1, per_page=len(items) or 1, pages=1))


@router.post("", status_code=201)
async def create_account(
    body: SocialAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[SocialAccountResponse]:
    # Plan limit check
    plan_result = await db.execute(select(Plan).where(Plan.id == current_user.plan_id))
    plan = plan_result.scalar_one_or_none()
    existing_count_result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id, SocialAccount.is_active.is_(True))
    )
    existing_count = len(existing_count_result.scalars().all())
    if plan and existing_count >= plan.max_accounts:
        raise PlanLimitException(f"現在のプランではXアカウントを最大{plan.max_accounts}件まで登録できます")

    # Check duplicate
    dup = await db.execute(
        select(SocialAccount).where(
            SocialAccount.user_id == current_user.id,
            SocialAccount.x_username == body.x_username,
        )
    )
    if dup.scalar_one_or_none():
        raise ConflictException("このXアカウントは既に登録されています")

    # Twikit login attempt to validate credentials
    # (performed as background task in production; here we store immediately)
    enc_password = encrypt(body.password)
    # cookies will be populated by worker after actual Twikit login
    account = SocialAccount(
        user_id=current_user.id,
        x_username=body.x_username,
        encrypted_password=enc_password,
        encrypted_cookies=None,
        encryption_key_id=settings.AES_KEY_ID,
        daily_like_limit=body.daily_like_limit,
        daily_follow_limit=body.daily_follow_limit,
        action_min_interval_sec=body.action_min_interval_sec,
        action_max_interval_sec=body.action_max_interval_sec,
        active_hours_start=body.active_hours_start,
        active_hours_end=body.active_hours_end,
        burst_size=body.burst_size,
        burst_rest_sec=body.burst_rest_sec,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    # Queue Twikit login task
    from app.worker.post_tasks import twikit_login_task
    twikit_login_task.delay(str(account.id))

    return SuccessResponse(data=_to_response(account))


@router.get("/{account_id}")
async def get_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[SocialAccountResponse]:
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundException("Xアカウント")
    return SuccessResponse(data=_to_response(account))


@router.patch("/{account_id}")
async def update_account(
    account_id: uuid.UUID,
    body: SocialAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[SocialAccountResponse]:
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundException("Xアカウント")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)

    return SuccessResponse(data=_to_response(account))


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundException("Xアカウント")
    await db.delete(account)


@router.post("/{account_id}/refresh-session")
async def refresh_session(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[SessionRefreshResponse]:
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundException("Xアカウント")

    # Queue re-login task
    from app.worker.post_tasks import twikit_login_task
    twikit_login_task.delay(str(account.id))

    new_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    return SuccessResponse(data=SessionRefreshResponse(session_expires_at=new_expiry))
