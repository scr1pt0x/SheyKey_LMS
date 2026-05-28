"""
Notification tasks: payment reminders via SMS.ru (3d and 1d before due date).
"""
import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.database import AsyncSessionLocal
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus
from backend.models.notification import NotificationLog, NotificationStatus, NotificationChannel
from backend.models.payment import PaymentSchedule, PaymentStatus
from backend.models.settings import SettingKey, SystemSetting
from backend.services.sms_service import send_sms
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.notifications.send_payment_reminders")
def send_payment_reminders(days_before: int = 3) -> dict:
    return asyncio.run(_send_payment_reminders(days_before))


async def _send_payment_reminders(days_before: int) -> dict:
    today = datetime.now(timezone.utc).date()
    target_date = today + timedelta(days=days_before)
    sent = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        template_setting = (
            await db.execute(
                select(SystemSetting.value).where(SystemSetting.key == SettingKey.NOTIFICATION_TEMPLATES)
            )
        ).scalar_one_or_none()

        templates = template_setting or {}
        template_key = "reminder_3d" if days_before == 3 else "reminder_1d"
        template = templates.get(
            template_key,
            "Уважаемый {name}, напоминаем о платеже {amount} ₽, ожидаемом {date}.",
        )

        rows = await db.execute(
            select(PaymentSchedule, Deal, Client)
            .join(Deal, PaymentSchedule.deal_id == Deal.id)
            .join(Client, Deal.client_id == Client.id)
            .where(PaymentSchedule.due_date == target_date)
            .where(PaymentSchedule.status == PaymentStatus.pending)
            .where(Deal.status == DealStatus.active)
        )

        for schedule, deal, client in rows.all():
            message = template.format(
                name=client.full_name.split()[0],
                amount=schedule.amount,
                date=schedule.due_date.strftime("%d.%m.%Y"),
            )

            log = NotificationLog(
                client_id=client.id,
                channel=NotificationChannel.sms,
                template=template_key,
                content=message,
                status=NotificationStatus.pending,
            )
            db.add(log)
            await db.flush()

            try:
                await send_sms(phone=client.phone, message=message)
                log.status = NotificationStatus.sent
                log.sent_at = datetime.now(timezone.utc)
                sent += 1
            except Exception as exc:
                log.status = NotificationStatus.failed
                log.error_message = str(exc)
                failed += 1
                logger.warning(f"SMS failed for client {client.id}: {exc}")

        await db.commit()

    logger.info(f"send_payment_reminders({days_before}d): {sent} sent, {failed} failed")
    return {"sent": sent, "failed": failed}
