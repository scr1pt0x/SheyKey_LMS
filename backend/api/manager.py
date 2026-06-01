"""Manager personal dashboard and stats."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus
from backend.models.payment import Payment, PaymentSchedule, PaymentStatus
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.user import User
from backend.schemas.manager import (
    CashLedgerItem,
    DealBrief,
    ManagerCashManualCreate,
    ManagerCashResponse,
    ManagerDashboardResponse,
    ManagerStatsResponse,
    ScheduledPaymentBrief,
    Stage1OverdueBrief,
)
from backend.services.audit_service import AuditService
from backend.models.manager_cash_entry import ManagerCashEntryKind
from backend.services.manager_cash_service import (
    build_cash_ledger,
    cash_balance,
    cash_totals,
    create_cash_entry,
)

router = APIRouter(prefix="/api/manager", tags=["manager"])


def _manager_id(user: User) -> uuid.UUID:
    return user.id


@router.get("/dashboard", response_model=ManagerDashboardResponse)
async def manager_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> ManagerDashboardResponse:
    from backend.services.overdue_case_service import sync_overdue_case_for_deal

    mid = _manager_id(current_user)
    today = datetime.now(timezone.utc).date()

    overdue_deal_ids = (
        await db.execute(
            select(Deal.id).where(Deal.manager_id == mid).where(Deal.status == DealStatus.overdue)
        )
    ).scalars().all()
    for deal_id in overdue_deal_ids:
        await sync_overdue_case_for_deal(db, deal_id)

    week_start_date = today - timedelta(days=6)
    month_start = today.replace(day=1)
    day_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    week_start = datetime.combine(week_start_date, datetime.min.time(), tzinfo=timezone.utc)
    month_start_dt = datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc)
    week_end_date = today + timedelta(days=7)

    async def count_deals(status: DealStatus) -> int:
        return (
            await db.execute(
                select(func.count()).where(Deal.manager_id == mid).where(Deal.status == status)
            )
        ).scalar_one()

    active_deals = await count_deals(DealStatus.active)
    overdue_deals = await count_deals(DealStatus.overdue)
    draft_deals = await count_deals(DealStatus.draft)

    portfolio_active_total = (
        await db.execute(
            select(func.coalesce(func.sum(Deal.total), 0))
            .where(Deal.manager_id == mid)
            .where(Deal.status == DealStatus.active)
        )
    ).scalar_one()

    payments_today = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Deal, Payment.deal_id == Deal.id)
            .where(Deal.manager_id == mid)
            .where(Payment.paid_at >= day_start)
            .where(Payment.paid_at <= day_end)
        )
    ).scalar_one()

    payments_week = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Deal, Payment.deal_id == Deal.id)
            .where(Deal.manager_id == mid)
            .where(Payment.paid_at >= week_start)
            .where(Payment.paid_at <= day_end)
        )
    ).scalar_one()

    payments_month = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Deal, Payment.deal_id == Deal.id)
            .where(Deal.manager_id == mid)
            .where(Payment.paid_at >= month_start_dt)
            .where(Payment.paid_at <= day_end)
        )
    ).scalar_one()

    deals_created_month = (
        await db.execute(
            select(func.count())
            .where(Deal.manager_id == mid)
            .where(Deal.created_at >= month_start_dt)
        )
    ).scalar_one()

    def _schedule_rows(date_from, date_to):
        return (
            select(PaymentSchedule, Deal)
            .join(Deal, PaymentSchedule.deal_id == Deal.id)
            .where(Deal.manager_id == mid)
            .where(PaymentSchedule.due_date >= date_from)
            .where(PaymentSchedule.due_date <= date_to)
            .where(PaymentSchedule.status.in_([PaymentStatus.pending, PaymentStatus.partial]))
            .where(Deal.status.in_([DealStatus.active, DealStatus.overdue]))
            .order_by(PaymentSchedule.due_date)
            .limit(10)
        )

    today_rows = await db.execute(_schedule_rows(today, today))
    week_rows = await db.execute(_schedule_rows(today, week_end_date))

    schedules_today = [
        ScheduledPaymentBrief(
            schedule_id=s.id,
            deal_id=d.id,
            client_id=d.client_id,
            due_date=s.due_date,
            amount=Decimal(str(s.amount)),
            status=s.status.value,
        )
        for s, d in today_rows.all()
    ]
    schedules_week = [
        ScheduledPaymentBrief(
            schedule_id=s.id,
            deal_id=d.id,
            client_id=d.client_id,
            due_date=s.due_date,
            amount=Decimal(str(s.amount)),
            status=s.status.value,
        )
        for s, d in week_rows.all()
    ]

    overdue_list_rows = await db.execute(
        select(Deal)
        .where(Deal.manager_id == mid)
        .where(Deal.status == DealStatus.overdue)
        .order_by(Deal.updated_at.desc())
        .limit(5)
    )

    stage1_rows = await db.execute(
        select(OverdueCase, Deal)
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .where(Deal.manager_id == mid)
        .where(OverdueCase.collection_stage == 1)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
        .order_by(OverdueCase.days_overdue.desc())
        .limit(10)
    )
    stage1_overdue_cases = [
        Stage1OverdueBrief(
            case_id=case.id,
            deal_id=deal.id,
            client_id=deal.client_id,
            type=deal.type.value,
            total=Decimal(str(deal.total)),
            days_overdue=case.days_overdue,
            total_debt=Decimal(str(case.total_debt)),
            overdue_installments_count=case.overdue_installments_count,
        )
        for case, deal in stage1_rows.all()
    ]

    def _deal_brief(d: Deal) -> DealBrief:
        return DealBrief(
            id=d.id,
            client_id=d.client_id,
            type=d.type.value,
            status=d.status.value,
            total=Decimal(str(d.total)),
        )

    return ManagerDashboardResponse(
        active_deals=active_deals,
        overdue_deals=overdue_deals,
        draft_deals=draft_deals,
        portfolio_active_total=Decimal(str(portfolio_active_total)),
        payments_today=Decimal(str(payments_today)),
        payments_week=Decimal(str(payments_week)),
        payments_month=Decimal(str(payments_month)),
        deals_created_month=deals_created_month,
        schedules_today=schedules_today,
        schedules_week=schedules_week,
        overdue_deals_list=[_deal_brief(d) for d in overdue_list_rows.scalars().all()],
        stage1_overdue_cases=stage1_overdue_cases,
    )


@router.get("/stats", response_model=ManagerStatsResponse)
async def manager_stats(
    month: str | None = Query(None, description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> ManagerStatsResponse:
    mid = _manager_id(current_user)
    today = datetime.now(timezone.utc).date()
    if month:
        try:
            year, mon = map(int, month.split("-"))
            period_start = today.replace(year=year, month=mon, day=1)
        except ValueError:
            period_start = today.replace(day=1)
    else:
        period_start = today.replace(day=1)

    if period_start.month == 12:
        next_month = period_start.replace(year=period_start.year + 1, month=1, day=1)
    else:
        next_month = period_start.replace(month=period_start.month + 1, day=1)

    period_start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    period_end_dt = datetime.combine(next_month, datetime.min.time(), tzinfo=timezone.utc)

    deals_created = (
        await db.execute(
            select(func.count())
            .where(Deal.manager_id == mid)
            .where(Deal.created_at >= period_start_dt)
            .where(Deal.created_at < period_end_dt)
        )
    ).scalar_one()

    payments_collected = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Deal, Payment.deal_id == Deal.id)
            .where(Deal.manager_id == mid)
            .where(Payment.paid_at >= period_start_dt)
            .where(Payment.paid_at < period_end_dt)
        )
    ).scalar_one()

    return ManagerStatsResponse(
        deals_created=deals_created,
        payments_collected=Decimal(str(payments_collected)),
    )


@router.get("/cash", response_model=ManagerCashResponse)
async def manager_cash_ledger(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> ManagerCashResponse:
    mid = _manager_id(current_user)
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    day_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    month_start_dt = datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc)

    rows, total = await build_cash_ledger(
        db, mid, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    total_today, total_month, total_all = await cash_totals(
        db, mid, day_start, day_end, month_start_dt
    )

    return ManagerCashResponse(
        items=[
            CashLedgerItem(
                id=r.id,
                entry_type=r.entry_type,
                amount=r.amount,
                paid_at=r.paid_at,
                method=r.method,
                description=r.description,
                deal_id=r.deal_id,
                client_name=r.client_name,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
        total_today=total_today,
        total_month=total_month,
        total_all_time=total_all,
    )


@router.post("/cash", response_model=CashLedgerItem, status_code=status.HTTP_201_CREATED)
async def manager_cash_manual_entry(
    body: ManagerCashManualCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CashLedgerItem:
    mid = _manager_id(current_user)
    kind = (
        ManagerCashEntryKind.expense
        if body.entry_kind == "expense"
        else ManagerCashEntryKind.income
    )
    if kind == ManagerCashEntryKind.expense:
        balance = await cash_balance(db, mid, None, None)
        if body.amount > balance:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно средств в кассе. Доступно: {balance}",
            )

    entry = await create_cash_entry(
        db,
        mid,
        amount=body.amount,
        paid_at=body.paid_at,
        method=body.method,
        description=body.description,
        entry_kind=kind,
    )
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CASH_EXPENSE" if kind == ManagerCashEntryKind.expense else "CASH_MANUAL_ENTRY",
        entity="manager_cash_entries",
        entity_id=str(entry.id),
        new_val={
            "amount": str(body.amount),
            "method": body.method.value,
            "entry_kind": kind.value,
        },
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(entry)
    ledger_type = "expense" if kind == ManagerCashEntryKind.expense else "manual"
    return CashLedgerItem(
        id=f"manual-{entry.id}",
        entry_type=ledger_type,
        amount=Decimal(str(entry.amount)),
        paid_at=entry.paid_at,
        method=entry.method.value,
        description=entry.description,
        deal_id=None,
        client_name=None,
    )
