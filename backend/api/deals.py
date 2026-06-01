import uuid
from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.access import list_manager_filter, require_deal_access
from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, get_current_user, require_role
from backend.models.client import Client
from backend.models.deal import Deal, DealParam, DealStatus, DealType
from backend.models.payment import PaymentSchedule
from backend.models.user import User, UserRole
from backend.schemas.common import PaginatedResponse
from backend.schemas.deal import (
    DealCreate,
    DealListItem,
    DealResponse,
    DealUpdate,
    MurabahaQuoteResponse,
    MurabahaTariffOptionsResponse,
    ScheduleItemResponse,
)
from backend.services.audit_service import AuditService
from backend.services.deal_activation_service import activate_deal
from backend.services.deal_portfolio_service import (
    assign_deal_portfolio,
    resolve_responsible_manager_id,
)
from backend.services.deal_display import deal_purchase_summary, deal_purchase_summary_from_deal
from backend.services.payment_calculator import generate_schedule

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _deal_params_to_dict(deal: Deal) -> dict:
    return {p.key: p.value for p in deal.params}


async def _manager_names_by_id(db: AsyncSession, manager_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not manager_ids:
        return {}
    rows = await db.execute(select(User.id, User.name).where(User.id.in_(manager_ids)))
    return {row.id: row.name for row in rows.all()}


async def _client_names_by_id(db: AsyncSession, client_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not client_ids:
        return {}
    rows = await db.execute(
        select(Client.id, Client.full_name).where(Client.id.in_(client_ids))
    )
    return {row.id: row.full_name for row in rows.all()}


def _build_deal_list_item(
    deal: Deal,
    manager_name: str | None,
    client_name: str | None,
) -> DealListItem:
    params = _deal_params_to_dict(deal) if deal.params else None
    base = DealListItem.model_validate(deal)
    return base.model_copy(
        update={
            "manager_name": manager_name,
            "client_name": client_name,
            "purchase_summary": deal_purchase_summary(
                deal.type, deal.principal, deal.product_description, params
            ),
        }
    )


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
    current_user: User = Depends(require_role("manager", "director")),
) -> PaginatedResponse[DealListItem]:
    query = select(Deal)

    if status_filter:
        query = query.where(Deal.status == status_filter)
    if type_filter:
        query = query.where(Deal.type == type_filter)
    effective_manager_id = list_manager_filter(current_user, manager_id)
    if effective_manager_id and not (
        current_user.role == UserRole.manager and client_id
    ):
        query = query.where(Deal.manager_id == effective_manager_id)
    if client_id:
        query = query.where(Deal.client_id == client_id)
    if date_from:
        query = query.where(func.date(Deal.created_at) >= date_from)
    if date_to:
        query = query.where(func.date(Deal.created_at) <= date_to)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(
        query.options(selectinload(Deal.params))
        .order_by(Deal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    deals = rows.scalars().all()
    manager_names = await _manager_names_by_id(db, {d.manager_id for d in deals})
    client_names = await _client_names_by_id(db, {d.client_id for d in deals})

    return PaginatedResponse(
        items=[
            _build_deal_list_item(
                d,
                manager_names.get(d.manager_id),
                client_names.get(d.client_id),
            )
            for d in deals
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/murabaha/quote", response_model=MurabahaQuoteResponse)
async def murabaha_quote(
    category: str = Query(..., pattern="^(consumer|phones|auto)$"),
    amount: float = Query(..., gt=0),
    term: int = Query(..., ge=1, le=360),
    tariff: str = Query(
        ...,
        pattern="^(NO_DOWNPAYMENT|NO_GUARANTOR|ONE_GUARANTOR|TWO_GUARANTORS)$",
    ),
    down_pct: int = Query(..., ge=0, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> MurabahaQuoteResponse:
    from backend.services.murabaha_tariff_service import (
        compute_murabaha_quote,
        load_murabaha_rate_settings,
    )

    try:
        rates = await load_murabaha_rate_settings(db)
        q = compute_murabaha_quote(
            category=category,
            amount=amount,
            term_months=term,
            tariff=tariff,
            down_payment_pct=down_pct,
            rates=rates,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MurabahaQuoteResponse(
        product_category=q.product_category,
        tariff=q.tariff,
        principal=q.principal,
        markup=q.markup,
        total=q.total,
        down_payment_pct=q.down_payment_pct,
        down_payment_amount=q.down_payment_amount,
        financed_amount=q.financed_amount,
        monthly_payment=q.monthly_payment,
        duration_months=q.duration_months,
        rate_per_month_pct=q.rate_per_month_pct,
    )


@router.get("/murabaha/tariff-options", response_model=MurabahaTariffOptionsResponse)
async def murabaha_tariff_options(
    category: str = Query(..., pattern="^(consumer|phones|auto)$"),
    amount: float = Query(..., gt=0),
    current_user: User = Depends(require_role("manager", "director")),
) -> MurabahaTariffOptionsResponse:
    from backend.services.murabaha_tariff_service import tariff_options_payload

    try:
        payload = tariff_options_payload(category, amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MurabahaTariffOptionsResponse.model_validate(payload)


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
    if body.type == DealType.murabaha and body.murabaha:
        from backend.services.murabaha_tariff_service import (
            load_murabaha_rate_settings,
            validate_murabaha_deal,
        )

        p = body.murabaha
        rates = await load_murabaha_rate_settings(db)
        try:
            quote = validate_murabaha_deal(
                category=p.product_category,
                amount=p.principal,
                term_months=p.duration_months,
                tariff=p.tariff,
                down_payment_pct=p.down_payment_pct,
                principal=p.principal,
                markup=p.markup,
                rates=rates,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        from backend.services.contract_number_service import allocate_contract_number

        item_qty = p.item_qty
        principal = p.principal
        markup = p.markup
        total = principal * item_qty + markup * item_qty if item_qty > 1 else principal + markup
        duration_months = p.duration_months
        start_date = p.start_date
        payday = p.payday if p.payday else start_date.day
        contract_number = await allocate_contract_number(db, start_date)

        guarantor_name = (p.guarantor_name or "").strip() or "—"
        guarantor_phone = (p.guarantor_phone or "").strip() or "—"

        params_data = {
            "principal": str(principal),
            "markup": str(markup),
            "duration_months": duration_months,
            "product_category": p.product_category,
            "tariff": p.tariff,
            "down_payment_pct": p.down_payment_pct,
            "down_payment_amount": str(quote.down_payment_amount),
            "monthly_payment": str(quote.monthly_payment),
            "item_qty": item_qty,
            "payday": payday,
            "pledge": p.pledge,
            "guarantor_name": guarantor_name,
            "guarantor_phone": guarantor_phone,
            "contract_number": contract_number,
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
        product_description=body.product_description,
        principal=principal,
        markup=markup,
        total=total,
        duration_months=duration_months,
        start_date=start_date,
        end_date=start_date + relativedelta(months=duration_months) if start_date else None,
    )
    db.add(deal)
    await db.flush()

    for key, value in params_data.items():
        if value is not None:
            db.add(DealParam(deal_id=deal.id, key=key, value=value))

    schedule_items = generate_schedule(body.type.value, params_data, start_date)
    await _create_schedules(db, deal, schedule_items)

    responsible_id = await resolve_responsible_manager_id(
        db, current_user, body.responsible_manager_id
    )
    await assign_deal_portfolio(db, deal, client, responsible_id)

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
        .options(
            selectinload(Deal.payment_schedules),
            selectinload(Deal.params),
            selectinload(Deal.manager),
        )
    )
    deal = result.scalar_one()
    return _build_deal_response(deal)


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> DealResponse:
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(
            selectinload(Deal.payment_schedules),
            selectinload(Deal.params),
            selectinload(Deal.manager),
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    await require_deal_access(db, deal, current_user)
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
    await require_deal_access(db, deal, current_user)
    if deal.status != DealStatus.draft:
        raise HTTPException(
            status_code=400,
            detail="Редактирование возможно только для черновика",
        )

    if body.product_description is not None:
        deal.product_description = body.product_description or None

    if body.murabaha and deal.type == DealType.murabaha:
        from backend.services.murabaha_tariff_service import (
            load_murabaha_rate_settings,
            validate_murabaha_deal,
        )

        p = body.murabaha
        rates = await load_murabaha_rate_settings(db)
        try:
            quote = validate_murabaha_deal(
                category=p.product_category,
                amount=p.principal,
                term_months=p.duration_months,
                tariff=p.tariff,
                down_payment_pct=p.down_payment_pct,
                principal=p.principal,
                markup=p.markup,
                rates=rates,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        item_qty = p.item_qty
        deal.principal = p.principal
        deal.markup = p.markup
        deal.total = p.principal * item_qty + p.markup * item_qty if item_qty > 1 else p.principal + p.markup
        deal.duration_months = p.duration_months
        deal.start_date = p.start_date
        payday = p.payday if p.payday else p.start_date.day
        guarantor_name = (p.guarantor_name or "").strip() or "—"
        guarantor_phone = (p.guarantor_phone or "").strip() or "—"
        params_data = {
            "principal": str(p.principal),
            "markup": str(p.markup),
            "duration_months": p.duration_months,
            "product_category": p.product_category,
            "tariff": p.tariff,
            "down_payment_pct": p.down_payment_pct,
            "down_payment_amount": str(quote.down_payment_amount),
            "monthly_payment": str(quote.monthly_payment),
            "item_qty": item_qty,
            "payday": payday,
            "pledge": p.pledge,
            "guarantor_name": guarantor_name,
            "guarantor_phone": guarantor_phone,
        }
        existing_keys = {param.key for param in deal.params}
        for key, value in params_data.items():
            if key in existing_keys:
                for param in deal.params:
                    if param.key == key:
                        param.value = value
            else:
                db.add(DealParam(deal_id=deal.id, key=key, value=value))
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
        .options(
            selectinload(Deal.payment_schedules),
            selectinload(Deal.params),
            selectinload(Deal.manager),
        )
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
    await require_deal_access(db, deal, current_user)
    if deal.status != DealStatus.draft:
        raise HTTPException(status_code=400, detail="Только черновик можно оформить")

    client = await db.get(Client, deal.client_id)
    if client:
        await assign_deal_portfolio(db, deal, client, current_user.id)
    new_status = await activate_deal(db, deal, current_user.id)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="STATUS_CHANGE",
        entity="deals",
        entity_id=str(deal.id),
        old_val={"status": "draft"},
        new_val={"status": new_status.value},
        ip=get_client_ip(request),
    )

    await db.commit()
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal.id)
        .options(
            selectinload(Deal.payment_schedules),
            selectinload(Deal.params),
            selectinload(Deal.manager),
        )
    )
    deal = result.scalar_one()
    return _build_deal_response(deal)


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
        product_description=deal.product_description,
        purchase_summary=deal_purchase_summary_from_deal(deal),
        manager_name=deal.manager.name if deal.manager else None,
        params=_deal_params_to_dict(deal) if deal.params else None,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        payment_schedules=schedules,
    )
