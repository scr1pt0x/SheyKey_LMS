"""Назначение ответственного менеджера на сделку и клиента."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.client import Client
from backend.models.deal import Deal
from backend.models.user import User, UserRole


async def resolve_responsible_manager_id(
    db: AsyncSession,
    current_user: User,
    optional_id: uuid.UUID | None,
) -> uuid.UUID:
    if current_user.role == UserRole.manager:
        return current_user.id

    if optional_id is not None:
        manager = await db.get(User, optional_id)
        if (
            not manager
            or manager.role != UserRole.manager
            or not manager.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите активного менеджера",
            )
        return manager.id

    return current_user.id


async def assign_deal_portfolio(
    _db: AsyncSession,
    deal: Deal,
    client: Client,
    responsible_id: uuid.UUID,
) -> None:
    deal.manager_id = responsible_id
    client.manager_id = responsible_id


async def user_is_manager(db: AsyncSession, user_id: uuid.UUID) -> bool:
    user = await db.get(User, user_id)
    return user is not None and user.role == UserRole.manager
