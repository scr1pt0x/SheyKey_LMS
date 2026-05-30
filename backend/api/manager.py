"""Manager personal dashboard and stats."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.client import Client, KycStatus
from backend.models.deal import Deal, DealStatus
from backend.models.payment import Payment, PaymentSchedule, PaymentStatus
from backend.models.user import User
from backend.schemas.manager import (
    DealBrief,
    ManagerDashboardResponse,
    ManagerStatsResponse,
    ScheduledPaymentBrief,
)

router = APIRouter(prefix="/api/manager", tags=["manager"])


def _manager_id(user: User) -> uuid.UUID:
    return user.id


@router.get("/dashboard", response_model=ManagerDashboardResponse)
async def manager_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> ManagerDashboardResponse:
    mid = _manager_id(current_user)
    today = datetime.now(timezone.utc).date()
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
    pending_deals = await count_deals(DealStatus.pending)
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

    clients_kyc_pending = (
        await db.execute(
            select(func.count())
            .where(Client.manager_id == mid)
            .where(Client.kyc_status == KycStatus.pending)
            .where(Client.is_archived == False)  # noqa: E712
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
    pending_list_rows = await db.execute(
        select(Deal)
        .where(Deal.manager_id == mid)
        .where(Deal.status == DealStatus.pending)
        .order_by(Deal.created_at.desc())
        .limit(5)
    )

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
        pending_deals=pending_deals,
        draft_deals=draft_deals,
        portfolio_active_total=Decimal(str(portfolio_active_total)),
        payments_today=Decimal(str(payments_today)),
        payments_week=Decimal(str(payments_week)),
        payments_month=Decimal(str(payments_month)),
        clients_kyc_pending=clients_kyc_pending,
        deals_created_month=deals_created_month,
        schedules_today=schedules_today,
        schedules_week=schedules_week,
        overdue_deals_list=[_deal_brief(d) for d in overdue_list_rows.scalars().all()],
        pending_deals_list=[_deal_brief(d) for d in pending_list_rows.scalars().all()],
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
