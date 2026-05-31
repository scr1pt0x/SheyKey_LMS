"""
Daily task: check unfulfilled payment promises and alert SB staff via in-app + Web Push.
Runs at 09:00 Moscow time.
"""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select

from backend.core.database import AsyncSessionLocal
from backend.models.overdue import OverdueCase, PaymentPromise
from backend.services.promise_notification_service import build_promise_alert
from backend.services.push_service import notify_staff
from backend.tasks.celery_app import celery_app

MSK = ZoneInfo("Europe/Moscow")


@celery_app.task(name="backend.tasks.check_promises.check_payment_promises")
def check_payment_promises() -> dict:
    return asyncio.run(_check_payment_promises())


async def _check_payment_promises() -> dict:
    today = datetime.now(MSK).date()
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

            title, body = build_promise_alert(
                promised_date=promise.promised_date,
                promised_amount=promise.promised_amount,
                case_id=case.id,
                today=today,
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
