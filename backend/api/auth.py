from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, get_current_user
from backend.core.redis_client import (
    delete_refresh_token,
    get_refresh_token,
    store_refresh_token,
)
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from backend.models.user import User
from backend.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserMeResponse,
)
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    settings_obj,
) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings_obj.APP_ENV == "production",
        samesite=COOKIE_SAMESITE,
        max_age=settings_obj.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings_obj.APP_ENV == "production",
        samesite=COOKIE_SAMESITE,
        max_age=settings_obj.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from backend.core.config import settings

    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token()
    await store_refresh_token(str(user.id), refresh_token)

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=datetime.now(timezone.utc))
    )
    await db.commit()

    await AuditService.log(
        db=db,
        user_id=str(user.id),
        action="LOGIN",
        entity="users",
        entity_id=str(user.id),
        new_val={"role": user.role.value},
        ip=get_client_ip(request),
    )

    _set_auth_cookies(response, access_token, f"{user.id}:{refresh_token}", settings)
    return TokenResponse(role=user.role.value, name=user.name, id=str(user.id))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenResponse:
    from backend.core.config import settings

    if not refresh_token_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    # Find the user whose refresh token this is
    # We scan all stored tokens — in production consider embedding user_id in the token
    # Here we decode from the cookie format: "user_id:token"
    if ":" not in refresh_token_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token format")

    user_id, token_value = refresh_token_cookie.split(":", 1)
    stored = await get_refresh_token(user_id)
    if not stored or stored != token_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or invalid")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access_token = create_access_token(str(user.id), user.role.value)
    new_refresh_token = create_refresh_token()
    await store_refresh_token(str(user.id), new_refresh_token)

    _set_auth_cookies(response, new_access_token, f"{user.id}:{new_refresh_token}", settings)
    return TokenResponse(role=user.role.value, name=user.name, id=str(user.id))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await delete_refresh_token(str(current_user.id))

    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="LOGOUT",
        entity="users",
        entity_id=str(current_user.id),
        ip=get_client_ip(request),
    )
    return {"detail": "Вы вышли из системы"}


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        id=str(current_user.id),
        name=current_user.name,
        role=current_user.role.value,
        phone=current_user.phone,
        is_active=current_user.is_active,
    )



@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Новый пароль должен содержать минимум 8 символов")

    new_hash = hash_password(body.new_password)
    await db.execute(
        update(User).where(User.id == current_user.id).values(password_hash=new_hash)
    )
    await db.commit()
    await delete_refresh_token(str(current_user.id))

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CHANGE_PASSWORD",
        entity="users",
        entity_id=str(current_user.id),
        ip=get_client_ip(request),
    )
    return {"detail": "Пароль успешно изменён. Пожалуйста, войдите заново."}
