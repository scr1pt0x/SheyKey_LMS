"""
Daily task: auto-transfer overdue deals to SB after N days (from system_settings).
Runs at 00:05 Moscow time.
"""
import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from backend.core.database import AsyncSessionLocal
from backend.models.deal import Deal, DealStatus
from backend.models.overdue import OverdueCase
from backend.models.payment import PaymentSchedule, PaymentStatus
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User, UserRole
from backend.services.push_service import notify_staff
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.auto_transfer_sb.auto_transfer_to_sb")
def auto_transfer_to_sb() -> dict:
    return asyncio.run(_auto_transfer_to_sb())


async def _auto_transfer_to_sb() -> dict:
    created_cases = 0
    async with AsyncSessionLocal() as db:
        # Get threshold from settings
        setting = (
            await db.execute(
                select(SystemSetting.value).where(SystemSetting.key == SettingKey.SB_THRESHOLD_DAYS)
            )
        ).scalar_one_or_none()
        threshold_days = int(setting) if setting is not None else 7

        today = datetime.now(timezone.utc).date()

        # Find all overdue deals
        overdue_deals = (
            await db.execute(select(Deal).where(Deal.status == DealStatus.overdue))
        ).scalars().all()

        for deal in overdue_deals:
            # Calculate days overdue (earliest overdue schedule)
            earliest_overdue = (
                await db.execute(
                    select(PaymentSchedule.due_date)
                    .where(PaymentSchedule.deal_id == deal.id)
                    .where(PaymentSchedule.status == PaymentStatus.overdue)
                    .order_by(PaymentSchedule.due_date)
                    .limit(1)
                )
            ).scalar_one_or_none()

            if not earliest_overdue:
                continue

            days_overdue = (today - earliest_overdue).days
            if days_overdue < threshold_days:
                continue

            # Check if case already exists
            existing_case = (
                await db.execute(
                    select(OverdueCase)
                    .where(OverdueCase.deal_id == deal.id)
                    .where(OverdueCase.status.notin_(["closed"]))
                )
            ).scalar_one_or_none()

            if existing_case:
                # Update days_overdue and total_debt
                total_debt = (
                    await db.execute(
                        select(
                            __import__("sqlalchemy").func.sum(
                                PaymentSchedule.amount - PaymentSchedule.paid_amount
                            )
                        )
                        .where(PaymentSchedule.deal_id == deal.id)
                        .where(PaymentSchedule.status.in_(["overdue", "partial"]))
                    )
                ).scalar_one() or 0

                existing_case.days_overdue = days_overdue
                existing_case.total_debt = total_debt
                continue

            # Calculate total debt
            total_debt = (
                await db.execute(
                    __import__("sqlalchemy").select(
                        __import__("sqlalchemy").func.sum(
                            PaymentSchedule.amount - PaymentSchedule.paid_amount
                        )
                    )
                    .where(PaymentSchedule.deal_id == deal.id)
                    .where(PaymentSchedule.status.in_(["overdue", "partial"]))
                )
            ).scalar_one() or 0

            case = OverdueCase(
                deal_id=deal.id,
                days_overdue=days_overdue,
                total_debt=total_debt,
            )
            db.add(case)
            await db.flush()
            created_cases += 1

            # Notify all directors about the new overdue case
            directors = (
                await db.execute(
                    select(User).where(User.role == UserRole.director).where(User.is_active == True)  # noqa
                )
            ).scalars().all()
            for director in directors:
                await notify_staff(
                    db=db,
                    user_id=director.id,
                    title="Новое дело в СБ",
                    body=f"Сделка просрочена {days_overdue} дн. · Долг: {total_debt} ₽",
                    entity_type="overdue_cases",
                    entity_id=str(case.id),
                    action_url=f"/sb/cases/{case.id}",
                )

        await db.commit()

    logger.info(f"auto_transfer_sb: {created_cases} new overdue cases created")
    return {"created_cases": created_cases}
