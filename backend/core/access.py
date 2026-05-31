"""Access control helpers for manager portfolio isolation."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.client import Client
from backend.models.deal import Deal
from backend.models.overdue import OverdueCase
from backend.models.payment import Payment
from backend.models.user import User, UserRole
from backend.services.search_service import client_has_open_sb_case

MANAGER_FORBIDDEN_DETAIL = "Нет доступа к этому ресурсу"
CLIENT_NOT_IN_PORTFOLIO = "Клиент не в вашем портфеле"


def list_manager_filter(
    user: User, manager_id_param: uuid.UUID | None
) -> uuid.UUID | None:
    """
    Effective manager_id for list queries.
    manager: always own id; director: optional filter; sb: no filter.
    """
    if user.role == UserRole.manager:
        return user.id
    if user.role == UserRole.director:
        return manager_id_param
    return None


def require_client_access(client: Client, user: User) -> None:
    if user.role == UserRole.manager and client.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MANAGER_FORBIDDEN_DETAIL,
        )


def require_deal_access(deal: Deal, user: User) -> None:
    if user.role == UserRole.manager and deal.manager_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MANAGER_FORBIDDEN_DETAIL,
        )


async def require_sb_case_on_deal(
    db: AsyncSession, deal_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(OverdueCase.id).where(
            OverdueCase.deal_id == deal_id,
            OverdueCase.sb_user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Дело по этой сделке не назначено вам",
        )


async def load_deal_for_user(
    db: AsyncSession, deal_id: uuid.UUID, user: User
) -> Deal:
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, user)
    if user.role == UserRole.sb:
        await require_sb_case_on_deal(db, deal_id, user.id)
    return deal


async def load_client_for_user(
    db: AsyncSession, client_id: uuid.UUID, user: User
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    require_client_access(client, user)
    if user.role == UserRole.sb:
        if not await client_has_open_sb_case(db, client_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Клиент не передан в Службу Безопасности",
            )
    return client


async def check_document_entity_access(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    user: User,
) -> None:
    if user.role != UserRole.manager:
        return
    if entity_type == "client":
        await load_client_for_user(db, entity_id, user)
    elif entity_type == "deal":
        await load_deal_for_user(db, entity_id, user)
    elif entity_type == "payment":
        payment = await db.get(Payment, entity_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Платёж не найден")
        await load_deal_for_user(db, payment.deal_id, user)
