import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.dependencies import get_current_user, require_role
from backend.models.client import Client
from backend.models.notification import NotificationChannel, NotificationLog, NotificationStatus
from backend.models.push_subscription import PushSubscription
from backend.models.settings import SettingKey, SystemSetting
from backend.models.staff_notification import StaffNotification
from backend.models.user import User
from backend.schemas.common import PaginatedResponse
from backend.schemas.notification import NotificationLogResponse, SendNotificationRequest
from backend.services.sms_service import send_sms

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class StaffNotificationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    body: str
    is_read: bool
    entity_type: str | None
    entity_id: uuid.UUID | None
    action_url: str | None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict  # { p256dh: str, auth: str }


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


# ─── In-app inbox endpoints ───────────────────────────────────────────────────

@router.get("/inbox", response_model=PaginatedResponse[StaffNotificationResponse])
async def get_inbox(
    is_read: bool | None = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[StaffNotificationResponse]:
    query = select(StaffNotification).where(StaffNotification.user_id == current_user.id)
    if is_read is not None:
        query = query.where(StaffNotification.is_read == is_read)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(
        query.order_by(StaffNotification.created_at.desc()).limit(limit).offset(offset)
    )
    items = rows.scalars().all()
    return PaginatedResponse(
        items=[StaffNotificationResponse.model_validate(n) for n in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/inbox/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> UnreadCountResponse:
    count = (
        await db.execute(
            select(func.count())
            .where(StaffNotification.user_id == current_user.id)
            .where(StaffNotification.is_read == False)  # noqa
        )
    ).scalar_one()
    return UnreadCountResponse(count=count)


@router.post("/inbox/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    result = await db.execute(
        select(StaffNotification).where(
            StaffNotification.id == notification_id,
            StaffNotification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    notif.is_read = True
    await db.commit()
    return {"detail": "ok"}


@router.post("/inbox/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    await db.execute(
        update(StaffNotification)
        .where(StaffNotification.user_id == current_user.id)
        .where(StaffNotification.is_read == False)  # noqa
        .values(is_read=True)
    )
    await db.commit()
    return {"detail": "all read"}


# ─── Web Push endpoints ───────────────────────────────────────────────────────

@router.get("/vapid-public-key")
async def get_vapid_public_key() -> dict:
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@router.post("/push-subscribe")
async def subscribe_push(
    body: PushSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    endpoint = body.endpoint
    p256dh = body.keys.get("p256dh", "")
    auth_key = body.keys.get("auth", "")

    if not p256dh or not auth_key:
        raise HTTPException(status_code=400, detail="keys.p256dh and keys.auth are required")

    existing = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == current_user.id,
                PushSubscription.endpoint == endpoint,
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.p256dh = p256dh
        existing.auth = auth_key
    else:
        db.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth_key,
            )
        )
    await db.commit()
    return {"detail": "subscribed"}


@router.delete("/push-subscribe")
async def unsubscribe_push(
    body: PushUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    existing = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == current_user.id,
                PushSubscription.endpoint == body.endpoint,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
    return {"detail": "unsubscribed"}


# ─── SMS to client (manual send) ─────────────────────────────────────────────

@router.post("/send")
async def send_notification(
    body: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    client = await db.get(Client, body.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    log = NotificationLog(
        client_id=body.client_id,
        channel=body.channel,
        template=body.template,
        content=body.message,
        status=NotificationStatus.pending,
        sender_id=current_user.id,
    )
    db.add(log)
    await db.flush()

    error_msg: str | None = None
    try:
        if body.channel == NotificationChannel.sms:
            await send_sms(phone=client.phone, message=body.message)
        else:
            raise HTTPException(
                status_code=400,
                detail="Telegram-уведомления клиентам не поддерживаются. Используйте SMS.",
            )
        log.status = NotificationStatus.sent
        log.sent_at = datetime.now(timezone.utc)
    except Exception as exc:
        error_msg = str(exc)
        log.status = NotificationStatus.failed
        log.error_message = error_msg

    await db.commit()

    if error_msg:
        raise HTTPException(status_code=502, detail=f"Ошибка отправки: {error_msg}")
    return {"detail": "Уведомление отправлено"}


@router.get("/client/{client_id}", response_model=PaginatedResponse[NotificationLogResponse])
async def client_notifications(
    client_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[NotificationLogResponse]:
    total = (
        await db.execute(
            select(func.count()).where(NotificationLog.client_id == client_id)
        )
    ).scalar_one()
    rows = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.client_id == client_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = rows.scalars().all()
    return PaginatedResponse(
        items=[NotificationLogResponse.model_validate(n) for n in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/templates")
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> dict:
    setting = (
        await db.execute(
            select(SystemSetting.value).where(SystemSetting.key == SettingKey.NOTIFICATION_TEMPLATES)
        )
    ).scalar_one_or_none()
    return setting or {}
