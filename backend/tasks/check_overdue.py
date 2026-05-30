"""
Daily task: mark overdue payment schedules and deals.
Runs at 00:01 Moscow time.
"""
import asyncio
from datetime import date, datetime, timezone

from loguru import logger
from sqlalchemy import select, update

from backend.core.database import AsyncSessionLocal
from backend.models.deal import Deal, DealStatus
from backend.models.payment import PaymentSchedule, PaymentStatus
from backend.services.overdue_case_service import sync_overdue_case_for_deal
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.check_overdue.check_overdue_payments")
def check_overdue_payments() -> dict:
    return asyncio.run(_check_overdue_payments())


async def _check_overdue_payments() -> dict:
    today = datetime.now(timezone.utc).date()
    updated_schedules = 0
    updated_deals = 0

    async with AsyncSessionLocal() as db:
        # Mark pending schedules as overdue
        pending_overdue = await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.due_date < today)
            .where(PaymentSchedule.status == PaymentStatus.pending)
        )
        for schedule in pending_overdue.scalars().all():
            schedule.status = PaymentStatus.overdue
            updated_schedules += 1

        await db.flush()

        # Mark deals as overdue if they have any overdue schedules
        overdue_deal_ids_result = await db.execute(
            select(PaymentSchedule.deal_id)
            .where(PaymentSchedule.status == PaymentStatus.overdue)
            .distinct()
        )
        overdue_deal_ids = [row[0] for row in overdue_deal_ids_result.all()]
        synced_cases = 0

        if overdue_deal_ids:
            result = await db.execute(
                select(Deal)
                .where(Deal.id.in_(overdue_deal_ids))
                .where(Deal.status == DealStatus.active)
            )
            for deal in result.scalars().all():
                deal.status = DealStatus.overdue
                updated_deals += 1

            for deal_id in overdue_deal_ids:
                case, _ = await sync_overdue_case_for_deal(db, deal_id)
                if case:
                    synced_cases += 1

        await db.commit()

    logger.info(
        f"check_overdue: {updated_schedules} schedules marked overdue, "
        f"{updated_deals} deals marked overdue"
    )
    return {
        "updated_schedules": updated_schedules,
        "updated_deals": updated_deals,
        "synced_cases": synced_cases if overdue_deal_ids else 0,
    }
