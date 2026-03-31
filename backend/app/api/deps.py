import uuid
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedException("無効なトークンです")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException("トークンが無効または期限切れです")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("ユーザーが存在しません")
    if not user.is_active:
        raise ForbiddenException("アカウントが無効です")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise ForbiddenException("管理者権限が必要です")
    return user


def require_plan_automate(user: User = Depends(get_current_user)) -> User:
    if not user.plan or not user.plan.can_automate:
        raise ForbiddenException("自動化機能はPro以上のプランで利用できます")
    return user
