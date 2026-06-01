"""
Daily task: sync overdue cases and notify directors for new SB-stage cases.
Runs at 00:05 Moscow time.
"""
import asyncio

from loguru import logger
from sqlalchemy import select

from backend.core.database import AsyncSessionLocal
from backend.models.user import User, UserRole
from backend.services.debt_collection_stage_service import load_debt_stage_settings
from backend.services.overdue_case_service import sync_all_overdue_deals
from backend.services.push_service import notify_staff
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.auto_transfer_sb.auto_transfer_to_sb")
def auto_transfer_to_sb() -> dict:
    return asyncio.run(_auto_transfer_to_sb())


async def _auto_transfer_to_sb() -> dict:
    notified = 0
    async with AsyncSessionLocal() as db:
        stage_settings = await load_debt_stage_settings(db)
        threshold_days = stage_settings.stage_2_days

        synced, created_cases = await sync_all_overdue_deals(db)

        directors = (
            await db.execute(
                select(User).where(User.role == UserRole.director).where(User.is_active == True)  # noqa
            )
        ).scalars().all()

        for case in created_cases:
            if case.collection_stage < 2:
                continue
            if case.days_overdue < threshold_days:
                continue
            for director in directors:
                await notify_staff(
                    db=db,
                    user_id=director.id,
                    title="Новое дело в СБ",
                    body=(
                        f"Этап {case.collection_stage}: просрочка {case.days_overdue} дн. "
                        f"· Долг: {case.total_debt} ₽"
                    ),
                    entity_type="overdue_cases",
                    entity_id=str(case.id),
                    action_url=f"/sb/cases/{case.id}",
                )
                notified += 1

        await db.commit()

    logger.info(f"auto_transfer_sb: synced={synced}, new_cases={len(created_cases)}, notifications={notified}")
    return {"synced_cases": synced, "created_cases": len(created_cases), "notifications_sent": notified}
