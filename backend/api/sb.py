import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, get_current_user, require_role
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus
from backend.models.payment import PaymentSchedule, PaymentStatus
from backend.models.overdue import (
    ContactLog,
    OverdueCase,
    OverdueCaseStatus,
    PaymentPromise,
)
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User, UserRole
from backend.schemas.common import PaginatedResponse
from backend.schemas.sb import (
    AssignCaseRequest,
    CaseNotesUpdate,
    CaseStatusUpdate,
    ContactLogCreate,
    ContactLogResponse,
    OverdueCaseResponse,
    PaymentPromiseCreate,
    PaymentPromiseResponse,
    PaymentScheduleBrief,
    SbCaseContextResponse,
    SbDashboardResponse,
    SbStageCaseBrief,
    SbStatsResponse,
    SbTodayWorkItem,
    SbTodayWorkResponse,
)
from backend.services.audit_service import AuditService
from backend.services.push_service import notify_staff
from backend.services.deal_display import deal_purchase_summary_from_deal
from backend.services.overdue_case_service import refresh_overdue_case_after_payment
from backend.services.sb_presence_service import record_sb_presence

async def _track_sb_presence(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if current_user.role == UserRole.sb:
        await record_sb_presence(db, current_user.id)


router = APIRouter(
    prefix="/api/sb",
    tags=["sb"],
    dependencies=[Depends(_track_sb_presence)],
)


async def _get_red_zone_cutoff(db: AsyncSession) -> datetime:
    red_zone_setting = (
        await db.execute(
            select(SystemSetting.value).where(SystemSetting.key == SettingKey.RED_ZONE_DAYS)
        )
    ).scalar_one_or_none()
    red_zone_days = int(red_zone_setting) if red_zone_setting else 14
    red_zone_cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=red_zone_days)
    return datetime.combine(red_zone_cutoff_date, datetime.min.time(), tzinfo=timezone.utc)


async def _case_is_red_zone(
    db: AsyncSession, case_id: uuid.UUID, case_status: OverdueCaseStatus, red_cutoff: datetime
) -> bool:
    if case_status not in (OverdueCaseStatus.new, OverdueCaseStatus.in_progress):
        return False
    last_contact = (
        await db.execute(
            select(func.max(ContactLog.created_at)).where(ContactLog.case_id == case_id)
        )
    ).scalar_one()
    return last_contact is None or last_contact < red_cutoff


@router.post("/presence")
async def sb_presence_ping(
    current_user: User = Depends(require_role("sb")),
) -> dict:
    """Heartbeat from SB cabinet; presence is recorded by router dependency."""
    return {"detail": "ok"}


