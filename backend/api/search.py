"""Global search for clients and deals."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.access import load_client_for_user
from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.user import User
from backend.schemas.search import ClientSearchProfile, GlobalSearchResponse
from backend.services.search_service import (
    build_client_profile,
    hits_to_legacy_clients_deals,
    search_clients,
)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> GlobalSearchResponse:
    hits = await search_clients(db, current_user, q, limit)
    clients, deals = hits_to_legacy_clients_deals(hits)
    return GlobalSearchResponse(clients=clients, deals=deals, hits=hits, query=q)


@router.get("/client/{client_id}", response_model=ClientSearchProfile)
async def client_search_profile(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> ClientSearchProfile:
    client = await load_client_for_user(db, client_id, current_user)
    overdue_cases, deals = await build_client_profile(db, client)
    portfolio_manager = await db.get(User, client.manager_id)
    return ClientSearchProfile(
        id=client.id,
        full_name=client.full_name,
        phone=client.phone,
        manager_id=client.manager_id,
        manager_name=portfolio_manager.name if portfolio_manager else "—",
        overdue_cases=overdue_cases,
        deals=deals,
    )
