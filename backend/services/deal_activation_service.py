"""Activate a deal: active/overdue status, schedule marks, SB sync."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.redis_client import DASHBOARD_CACHE_PREFIX, cache_delete
from backend.models.deal import Deal, DealStatus
from backend.models.payment import PaymentSchedule, PaymentStatus


async def activate_deal(
    db: AsyncSession,
    deal: Deal,
    activated_by: uuid.UUID,
) -> DealStatus:
    """
    Transition deal to active (or overdue if backdated).
    Sets approved_by / approved_at. Caller commits and audits.
    """
    deal.status = DealStatus.active
    deal.approved_by = activated_by
    deal.approved_at = datetime.now(timezone.utc)

    today = datetime.now(timezone.utc).date()
    if deal.start_date and deal.start_date < today:
        overdue_result = await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.deal_id == deal.id)
            .where(PaymentSchedule.due_date < today)
            .where(PaymentSchedule.status == PaymentStatus.pending)
        )
        has_overdue = False
        for sched in overdue_result.scalars().all():
            sched.status = PaymentStatus.overdue
            has_overdue = True
        if has_overdue:
            deal.status = DealStatus.overdue

    if deal.status == DealStatus.overdue:
        from backend.services.overdue_case_service import sync_overdue_case_for_deal

        await sync_overdue_case_for_deal(db, deal.id)

    await cache_delete(f"{DASHBOARD_CACHE_PREFIX}main:v2")
    return deal.status
