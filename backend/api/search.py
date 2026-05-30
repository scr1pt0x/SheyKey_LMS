"""Global search for clients and deals."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.client import Client
from backend.models.deal import Deal
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.user import User, UserRole

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    like = f"%{q}%"
    clients: list[dict] = []
    deals: list[dict] = []

    if current_user.role == UserRole.manager:
        mid = current_user.id
        client_rows = await db.execute(
            select(Client)
            .where(Client.manager_id == mid)
            .where(
                or_(
                    Client.full_name.ilike(like),
                    Client.phone.ilike(like),
                    Client.passport.ilike(like),
                )
            )
            .limit(limit)
        )
        for c in client_rows.scalars().all():
            clients.append({"id": str(c.id), "full_name": c.full_name, "phone": c.phone})

        deal_rows = await db.execute(
            select(Deal)
            .where(Deal.manager_id == mid)
            .join(Client, Deal.client_id == Client.id)
            .where(
                or_(
                    Client.full_name.ilike(like),
                    Client.phone.ilike(like),
                )
            )
            .limit(limit)
        )
        for d in deal_rows.scalars().all():
            deals.append(
                {
                    "id": str(d.id),
                    "client_id": str(d.client_id),
                    "type": d.type.value,
                    "status": d.status.value,
                    "total": float(d.total),
                }
            )

    elif current_user.role == UserRole.sb:
        open_case_deal_ids = (
            await db.execute(
                select(OverdueCase.deal_id)
                .where(OverdueCase.status != OverdueCaseStatus.closed)
                .distinct()
            )
        ).scalars().all()

        client_rows = await db.execute(
            select(Client)
            .where(
                or_(
                    Client.full_name.ilike(like),
                    Client.phone.ilike(like),
                    Client.passport.ilike(like),
                )
            )
            .limit(limit)
        )
        for c in client_rows.scalars().all():
            clients.append({"id": str(c.id), "full_name": c.full_name, "phone": c.phone})

        if open_case_deal_ids:
            deal_rows = await db.execute(
                select(Deal)
                .where(Deal.id.in_(open_case_deal_ids))
                .join(Client, Deal.client_id == Client.id)
                .where(
                    or_(
                        Client.full_name.ilike(like),
                        Client.phone.ilike(like),
                    )
                )
                .limit(limit)
            )
            for d in deal_rows.scalars().all():
                deals.append(
                    {
                        "id": str(d.id),
                        "client_id": str(d.client_id),
                        "type": d.type.value,
                        "status": d.status.value,
                        "total": float(d.total),
                    }
                )

    else:
        client_rows = await db.execute(
            select(Client)
            .where(
                or_(
                    Client.full_name.ilike(like),
                    Client.phone.ilike(like),
                    Client.passport.ilike(like),
                )
            )
            .limit(limit)
        )
        for c in client_rows.scalars().all():
            clients.append({"id": str(c.id), "full_name": c.full_name, "phone": c.phone})

        deal_rows = await db.execute(
            select(Deal)
            .join(Client, Deal.client_id == Client.id)
            .where(
                or_(
                    Client.full_name.ilike(like),
                    Client.phone.ilike(like),
                )
            )
            .limit(limit)
        )
        for d in deal_rows.scalars().all():
            deals.append(
                {
                    "id": str(d.id),
                    "client_id": str(d.client_id),
                    "type": d.type.value,
                    "status": d.status.value,
                    "total": float(d.total),
                }
            )

    return {"clients": clients, "deals": deals, "query": q}
