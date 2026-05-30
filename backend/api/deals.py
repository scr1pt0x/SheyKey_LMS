import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.access import (
    CLIENT_NOT_IN_PORTFOLIO,
    list_manager_filter,
    require_deal_access,
)
from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, get_current_user, require_role
from backend.models.client import Client
from backend.models.deal import Deal, DealParam, DealStatus, DealType
from backend.models.payment import PaymentSchedule
from backend.models.restructuring import Restructuring
from backend.schemas.sb import RestructuringResponse
from backend.models.user import User, UserRole
from backend.schemas.common import PaginatedResponse
from backend.schemas.deal import (
    ApproveRequest,
    DealCreate,
    DealListItem,
    DealResponse,
    DealUpdate,
    RejectRequest,
    RestructureRequest,
    ScheduleItemResponse,
)
from backend.services.audit_service import AuditService
from backend.services.payment_calculator import generate_schedule
from backend.services.push_service import notify_staff

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _deal_params_to_dict(deal: Deal) -> dict:
    return {p.key: p.value for p in deal.params}


async def _create_schedules(
    db: AsyncSession, deal: Deal, schedule_items
) -> None:
    for item in schedule_items:
        schedule = PaymentSchedule(
            deal_id=deal.id,
            installment_number=item.installment_number,
            due_date=item.due_date,
            amount=item.amount,
            installment_type=item.installment_type,
        )
        db.add(schedule)


@router.get("", response_model=PaginatedResponse[DealListItem])
async def list_deals(
    status_filter: DealStatus | None = Query(None, alias="status"),
    type_filter: DealType | None = Query(None, alias="type"),
    manager_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[DealListItem]:
    query = select(Deal)

    if status_filter:
        query = query.where(Deal.status == status_filter)
    if type_filter:
        query = query.where(Deal.type == type_filter)
    effective_manager_id = list_manager_filter(current_user, manager_id)
    if effective_manager_id:
        query = query.where(Deal.manager_id == effective_manager_id)
    if client_id:
        query = query.where(Deal.client_id == client_id)
    if date_from:
        query = query.where(Deal.start_date >= date_from)
    if date_to:
        query = query.where(Deal.start_date <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(query.order_by(Deal.created_at.desc()).limit(limit).offset(offset))
    deals = rows.scalars().all()

    return PaginatedResponse(
        items=[DealListItem.model_validate(d) for d in deals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    body: DealCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> DealResponse:
    from decimal import Decimal

    client = await db.get(Client, body.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    if current_user.role == UserRole.manager and client.manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CLIENT_NOT_IN_PORTFOLIO,
        )

    if body.type == DealType.murabaha and body.murabaha:
        p = body.murabaha
        principal = p.principal
        markup = p.markup
        total = principal + markup
        duration_months = p.duration_months
        start_date = p.start_date
        params_data = {
            "principal": str(principal),
            "markup": str(markup),
            "duration_months": duration_months,
        }
    elif body.type == DealType.ijara and body.ijara:
        p = body.ijara
        principal = p.monthly_rent * p.duration_months
        markup = Decimal("0")
        total = principal + (p.buyout_amount or Decimal("0"))
        duration_months = p.duration_months
        start_date = p.start_date
        params_data = {
            "monthly_rent": str(p.monthly_rent),
            "duration_months": duration_months,
            "buyout_amount": str(p.buyout_amount) if p.buyout_amount else None,
        }
    else:
        raise HTTPException(status_code=400, detail="Missing deal parameters")

    deal = Deal(
        client_id=body.client_id,
        manager_id=current_user.id,
        type=body.type,
        status=DealStatus.draft,
        principal=principal,
        markup=markup,
        total=total,
        duration_months=duration_months,
        start_date=start_date,
        end_date=start_date.replace(year=start_date.year + (start_date.month + duration_months - 1) // 12,
                                    month=(start_date.month + duration_months - 1) % 12 + 1)
        if start_date else None,
    )
    db.add(deal)
    await db.flush()

    for key, value in params_data.items():
        if value is not None:
            db.add(DealParam(deal_id=deal.id, key=key, value=value))

    schedule_items = generate_schedule(body.type.value, params_data, start_date)
    await _create_schedules(db, deal, schedule_items)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CREATE",
        entity="deals",
        entity_id=str(deal.id),
        new_val={"type": body.type.value, "total": str(total), "client_id": str(body.client_id)},
        ip=get_client_ip(request),
    )
    await db.commit()

    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.payment_schedules))
    )
    deal = result.scalar_one()
    return _build_deal_response(deal)


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> DealResponse:
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.payment_schedules), selectinload(Deal.params))
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, current_user)
    return _build_deal_response(deal)


