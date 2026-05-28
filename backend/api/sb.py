import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.deal import Deal, DealStatus
from backend.models.overdue import (
    ContactLog,
    OverdueCase,
    OverdueCaseStatus,
    PaymentPromise,
)
from backend.models.restructuring import Restructuring
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User
from backend.schemas.common import PaginatedResponse
from backend.schemas.sb import (
    AssignCaseRequest,
    CaseStatusUpdate,
    ContactLogCreate,
    ContactLogResponse,
    OverdueCaseResponse,
    PaymentPromiseCreate,
    PaymentPromiseResponse,
    RestructuringCreate,
    RestructuringResponse,
    SbDashboardResponse,
)
from backend.services.audit_service import AuditService
from backend.services.push_service import notify_staff

router = APIRouter(prefix="/api/sb", tags=["sb"])


@router.get("/cases", response_model=PaginatedResponse[OverdueCaseResponse])
async def list_cases(
    status_filter: OverdueCaseStatus | None = Query(None, alias="status"),
    sb_user_id: uuid.UUID | None = None,
    days_overdue_min: int | None = None,
    days_overdue_max: int | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> PaginatedResponse[OverdueCaseResponse]:
    query = select(OverdueCase)
    if status_filter:
        query = query.where(OverdueCase.status == status_filter)
    if sb_user_id:
        query = query.where(OverdueCase.sb_user_id == sb_user_id)
    if days_overdue_min is not None:
        query = query.where(OverdueCase.days_overdue >= days_overdue_min)
    if days_overdue_max is not None:
        query = query.where(OverdueCase.days_overdue <= days_overdue_max)
    if amount_min is not None:
        query = query.where(OverdueCase.total_debt >= amount_min)
    if amount_max is not None:
        query = query.where(OverdueCase.total_debt <= amount_max)

    query = query.order_by(OverdueCase.total_debt.desc(), OverdueCase.days_overdue.desc())

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(query.limit(limit).offset(offset))
    cases = rows.scalars().all()

    return PaginatedResponse(
        items=[OverdueCaseResponse.model_validate(c) for c in cases],
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


@router.post("/cases/{case_id}/restructure", response_model=RestructuringResponse)
async def request_restructure(
    case_id: uuid.UUID,
    body: RestructuringCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> RestructuringResponse:
    case = await db.get(OverdueCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    restructuring = Restructuring(
        deal_id=case.deal_id,
        case_id=case_id,
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
        entity_id=None,
        new_val={"case_id": str(case_id), "reason": body.reason},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(restructuring)
    return RestructuringResponse.model_validate(restructuring)


@router.get("/dashboard", response_model=SbDashboardResponse)
async def sb_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("sb", "director")),
) -> SbDashboardResponse:
    from decimal import Decimal
    from sqlalchemy import case as sa_case

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

    # Recovered this month (fulfilled promises)
    from datetime import date as date_cls
    month_start = today.replace(day=1)
    recovered_result = await db.execute(
        select(func.coalesce(func.sum(PaymentPromise.promised_amount), 0))
        .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
        .where(OverdueCase.sb_user_id == user_id)
        .where(PaymentPromise.is_fulfilled == True)  # noqa
        .where(PaymentPromise.updated_at >= datetime.combine(month_start, datetime.min.time()))
    )
    recovered = recovered_result.scalar_one() or Decimal("0")

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

    return SbDashboardResponse(
        my_cases_new=counts.get("new", 0),
        my_cases_in_progress=counts.get("in_progress", 0),
        my_cases_agreed=counts.get("agreed", 0),
        my_cases_closed=counts.get("closed", 0),
        promises_today=promises_today,
        promises_this_week=promises_week,
        recovered_this_month=Decimal(str(recovered)),
        red_zone_cases=red_zone_count,
    )
