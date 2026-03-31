import pyotp
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.schemas.user import UserResponse, UserUpdateRequest, PlanInfo, TotpSetupResponse, TotpVerifyRequest
from app.schemas.common import SuccessResponse
from app.core.security import encrypt, decrypt
from app.core.exceptions import ValidationException
from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])


def _build_user_response(user: User, plan: Plan | None) -> UserResponse:
    plan_info = None
    if plan:
        plan_info = PlanInfo(
            name=plan.name,
            display_name=plan.display_name,
            price_jpy=plan.price_jpy,
            max_accounts=plan.max_accounts,
            max_posts_month=plan.max_posts_month,
            can_automate=plan.can_automate,
            expires_at=user.plan_expires_at,
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=user.timezone,
        is_active=user.is_active,
        plan=plan_info,
        created_at=user.created_at,
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    plan_result = await db.execute(select(Plan).where(Plan.id == current_user.plan_id))
    plan = plan_result.scalar_one_or_none()
    return SuccessResponse(data=_build_user_response(current_user, plan))


@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.timezone is not None:
        current_user.timezone = body.timezone

    plan_result = await db.execute(select(Plan).where(Plan.id == current_user.plan_id))
    plan = plan_result.scalar_one_or_none()
    return SuccessResponse(data=_build_user_response(current_user, plan))


@router.post("/me/totp/enable")
async def totp_enable(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[TotpSetupResponse]:
    secret = pyotp.random_base32()
    # Store encrypted temporarily (user must verify before we save permanently)
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(name=current_user.email, issuer_name=settings.APP_NAME)
    # Return plaintext secret for QR display — user calls /verify to activate
    return SuccessResponse(data=TotpSetupResponse(secret=secret, qr_url=qr_url))


@router.post("/me/totp/verify")
async def totp_verify(
    body: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    # Expect secret to be passed back after /enable
    # In production, store pending secret in Redis. Simplified here.
    raise ValidationException("2FA有効化フローを完成させてください（Redis連携が必要）")


@router.delete("/me/totp")
async def totp_disable(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    current_user.totp_secret = None
    return SuccessResponse(data={"message": "2FAを無効化しました"})