@router.patch("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: uuid.UUID,
    body: DealUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> DealResponse:
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.payment_schedules), selectinload(Deal.params))
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, current_user)
    if deal.status not in (DealStatus.draft, DealStatus.pending):
        raise HTTPException(
            status_code=400,
            detail="Редактирование сделки возможно только до её одобрения",
        )

    if body.murabaha and deal.type == DealType.murabaha:
        p = body.murabaha
        deal.principal = p.principal
        deal.markup = p.markup
        deal.total = p.principal + p.markup
        deal.duration_months = p.duration_months
        deal.start_date = p.start_date
        params_data = {
            "principal": str(p.principal),
            "markup": str(p.markup),
            "duration_months": p.duration_months,
        }
        for param in deal.params:
            if param.key in params_data:
                param.value = params_data[param.key]
        for ps in deal.payment_schedules:
            await db.delete(ps)
        await db.flush()
        schedule_items = generate_schedule(deal.type.value, params_data, p.start_date)
        await _create_schedules(db, deal, schedule_items)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="UPDATE",
        entity="deals",
        entity_id=str(deal.id),
        ip=get_client_ip(request),
    )
    await db.commit()

    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(selectinload(Deal.payment_schedules))
    )
    deal = result.scalar_one()
    return _build_deal_response(deal)


@router.post("/{deal_id}/submit", response_model=DealResponse)
async def submit_deal(
    deal_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> DealResponse:
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id).options(selectinload(Deal.payment_schedules))
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, current_user)
    if deal.status != DealStatus.draft:
        raise HTTPException(status_code=400, detail="Только черновик можно отправить на согласование")

    deal.status = DealStatus.pending
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="STATUS_CHANGE",
        entity="deals",
        entity_id=str(deal.id),
        old_val={"status": "draft"},
        new_val={"status": "pending"},
        ip=get_client_ip(request),
    )
    # Notify all directors about the new deal pending approval
    directors = (
        await db.execute(
            select(User).where(User.role == UserRole.director).where(User.is_active == True)  # noqa
        )
    ).scalars().all()
    for director in directors:
        await notify_staff(
            db=db,
            user_id=director.id,
            title="Новая сделка на согласовании",
            body=f"Сделка на {deal.total} ₽ ожидает вашего решения.",
            entity_type="deals",
            entity_id=str(deal.id),
            action_url=f"/director/approval",
        )
    await db.commit()
    await db.refresh(deal)
    return _build_deal_response(deal)


@router.get("/{deal_id}/restructurings", response_model=list[RestructuringResponse])
async def list_deal_restructurings(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> list[RestructuringResponse]:
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, current_user)

    rows = await db.execute(
        select(Restructuring)
        .where(Restructuring.deal_id == deal_id)
        .order_by(Restructuring.created_at.desc())
    )
    return [RestructuringResponse.model_validate(r) for r in rows.scalars().all()]


@router.post("/{deal_id}/restructure")
async def request_restructure(
    deal_id: uuid.UUID,
    body: RestructureRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    require_deal_access(deal, current_user)
    if deal.status not in (DealStatus.active, DealStatus.overdue):
        raise HTTPException(
            status_code=400,
            detail="Реструктуризация возможна только для активных или просроченных сделок",
        )

    restructuring = Restructuring(
        deal_id=deal.id,
        initiated_by=current_user.id,
        reason=body.reason,
        new_schedule=body.new_schedule,
    )
    db.add(restructuring)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="RESTRUCTURE_REQUEST",
        entity="restructurings",
        entity_id=str(restructuring.id) if restructuring.id else None,
        new_val={"deal_id": str(deal_id), "reason": body.reason},
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Запрос на реструктуризацию отправлен"}


def _build_deal_response(deal: Deal) -> DealResponse:
    schedules = [
        ScheduleItemResponse.model_validate(ps)
        for ps in sorted(deal.payment_schedules, key=lambda x: x.installment_number)
    ]
    return DealResponse(
        id=deal.id,
        client_id=deal.client_id,
        manager_id=deal.manager_id,
        type=deal.type,
        status=deal.status,
        principal=deal.principal,
        markup=deal.markup,
        total=deal.total,
        duration_months=deal.duration_months,
        start_date=deal.start_date,
        end_date=deal.end_date,
        approved_by=deal.approved_by,
        approved_at=deal.approved_at,
        rejection_comment=deal.rejection_comment,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        payment_schedules=schedules,
    )
