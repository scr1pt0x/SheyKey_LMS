"""Sync overdue_cases with deal payment schedule state."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.deal import Deal, DealStatus
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.payment import PaymentSchedule, PaymentStatus


async def sync_overdue_case_for_deal(
    db: AsyncSession, deal_id: uuid.UUID
) -> tuple[OverdueCase | None, bool]:
    """
    Create or update an open overdue case when the deal has overdue/partial schedules.
    Returns None if there is no overdue debt to track.
    """
    deal = await db.get(Deal, deal_id)
    if not deal:
        return None, False

    today = datetime.now(timezone.utc).date()

    overdue_schedules = (
        await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.deal_id == deal_id)
            .where(PaymentSchedule.status.in_([PaymentStatus.overdue, PaymentStatus.partial]))
        )
    ).scalars().all()

    if not overdue_schedules:
        if deal.status == DealStatus.overdue:
            deal.status = DealStatus.active
        return None, False

    earliest_due = min(s.due_date for s in overdue_schedules)
    days_overdue = max(0, (today - earliest_due).days)
    total_debt = sum(
        float(s.amount) - float(s.paid_amount or 0) for s in overdue_schedules
    )

    if deal.status in (DealStatus.active, DealStatus.pending):
        deal.status = DealStatus.overdue
    elif deal.status not in (DealStatus.overdue, DealStatus.closed):
        deal.status = DealStatus.overdue

    existing = (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.deal_id == deal_id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
        )
    ).scalar_one_or_none()

    if existing:
        existing.days_overdue = days_overdue
        existing.total_debt = total_debt
        await db.flush()
        return existing, False

    case = OverdueCase(
        deal_id=deal_id,
        days_overdue=days_overdue,
        total_debt=total_debt,
        status=OverdueCaseStatus.new,
    )
    db.add(case)
    await db.flush()
    return case, True


async def sync_all_overdue_deals(db: AsyncSession) -> tuple[int, list[OverdueCase]]:
    """Sync cases for every deal that has overdue schedules. Returns (total synced, newly created)."""
    deal_ids_result = await db.execute(
        select(PaymentSchedule.deal_id)
        .where(PaymentSchedule.status.in_([PaymentStatus.overdue, PaymentStatus.partial]))
        .distinct()
    )
    synced = 0
    created_cases: list[OverdueCase] = []
    for (deal_id,) in deal_ids_result.all():
        case, is_new = await sync_overdue_case_for_deal(db, deal_id)
        if case:
            synced += 1
            if is_new:
                created_cases.append(case)
    return synced, created_cases


async def ensure_missing_overdue_cases(db: AsyncSession) -> int:
    """
    Create overdue_cases for deals that have overdue schedules but no open case.
    Used when loading SB/director views so legacy deals appear without manual sync.
    """
    open_case_exists = (
        select(OverdueCase.id)
        .where(OverdueCase.deal_id == PaymentSchedule.deal_id)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
    )
    missing_deals = (
        await db.execute(
            select(PaymentSchedule.deal_id)
            .where(
                PaymentSchedule.status.in_(
                    [PaymentStatus.overdue, PaymentStatus.partial]
                )
            )
            .where(~exists(open_case_exists))
            .distinct()
        )
    ).scalars().all()

    created = 0
    for deal_id in missing_deals:
        _, is_new = await sync_overdue_case_for_deal(db, deal_id)
        if is_new:
            created += 1
    if created:
        await db.flush()
    return created
