from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .redis_client import get_refresh_token
from .security import decode_access_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None),
):
    from backend.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not access_token:
        raise credentials_exception
    try:
        payload = decode_access_token(access_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[object, Depends(get_current_user)]


def require_role(*roles: str):
    async def checker(current_user=Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return current_user

    return checker


def require_manager():
    return require_role("manager")


def require_sb():
    return require_role("sb")


def require_director():
    return require_role("director")


def require_manager_or_director():
    return require_role("manager", "director")


def require_sb_or_director():
    return require_role("sb", "director")


def require_any():
    return require_role("manager", "sb", "director")


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
