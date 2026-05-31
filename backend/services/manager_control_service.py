"""Aggregated metrics for director manager control overview."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus
from backend.models.manager_cash_entry import ManagerCashEntry, ManagerCashEntryKind
from backend.models.payment import Payment
from backend.models.user import User, UserRole
from backend.schemas.director import ManagerControlItem


def _overdue_pct(active: int, overdue: int) -> float:
    total = active + overdue
    if total == 0:
        return 0.0
    return round(overdue / total * 100, 1)


async def fetch_managers_overview(db: AsyncSession) -> list[ManagerControlItem]:
    today = datetime.now(timezone.utc).date()
    week_start_date = today - timedelta(days=6)
    month_start = today.replace(day=1)
    day_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    week_start = datetime.combine(week_start_date, datetime.min.time(), tzinfo=timezone.utc)
    month_start_dt = datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc)

    deal_stats = (
        select(
            Deal.manager_id.label("manager_id"),
            func.count(Deal.id).filter(Deal.status == DealStatus.active).label("active"),
            func.count(Deal.id).filter(Deal.status == DealStatus.overdue).label("overdue"),
            func.count(Deal.id).filter(Deal.status == DealStatus.draft).label("draft"),
            func.coalesce(
                func.sum(Deal.total).filter(Deal.status == DealStatus.active), 0
            ).label("portfolio"),
            func.count(Deal.id)
            .filter(Deal.created_at >= month_start_dt)
            .label("deals_created_month"),
        )
        .group_by(Deal.manager_id)
        .subquery()
    )

    client_stats = (
        select(
            Client.manager_id.label("manager_id"),
            func.count(Client.id).label("clients_count"),
        )
        .where(Client.is_archived == False)  # noqa: E712
        .group_by(Client.manager_id)
        .subquery()
    )

    payment_stats = (
        select(
            Deal.manager_id.label("manager_id"),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.paid_at >= day_start, Payment.paid_at <= day_end
                ),
                0,
            ).label("payments_today"),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.paid_at >= week_start, Payment.paid_at <= day_end
                ),
                0,
            ).label("payments_week"),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.paid_at >= month_start_dt, Payment.paid_at <= day_end
                ),
                0,
            ).label("payments_month"),
        )
        .join(Payment, Payment.deal_id == Deal.id)
        .group_by(Deal.manager_id)
        .subquery()
    )

    manual_income_month = (
        select(
            ManagerCashEntry.manager_id.label("manager_id"),
            func.coalesce(func.sum(ManagerCashEntry.amount), 0).label("manual_income_month"),
        )
        .where(ManagerCashEntry.entry_kind == ManagerCashEntryKind.income)
        .where(ManagerCashEntry.paid_at >= month_start_dt)
        .where(ManagerCashEntry.paid_at <= day_end)
        .group_by(ManagerCashEntry.manager_id)
        .subquery()
    )

    manual_expense_month = (
        select(
            ManagerCashEntry.manager_id.label("manager_id"),
            func.coalesce(func.sum(ManagerCashEntry.amount), 0).label("manual_expense_month"),
        )
        .where(ManagerCashEntry.entry_kind == ManagerCashEntryKind.expense)
        .where(ManagerCashEntry.paid_at >= month_start_dt)
        .where(ManagerCashEntry.paid_at <= day_end)
        .group_by(ManagerCashEntry.manager_id)
        .subquery()
    )

    last_activity_sq = (
        select(
            AuditLog.user_id.label("user_id"),
            func.max(AuditLog.created_at).label("last_activity"),
        )
        .where(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id)
        .subquery()
    )

    rows = await db.execute(
        select(
            User.id,
            User.name,
            func.coalesce(deal_stats.c.active, 0).label("active"),
            func.coalesce(deal_stats.c.overdue, 0).label("overdue"),
            func.coalesce(deal_stats.c.draft, 0).label("draft"),
            func.coalesce(deal_stats.c.portfolio, 0).label("portfolio"),
            func.coalesce(deal_stats.c.deals_created_month, 0).label("deals_created_month"),
            func.coalesce(client_stats.c.clients_count, 0).label("clients_count"),
            func.coalesce(payment_stats.c.payments_today, 0).label("payments_today"),
            func.coalesce(payment_stats.c.payments_week, 0).label("payments_week"),
            func.coalesce(payment_stats.c.payments_month, 0).label("payments_month"),
            func.coalesce(manual_income_month.c.manual_income_month, 0).label(
                "manual_income_month"
            ),
            func.coalesce(manual_expense_month.c.manual_expense_month, 0).label(
                "manual_expense_month"
            ),
            last_activity_sq.c.last_activity,
        )
        .where(User.role == UserRole.manager)
        .where(User.is_active == True)  # noqa: E712
        .outerjoin(deal_stats, deal_stats.c.manager_id == User.id)
        .outerjoin(client_stats, client_stats.c.manager_id == User.id)
        .outerjoin(payment_stats, payment_stats.c.manager_id == User.id)
        .outerjoin(manual_income_month, manual_income_month.c.manager_id == User.id)
        .outerjoin(manual_expense_month, manual_expense_month.c.manager_id == User.id)
        .outerjoin(last_activity_sq, last_activity_sq.c.user_id == User.id)
        .order_by(User.name)
    )

    items: list[ManagerControlItem] = []
    for r in rows.all():
        active = int(r.active or 0)
        overdue = int(r.overdue or 0)
        payments_month = Decimal(str(r.payments_month))
        manual_in = Decimal(str(r.manual_income_month))
        manual_out = Decimal(str(r.manual_expense_month))
        cash_month = payments_month + manual_in - manual_out

        items.append(
            ManagerControlItem(
                user_id=r.id,
                name=r.name,
                active_deals=active,
                overdue_deals=overdue,
                draft_deals=int(r.draft or 0),
                total_portfolio=Decimal(str(r.portfolio)),
                overdue_pct=_overdue_pct(active, overdue),
                clients_count=int(r.clients_count or 0),
                payments_today=Decimal(str(r.payments_today)),
                payments_week=Decimal(str(r.payments_week)),
                payments_month=payments_month,
                cash_month=cash_month,
                deals_created_month=int(r.deals_created_month or 0),
                last_activity=r.last_activity,
            )
        )
    return items
