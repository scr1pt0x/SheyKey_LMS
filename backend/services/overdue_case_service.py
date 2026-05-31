"""Sync overdue_cases with deal payment schedule state."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.deal import Deal, DealStatus
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.payment import PaymentSchedule, PaymentStatus

_UNPAID_STATUSES = (
    PaymentStatus.pending,
    PaymentStatus.overdue,
    PaymentStatus.partial,
)


def _schedule_outstanding(schedule: PaymentSchedule) -> Decimal:
    return Decimal(str(schedule.amount)) - Decimal(str(schedule.paid_amount or 0))


def schedule_counts_toward_sb_debt(schedule: PaymentSchedule, today: date) -> bool:
    """True if this schedule line contributes to SB overdue debt (not future prepayments)."""
    if _schedule_outstanding(schedule) <= 0:
        return False
    if schedule.status == PaymentStatus.overdue:
        return True
    if schedule.due_date < today:
        return schedule.status in (PaymentStatus.pending, PaymentStatus.partial)
    return False


async def _load_open_case(db: AsyncSession, deal_id: uuid.UUID) -> OverdueCase | None:
    return (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.deal_id == deal_id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
        )
    ).scalar_one_or_none()


async def _load_sb_debt_lines(
    db: AsyncSession, deal_id: uuid.UUID, today: date
) -> list[PaymentSchedule]:
    rows = await db.execute(
        select(PaymentSchedule)
        .where(PaymentSchedule.deal_id == deal_id)
        .where(PaymentSchedule.status.in_(_UNPAID_STATUSES))
    )
    return [
        s for s in rows.scalars().all() if schedule_counts_toward_sb_debt(s, today)
    ]


async def _deal_has_sb_overdue_outstanding(
    db: AsyncSession, deal_id: uuid.UUID, today: date
) -> bool:
    lines = await _load_sb_debt_lines(db, deal_id, today)
    return len(lines) > 0


async def _close_open_case(
    db: AsyncSession, case: OverdueCase, deal: Deal, today: date
) -> OverdueCase:
    now = datetime.now(timezone.utc)
    case.status = OverdueCaseStatus.closed
    case.closed_at = now
    case.total_debt = 0
    case.days_overdue = 0
    if not await _deal_has_sb_overdue_outstanding(db, deal.id, today):
        if deal.status == DealStatus.overdue:
            deal.status = DealStatus.active
    await db.flush()
    return case


async def sync_overdue_case_for_deal(
    db: AsyncSession, deal_id: uuid.UUID
) -> tuple[OverdueCase | None, bool]:
    """
    Create or update an open overdue case when the deal has past-due debt.
    Closes the open case when overdue debt is cleared. Returns None if nothing to track.
    """
    deal = await db.get(Deal, deal_id)
    if not deal:
        return None, False

    today = datetime.now(timezone.utc).date()
    existing = await _load_open_case(db, deal_id)
    sb_debt_lines = await _load_sb_debt_lines(db, deal_id, today)

    if not sb_debt_lines:
        if existing:
            await _close_open_case(db, existing, deal, today)
        elif deal.status == DealStatus.overdue:
            deal.status = DealStatus.active
            await db.flush()
        return None, False

    earliest_due = min(s.due_date for s in sb_debt_lines)
    days_overdue = max(0, (today - earliest_due).days)
    total_debt = float(sum(_schedule_outstanding(s) for s in sb_debt_lines))

    if total_debt <= 0:
        if existing:
            await _close_open_case(db, existing, deal, today)
        return None, False

    if deal.status == DealStatus.active:
        deal.status = DealStatus.overdue
    elif deal.status not in (DealStatus.overdue, DealStatus.closed):
        deal.status = DealStatus.overdue

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


async def refresh_overdue_case_after_payment(
    db: AsyncSession, deal_id: uuid.UUID
) -> OverdueCase | None:
    """Recalculate debt and close the SB case when overdue balance is paid off."""
    case, _ = await sync_overdue_case_for_deal(db, deal_id)
    return case


async def refresh_open_cases_for_deals(
    db: AsyncSession, deal_ids: list[uuid.UUID]
) -> None:
    """Recalculate SB debt for a set of deals (e.g. current list page)."""
    for deal_id in deal_ids:
        await sync_overdue_case_for_deal(db, deal_id)


async def _deal_ids_with_sb_overdue_debt(db: AsyncSession, today: date) -> set[uuid.UUID]:
    rows = await db.execute(
        select(PaymentSchedule)
        .where(PaymentSchedule.status.in_(_UNPAID_STATUSES))
    )
    deal_ids: set[uuid.UUID] = set()
    for schedule in rows.scalars().all():
        if schedule_counts_toward_sb_debt(schedule, today):
            deal_ids.add(schedule.deal_id)
    return deal_ids


async def sync_all_overdue_deals(db: AsyncSession) -> tuple[int, list[OverdueCase]]:
    """Sync cases for every deal that has past-due debt. Returns (total synced, newly created)."""
    today = datetime.now(timezone.utc).date()
    deal_ids = await _deal_ids_with_sb_overdue_debt(db, today)
    synced = 0
    created_cases: list[OverdueCase] = []
    for deal_id in deal_ids:
        case, is_new = await sync_overdue_case_for_deal(db, deal_id)
        if case:
            synced += 1
            if is_new:
                created_cases.append(case)
    return synced, created_cases


async def ensure_missing_overdue_cases(db: AsyncSession) -> int:
    """
    Create overdue_cases for deals with past-due debt but no open case.
    Used when loading SB/director views so legacy deals appear without manual sync.
    """
    today = datetime.now(timezone.utc).date()
    deal_ids_with_debt = await _deal_ids_with_sb_overdue_debt(db, today)

    created = 0
    for deal_id in deal_ids_with_debt:
        if await _load_open_case(db, deal_id):
            continue
        _, is_new = await sync_overdue_case_for_deal(db, deal_id)
        if is_new:
            created += 1
    if created:
        await db.flush()
    return created
