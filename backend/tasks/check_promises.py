"""
Daily task: check unfulfilled payment promises and alert SB staff via in-app + Web Push.
Runs at 09:00 Moscow time.
"""
import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from backend.core.database import AsyncSessionLocal
from backend.models.overdue import OverdueCase, PaymentPromise
from backend.models.user import User
from backend.services.push_service import notify_staff
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.check_promises.check_payment_promises")
def check_payment_promises() -> dict:
    return asyncio.run(_check_payment_promises())


async def _check_payment_promises() -> dict:
    today = datetime.now(timezone.utc).date()
    alerted = 0

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(PaymentPromise, OverdueCase)
            .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
            .where(PaymentPromise.promised_date <= today)
            .where(PaymentPromise.is_fulfilled == False)  # noqa
        )

        for promise, case in rows.all():
            if not case.sb_user_id:
                continue

            days_late = (today - promise.promised_date).days
            title = "Обещание платежа не выполнено"
            body = (
                f"Дело #{str(case.id)[:8]} · "
                f"Сумма: {promise.promised_amount} ₽ · "
                f"Просрочено на {days_late} дн."
            )

            try:
                await notify_staff(
                    db=db,
                    user_id=case.sb_user_id,
                    title=title,
                    body=body,
                    entity_type="overdue_cases",
                    entity_id=str(case.id),
                    action_url=f"/sb/cases/{case.id}",
                )
                alerted += 1
            except Exception as exc:
                logger.warning(f"Failed to notify SB user {case.sb_user_id}: {exc}")

        await db.commit()

    logger.info(f"check_promises: {alerted} notifications sent")
    return {"alerted": alerted}
