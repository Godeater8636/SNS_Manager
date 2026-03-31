from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.plan import Plan
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RegisterResponse, PasswordResetRequest, PasswordResetConfirm,
)
from app.schemas.common import SuccessResponse
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.exceptions import ConflictException, UnauthorizedException, ValidationException
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# NOTE: In production, OTP tokens should be stored in Redis with TTL.
# For simplicity, an in-memory dict is used here (NOT production-safe).
_otp_store: dict[str, tuple[str, datetime]] = {}


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RegisterResponse]:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ConflictException("このメールアドレスは既に登録されています")

    # Use starter plan as default
    plan_result = await db.execute(select(Plan).where(Plan.name == "starter"))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise ValidationException("プランが設定されていません。初期データを投入してください")

    trial_end = datetime.now(timezone.utc) + timedelta(days=14)
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        plan_id=plan.id,
        trial_ends_at=trial_end,
        plan_expires_at=trial_end,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="strict",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return SuccessResponse(data=RegisterResponse(
        user_id=str(user.id),
        email=user.email,
        access_token=access_token,
    ))


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise UnauthorizedException("メールアドレスまたはパスワードが正しくありません")

    if not user.is_active:
        raise UnauthorizedException("このアカウントは無効です")

    # TOTP check
    if user.totp_secret:
        if not body.totp_code:
            raise ValidationException("2段階認証コードを入力してください")
        import pyotp
        from app.core.security import decrypt
        secret = decrypt(user.totp_secret)
        totp = pyotp.TOTP(secret)
        if not totp.verify(body.totp_code):
            raise UnauthorizedException("2段階認証コードが正しくありません")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="strict",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return SuccessResponse(data=TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/refresh")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    token = request.cookies.get("refresh_token")
    if not token:
        raise UnauthorizedException("リフレッシュトークンが見つかりません")

    from jose import JWTError
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException()
        user_id = payload.get("sub")
    except JWTError:
        raise UnauthorizedException("リフレッシュトークンが無効です")

    import uuid
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException()

    access_token = create_access_token(str(user.id))
    return SuccessResponse(data=TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("refresh_token")


@router.post("/password-reset/request")
async def password_reset_request(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import generate_otp
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        otp = generate_otp(6)
        _otp_store[body.email] = (otp, datetime.now(timezone.utc) + timedelta(minutes=30))
        # TODO: send email via SendGrid
    # Always return success (don't reveal existence)
    return SuccessResponse(data={"message": "メールを確認してください"})


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    # NOTE: token here is email:otp format in this simplified implementation
    try:
        email, otp = body.token.split(":", 1)
    except ValueError:
        raise ValidationException("トークンの形式が無効です")

    entry = _otp_store.get(email)
    if not entry or entry[0] != otp or datetime.now(timezone.utc) > entry[1]:
        raise ValidationException("トークンが無効または期限切れです")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise ValidationException("ユーザーが見つかりません")

    user.password_hash = hash_password(body.new_password)
    _otp_store.pop(email, None)
    return SuccessResponse(data={"message": "パスワードを変更しました"})
