import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.access import list_manager_filter, load_client_for_user
from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, get_current_user, require_role
from backend.models.client import Client, KycStatus
from backend.models.notification import NotificationLog
from backend.models.user import User, UserRole
from backend.schemas.client import (
    ClientCreate,
    ClientListItem,
    ClientResponse,
    ClientUpdate,
    KycUpdate,
    NoteAddRequest,
)
from backend.schemas.common import PaginatedResponse
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=PaginatedResponse[ClientListItem])
async def list_clients(
    q: str | None = Query(None, description="Search by name, phone or passport"),
    kyc_status: KycStatus | None = None,
    manager_id: uuid.UUID | None = None,
    scope: Literal["portfolio", "all"] = Query(
        "portfolio",
        description="portfolio — только свои клиенты (менеджер); all — все для оформления сделки",
    ),
    is_archived: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[ClientListItem]:
    query = select(Client)

    if q:
        like = f"%{q}%"
        query = query.where(
            or_(
                Client.full_name.ilike(like),
                Client.phone.ilike(like),
                Client.passport.ilike(like),
            )
        )
    if kyc_status:
        query = query.where(Client.kyc_status == kyc_status)
    if current_user.role == UserRole.manager:
        if scope == "portfolio":
            query = query.where(Client.manager_id == current_user.id)
    else:
        effective_manager_id = list_manager_filter(current_user, manager_id)
        if effective_manager_id:
            query = query.where(Client.manager_id == effective_manager_id)

    query = query.where(Client.is_archived == is_archived)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.order_by(Client.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    clients = result.scalars().all()

    return PaginatedResponse(
        items=[ClientListItem.model_validate(c) for c in clients],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> ClientResponse:
    client = Client(
        manager_id=current_user.id,
        full_name=body.full_name,
        phone=body.phone,
        passport=body.passport,
        address=body.address,
        notes=body.notes,
        tags=body.tags or [],
    )
    db.add(client)
    await db.flush()

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CREATE",
        entity="clients",
        entity_id=str(client.id),
        new_val={"full_name": client.full_name, "phone": client.phone},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(client)
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> ClientResponse:
    client = await load_client_for_user(db, client_id, current_user)
    manager = await db.get(User, client.manager_id)
    resp = ClientResponse.model_validate(client)
    return resp.model_copy(
        update={"manager_name": manager.name if manager else None}
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> ClientResponse:
    client = await load_client_for_user(db, client_id, current_user)

    old_val = {
        "full_name": client.full_name,
        "phone": client.phone,
        "passport": client.passport,
        "address": client.address,
    }

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="UPDATE",
        entity="clients",
        entity_id=str(client.id),
        old_val=old_val,
        new_val=update_data,
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(client)
    return ClientResponse.model_validate(client)


@router.post("/{client_id}/archive", response_model=ClientResponse)
async def archive_client(
    client_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> ClientResponse:
    client = await load_client_for_user(db, client_id, current_user)

    client.is_archived = True
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="ARCHIVE",
        entity="clients",
        entity_id=str(client.id),
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(client)
    return ClientResponse.model_validate(client)


@router.patch("/{client_id}/kyc", response_model=ClientResponse)
async def update_kyc(
    client_id: uuid.UUID,
    body: KycUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> ClientResponse:
    client = await load_client_for_user(db, client_id, current_user)

    old_status = client.kyc_status
    client.kyc_status = body.kyc_status

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="KYC_UPDATE",
        entity="clients",
        entity_id=str(client.id),
        old_val={"kyc_status": old_status.value},
        new_val={"kyc_status": body.kyc_status.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(client)
    return ClientResponse.model_validate(client)


@router.post("/{client_id}/notes")
async def add_note(
    client_id: uuid.UUID,
    body: NoteAddRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> dict:
    client = await load_client_for_user(db, client_id, current_user)

    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    separator = "\n\n" if client.notes else ""
    client.notes = f"{client.notes or ''}{separator}[{timestamp}] {body.note}"

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="ADD_NOTE",
        entity="clients",
        entity_id=str(client.id),
        new_val={"note": body.note},
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Заметка добавлена"}


@router.get("/{client_id}/notifications")
async def get_client_notifications(
    client_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse:
    from backend.schemas.notification import NotificationLogResponse

    await load_client_for_user(db, client_id, current_user)

    total_q = await db.execute(
        select(func.count()).where(NotificationLog.client_id == client_id)
    )
    total = total_q.scalar_one()

    rows = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.client_id == client_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = rows.scalars().all()
    return PaginatedResponse(
        items=[NotificationLogResponse.model_validate(n) for n in items],
        total=total,
        limit=limit,
        offset=offset,
    )
