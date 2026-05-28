"""
Central staff notification service.
Replaces telegram_service.py.

Two delivery channels:
1. staff_notifications table  — always written, shown as in-app bell icon
2. Web Push via pywebpush      — sent to all active push subscriptions for the user
"""
import json
import uuid
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.push_subscription import PushSubscription
from backend.models.staff_notification import StaffNotification


async def notify_staff(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    title: str,
    body: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str | uuid.UUID] = None,
    action_url: Optional[str] = None,
) -> None:
    """
    Insert a staff_notification record and fire Web Push to all subscribed devices.
    Call this from any place that previously called notify_user(telegram).
    Does NOT commit — caller is responsible for committing the session.
    """
    uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    eid = uuid.UUID(str(entity_id)) if entity_id and not isinstance(entity_id, uuid.UUID) else entity_id

    notification = StaffNotification(
        user_id=uid,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=eid,
        action_url=action_url,
    )
    db.add(notification)
    await db.flush()

    # Fire Web Push to all subscriptions for this user (best-effort, non-blocking)
    if settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY:
        subs_result = await db.execute(
            select(PushSubscription).where(PushSubscription.user_id == uid)
        )
        subscriptions = subs_result.scalars().all()
        for sub in subscriptions:
            await _send_web_push(
                endpoint=sub.endpoint,
                p256dh=sub.p256dh,
                auth=sub.auth,
                title=title,
                body=body,
                action_url=action_url,
            )


async def _send_web_push(
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
    action_url: Optional[str],
) -> None:
    """
    Send a Web Push notification via pywebpush.
    Silently logs errors rather than raising to avoid blocking the main flow.
    """
    try:
        from pywebpush import WebPushException, webpush

        payload = json.dumps({"title": title, "body": body, "action_url": action_url or "/"})
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.VAPID_SUBJECT,
            },
            content_encoding="aes128gcm",
        )
    except Exception as exc:
        logger.warning(f"Web Push failed for endpoint {endpoint[:40]}…: {exc}")