@router.get("/cases", response_model=PaginatedResponse[OverdueCaseResponse])
async def list_cases(
    status_filter: OverdueCaseStatus | None = Query(None, alias="status"),
    sb_user_id: uuid.UUID | None = None,
    unassigned: bool = False,
    days_overdue_min: int | None = None,
    days_overdue_max: int | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    red_zone_only: bool = False,
    collection_stage: int | None = None,
    collection_stage_min: int | None = None,
    q: str | None = Query(None, min_length=2),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> PaginatedResponse[OverdueCaseResponse]:
    from backend.services.overdue_case_service import (
        ensure_missing_overdue_cases,
        refresh_open_cases_for_deals,
    )
    from backend.services.search_service import client_text_filter

    await ensure_missing_overdue_cases(db)
    await db.commit()

    query = (
        select(OverdueCase, Client.full_name, Client.phone, Deal.manager_id, User.name.label("manager_name"))
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .join(Client, Deal.client_id == Client.id)
        .join(User, Deal.manager_id == User.id)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
    )
    if current_user.role == UserRole.sb:
        from backend.services.debt_collection_stage_service import (
            load_debt_stage_settings,
            resolve_sb_collection_stage,
        )

        stage_settings = await load_debt_stage_settings(db)
        assigned_stage = resolve_sb_collection_stage(current_user.id, stage_settings)
        query = query.where(OverdueCase.sb_user_id == current_user.id)
        if assigned_stage is not None:
            query = query.where(OverdueCase.collection_stage == assigned_stage)
        else:
            query = query.where(OverdueCase.collection_stage >= 2)
    else:
        stage_min = collection_stage_min if collection_stage_min is not None else 1
        query = query.where(OverdueCase.collection_stage >= stage_min)
        if collection_stage is not None:
            query = query.where(OverdueCase.collection_stage == collection_stage)
        if unassigned:
            query = query.where(OverdueCase.sb_user_id.is_(None))
        elif sb_user_id:
            query = query.where(OverdueCase.sb_user_id == sb_user_id)
    if status_filter:
        query = query.where(OverdueCase.status == status_filter)
    if days_overdue_min is not None:
        query = query.where(OverdueCase.days_overdue >= days_overdue_min)
    if days_overdue_max is not None:
        query = query.where(OverdueCase.days_overdue <= days_overdue_max)
    if amount_min is not None:
        query = query.where(OverdueCase.total_debt >= amount_min)
    if amount_max is not None:
        query = query.where(OverdueCase.total_debt <= amount_max)
    if q:
        query = query.where(client_text_filter(q))

    query = query.order_by(OverdueCase.total_debt.desc(), OverdueCase.days_overdue.desc())

    red_cutoff = await _get_red_zone_cutoff(db)

    if red_zone_only:
        all_rows = (await db.execute(query)).all()
        filtered = []
        for case, client_name, client_phone, manager_id, manager_name in all_rows:
            if await _case_is_red_zone(db, case.id, case.status, red_cutoff):
                filtered.append((case, client_name, client_phone, manager_id, manager_name))
        total = len(filtered)
        page_rows = filtered[offset : offset + limit]
    else:
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        page_rows = (await db.execute(query.limit(limit).offset(offset))).all()

    deal_ids = list({case.deal_id for case, _, _, _, _ in page_rows})
    if deal_ids:
        await refresh_open_cases_for_deals(db, deal_ids)
        await db.commit()

    items = []
    for case, client_name, client_phone, manager_id, manager_name in page_rows:
        await db.refresh(case)
        if case.status == OverdueCaseStatus.closed:
            continue
        resp = OverdueCaseResponse.model_validate(case)
        resp.is_red_zone = await _case_is_red_zone(db, case.id, case.status, red_cutoff)
        resp.client_name = client_name
        resp.client_phone = client_phone
        resp.manager_id = manager_id
        resp.manager_name = manager_name
        items.append(resp)

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/cases/{case_id}", response_model=OverdueCaseResponse)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> OverdueCaseResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    await refresh_overdue_case_after_payment(db, case.deal_id)
    await db.refresh(case)
    await db.commit()
    return OverdueCaseResponse.model_validate(case)


@router.patch("/cases/{case_id}/notes", response_model=OverdueCaseResponse)
async def update_case_notes(
    case_id: uuid.UUID,
    body: CaseNotesUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> OverdueCaseResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    case.internal_notes = body.internal_notes
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="UPDATE",
        entity="overdue_cases",
        entity_id=str(case_id),
        new_val={"internal_notes": "updated"},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(case)
    return OverdueCaseResponse.model_validate(case)


@router.patch("/cases/{case_id}/assign")
async def assign_case(
    case_id: uuid.UUID,
    body: AssignCaseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> dict:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    if case.collection_stage < 2 and current_user.role == UserRole.sb:
        raise HTTPException(
            status_code=400,
            detail="На этапе 1 дело ведёт менеджер сделки",
        )

    sb_user = await db.get(User, body.sb_user_id)
    if not sb_user or sb_user.role.value not in ("sb", "director"):
        raise HTTPException(status_code=400, detail="Пользователь не является сотрудником СБ")

    old_assignee = case.sb_user_id
    case.sb_user_id = body.sb_user_id
    case.assigned_at = datetime.now(timezone.utc)
    if case.status == OverdueCaseStatus.new:
        case.status = OverdueCaseStatus.in_progress

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CASE_ASSIGNED",
        entity="overdue_cases",
        entity_id=str(case_id),
        old_val={"sb_user_id": str(old_assignee) if old_assignee else None},
        new_val={"sb_user_id": str(body.sb_user_id)},
        ip=get_client_ip(request),
    )
    await notify_staff(
        db=db,
        user_id=body.sb_user_id,
        title="Вам назначено дело",
        body=f"Долг: {case.total_debt} ₽ · Просрочка: {case.days_overdue} дн.",
        entity_type="overdue_cases",
        entity_id=str(case_id),
        action_url=f"/sb/cases/{case_id}",
    )
    await db.commit()
    return {"detail": "Дело назначено"}


@router.post("/cases/{case_id}/take")
async def take_case(
    case_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb")),
) -> dict:
    """SB employee assigns an unassigned case to themselves."""
    return await assign_case(
        case_id=case_id,
        body=AssignCaseRequest(sb_user_id=current_user.id),
        request=request,
        db=db,
        current_user=current_user,
    )


@router.patch("/cases/{case_id}/status")
async def update_case_status(
    case_id: uuid.UUID,
    body: CaseStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> dict:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    old_status = case.status
    case.status = body.status
    if body.status == OverdueCaseStatus.closed:
        case.closed_at = datetime.now(timezone.utc)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="STATUS_CHANGE",
        entity="overdue_cases",
        entity_id=str(case_id),
        old_val={"status": old_status.value},
        new_val={"status": body.status.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": f"Статус изменён на {body.status.value}"}


@router.post("/cases/{case_id}/contacts", response_model=ContactLogResponse)
async def add_contact_log(
    case_id: uuid.UUID,
    body: ContactLogCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> ContactLogResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    log = ContactLog(
        case_id=case_id,
        sb_user_id=current_user.id,
        type=body.type,
        result=body.result,
        next_action=body.next_action,
        next_action_date=body.next_action_date,
    )
    db.add(log)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CONTACT_LOGGED",
        entity="contact_logs",
        entity_id=None,
        new_val={"case_id": str(case_id), "type": body.type.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(log)
    return ContactLogResponse.model_validate(log)


@router.get("/cases/{case_id}/contacts", response_model=list[ContactLogResponse])
async def get_contact_logs(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> list[ContactLogResponse]:
    rows = await db.execute(
        select(ContactLog)
        .where(ContactLog.case_id == case_id)
        .order_by(ContactLog.created_at.desc())
    )
    return [ContactLogResponse.model_validate(c) for c in rows.scalars().all()]


@router.post("/cases/{case_id}/promises", response_model=PaymentPromiseResponse)
async def add_promise(
    case_id: uuid.UUID,
    body: PaymentPromiseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> PaymentPromiseResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    promise = PaymentPromise(
        case_id=case_id,
        promised_date=body.promised_date,
        promised_amount=body.promised_amount,
    )
    db.add(promise)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="PROMISE_ADDED",
        entity="payment_promises",
        entity_id=None,
        new_val={
            "case_id": str(case_id),
            "promised_date": str(body.promised_date),
            "promised_amount": str(body.promised_amount),
        },
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(promise)
    return PaymentPromiseResponse.model_validate(promise)


@router.get("/cases/{case_id}/promises", response_model=list[PaymentPromiseResponse])
async def get_promises(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> list[PaymentPromiseResponse]:
    rows = await db.execute(
        select(PaymentPromise)
        .where(PaymentPromise.case_id == case_id)
        .order_by(PaymentPromise.promised_date)
    )
    return [PaymentPromiseResponse.model_validate(p) for p in rows.scalars().all()]


@router.get("/dashboard", response_model=SbDashboardResponse)
async def sb_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> SbDashboardResponse:
    from decimal import Decimal
    from sqlalchemy import case as sa_case

    from backend.services.overdue_case_service import ensure_missing_overdue_cases

    await ensure_missing_overdue_cases(db)
    await db.commit()

    user_id = current_user.id
    today = datetime.now(timezone.utc).date()

    # My cases by status
    status_counts = await db.execute(
        select(OverdueCase.status, func.count())
        .where(OverdueCase.sb_user_id == user_id)
        .group_by(OverdueCase.status)
    )
    counts = {row[0].value: row[1] for row in status_counts.all()}

    # Promises today
    promises_today = (
        await db.execute(
            select(func.count())
            .select_from(PaymentPromise)
            .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
            .where(OverdueCase.sb_user_id == user_id)
            .where(PaymentPromise.promised_date == today)
            .where(PaymentPromise.is_fulfilled == False)  # noqa
        )
    ).scalar_one()

    # Promises this week
    from datetime import timedelta
    week_end = today + timedelta(days=7)
    promises_week = (
        await db.execute(
            select(func.count())
            .select_from(PaymentPromise)
            .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
            .where(OverdueCase.sb_user_id == user_id)
            .where(PaymentPromise.promised_date >= today)
            .where(PaymentPromise.promised_date <= week_end)
            .where(PaymentPromise.is_fulfilled == False)  # noqa
        )
    ).scalar_one()

    # Collected this month: payments recorded by SB (not promise flags)
    from backend.services.sb_metrics_service import sb_collected_amount

    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    recovered = await sb_collected_amount(db, user_id, month_start_dt, now_dt)

    # Red zone: cases without contact in N days
    red_zone_setting = (
        await db.execute(
            select(SystemSetting.value).where(SystemSetting.key == SettingKey.RED_ZONE_DAYS)
        )
    ).scalar_one_or_none()
    red_zone_days = int(red_zone_setting) if red_zone_setting else 14
    red_zone_cutoff = today - __import__("datetime").timedelta(days=red_zone_days)

    red_zone_subq = (
        select(ContactLog.case_id, func.max(ContactLog.created_at).label("last_contact"))
        .group_by(ContactLog.case_id)
        .subquery()
    )

    red_zone_count = (
        await db.execute(
            select(func.count())
            .select_from(OverdueCase)
            .outerjoin(red_zone_subq, OverdueCase.id == red_zone_subq.c.case_id)
            .where(OverdueCase.sb_user_id == user_id)
            .where(OverdueCase.status.in_([OverdueCaseStatus.new, OverdueCaseStatus.in_progress]))
            .where(
                (red_zone_subq.c.last_contact == None)  # noqa
                | (red_zone_subq.c.last_contact < datetime.combine(red_zone_cutoff, datetime.min.time()))
            )
        )
    ).scalar_one()

    unassigned_total = (
        await db.execute(
            select(func.count())
            .select_from(OverdueCase)
            .where(OverdueCase.sb_user_id.is_(None))
            .where(OverdueCase.collection_stage >= 2)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
        )
    ).scalar_one()

    from backend.services.debt_collection_stage_service import (
        load_debt_stage_settings,
        resolve_sb_collection_stage,
    )

    stage_settings = await load_debt_stage_settings(db)
    assigned_stage = (
        resolve_sb_collection_stage(user_id, stage_settings)
        if current_user.role == UserRole.sb
        else None
    )
    stage_open_cases: list[SbStageCaseBrief] = []
    if assigned_stage is not None:
        stage_rows = await db.execute(
            select(OverdueCase, Client.full_name)
            .join(Deal, OverdueCase.deal_id == Deal.id)
            .join(Client, Deal.client_id == Client.id)
            .where(OverdueCase.sb_user_id == user_id)
            .where(OverdueCase.collection_stage == assigned_stage)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
            .order_by(OverdueCase.days_overdue.desc())
            .limit(10)
        )
        stage_open_cases = [
            SbStageCaseBrief(
                case_id=case.id,
                deal_id=case.deal_id,
                client_name=client_name,
                days_overdue=case.days_overdue,
                total_debt=Decimal(str(case.total_debt)),
                overdue_installments_count=case.overdue_installments_count,
                collection_stage=case.collection_stage,
            )
            for case, client_name in stage_rows.all()
        ]

    return SbDashboardResponse(
        my_cases_new=counts.get("new", 0),
        my_cases_in_progress=counts.get("in_progress", 0),
        my_cases_agreed=counts.get("agreed", 0),
        my_cases_closed=counts.get("closed", 0),
        promises_today=promises_today,
        promises_this_week=promises_week,
        recovered_this_month=Decimal(str(recovered)),
        red_zone_cases=red_zone_count,
        unassigned_cases_total=unassigned_total,
        assigned_collection_stage=assigned_stage,
        stage_open_cases=stage_open_cases,
    )


@router.get("/dashboard/today", response_model=SbTodayWorkResponse)
async def sb_dashboard_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb")),
) -> SbTodayWorkResponse:
    from backend.services.overdue_case_service import ensure_missing_overdue_cases

    await ensure_missing_overdue_cases(db)
    await db.commit()

    user_id = current_user.id
    today = datetime.now(timezone.utc).date()
    red_cutoff = await _get_red_zone_cutoff(db)

    my_cases = (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.sb_user_id == user_id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
            .order_by(OverdueCase.total_debt.desc())
        )
    ).scalars().all()

    red_zone_cases: list[SbTodayWorkItem] = []
    for case in my_cases:
        if await _case_is_red_zone(db, case.id, case.status, red_cutoff):
            last_contact = (
                await db.execute(
                    select(func.max(ContactLog.created_at)).where(ContactLog.case_id == case.id)
                )
            ).scalar_one()
            red_zone_cases.append(
                SbTodayWorkItem(
                    case_id=case.id,
                    deal_id=case.deal_id,
                    total_debt=Decimal(str(case.total_debt)),
                    days_overdue=case.days_overdue,
                    status=case.status.value,
                    last_contact_at=last_contact,
                )
            )

    async def _promises_for_date(condition) -> list[SbTodayWorkItem]:
        rows = await db.execute(
            select(PaymentPromise, OverdueCase)
            .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
            .where(OverdueCase.sb_user_id == user_id)
            .where(PaymentPromise.is_fulfilled == False)  # noqa: E712
            .where(condition)
            .order_by(PaymentPromise.promised_date)
        )
        items = []
        for promise, case in rows.all():
            items.append(
                SbTodayWorkItem(
                    case_id=case.id,
                    deal_id=case.deal_id,
                    total_debt=Decimal(str(case.total_debt)),
                    days_overdue=case.days_overdue,
                    status=case.status.value,
                    promised_date=promise.promised_date,
                    promised_amount=Decimal(str(promise.promised_amount)),
                    promise_id=promise.id,
                )
            )
        return items

    promises_today = await _promises_for_date(PaymentPromise.promised_date == today)
    promises_overdue = await _promises_for_date(PaymentPromise.promised_date < today)

    unassigned_rows = (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.sb_user_id.is_(None))
            .where(OverdueCase.collection_stage >= 2)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
            .order_by(OverdueCase.total_debt.desc())
            .limit(10)
        )
    ).scalars().all()
    unassigned_top = [
        SbTodayWorkItem(
            case_id=c.id,
            deal_id=c.deal_id,
            total_debt=Decimal(str(c.total_debt)),
            days_overdue=c.days_overdue,
            status=c.status.value,
        )
        for c in unassigned_rows
    ]

    return SbTodayWorkResponse(
        red_zone_cases=red_zone_cases,
        promises_today=promises_today,
        promises_overdue=promises_overdue,
        unassigned_top=unassigned_top,
    )


@router.get("/cases/{case_id}/context", response_model=SbCaseContextResponse)
async def get_case_context(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> SbCaseContextResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    if current_user.role == UserRole.sb and case.sb_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Дело не назначено вам")

    await refresh_overdue_case_after_payment(db, case.deal_id)
    await db.refresh(case)

    deal_row = await db.execute(
        select(Deal)
        .where(Deal.id == case.deal_id)
        .options(selectinload(Deal.params), selectinload(Deal.manager))
    )
    deal = deal_row.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")

    client = await db.get(Client, deal.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    next_schedule = (
        await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.deal_id == deal.id)
            .where(PaymentSchedule.status.in_([PaymentStatus.pending, PaymentStatus.overdue, PaymentStatus.partial]))
            .order_by(PaymentSchedule.due_date)
            .limit(1)
        )
    ).scalar_one_or_none()

    pending_rows = (
        await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.deal_id == deal.id)
            .where(PaymentSchedule.status.in_([PaymentStatus.pending, PaymentStatus.overdue, PaymentStatus.partial]))
            .order_by(PaymentSchedule.due_date)
        )
    ).scalars().all()

    deal_manager = deal.manager

    resp = SbCaseContextResponse(
        client_id=client.id,
        client_name=client.full_name,
        client_phone=client.phone,
        manager_id=deal.manager_id,
        manager_name=deal_manager.name if deal_manager else "—",
        deal_type=deal.type.value,
        deal_status=deal.status.value,
        deal_total=Decimal(str(deal.total)),
        product_description=deal.product_description,
        purchase_summary=deal_purchase_summary_from_deal(deal),
        next_schedule_due_date=next_schedule.due_date if next_schedule else None,
        next_schedule_amount=Decimal(str(next_schedule.amount)) if next_schedule else None,
        pending_schedules=[
            PaymentScheduleBrief(
                id=s.id,
                installment_number=s.installment_number,
                due_date=s.due_date,
                amount=Decimal(str(s.amount)),
                paid_amount=Decimal(str(s.paid_amount)),
                status=s.status.value,
            )
            for s in pending_rows
        ],
    )
    await db.commit()
    return resp


@router.get("/stats", response_model=SbStatsResponse)
async def sb_stats(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb")),
) -> SbStatsResponse:
    user_id = current_user.id
    today = datetime.now(timezone.utc).date()
    period_from = date_from or today.replace(day=1)
    period_to = date_to or today
    start_dt = datetime.combine(period_from, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(period_to, datetime.max.time(), tzinfo=timezone.utc)

    cases_closed = (
        await db.execute(
            select(func.count())
            .where(OverdueCase.sb_user_id == user_id)
            .where(OverdueCase.status == OverdueCaseStatus.closed)
            .where(OverdueCase.closed_at >= start_dt)
            .where(OverdueCase.closed_at <= end_dt)
        )
    ).scalar_one()

    from backend.services.sb_metrics_service import sb_collected_amount

    fulfilled_amount = await sb_collected_amount(db, user_id, start_dt, end_dt)

    avg_days = (
        await db.execute(
            select(func.avg(OverdueCase.days_overdue))
            .where(OverdueCase.sb_user_id == user_id)
            .where(OverdueCase.status == OverdueCaseStatus.closed)
            .where(OverdueCase.closed_at >= start_dt)
            .where(OverdueCase.closed_at <= end_dt)
        )
    ).scalar_one()

    return SbStatsResponse(
        cases_closed=cases_closed,
        promises_fulfilled_amount=Decimal(str(fulfilled_amount or 0)),
        avg_days_overdue_closed=float(avg_days) if avg_days is not None else None,
    )


@router.get("/promises/calendar")
async def sb_promises_calendar(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb")),
) -> list[dict]:
    rows = await db.execute(
        select(PaymentPromise, OverdueCase)
        .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
        .where(OverdueCase.sb_user_id == current_user.id)
        .where(PaymentPromise.promised_date >= date_from)
        .where(PaymentPromise.promised_date <= date_to)
        .where(PaymentPromise.is_fulfilled == False)  # noqa: E712
        .order_by(PaymentPromise.promised_date)
    )
    return [
        {
            "promise_id": str(p.id),
            "case_id": str(c.id),
            "deal_id": str(c.deal_id),
            "promised_date": p.promised_date.isoformat(),
            "promised_amount": float(p.promised_amount),
            "is_fulfilled": p.is_fulfilled,
            "total_debt": float(c.total_debt),
        }
        for p, c in rows.all()
    ]
