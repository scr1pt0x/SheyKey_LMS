import uuid
from datetime import datetime

from pydantic import BaseModel

from backend.models.notification import NotificationChannel, NotificationStatus


class SendNotificationRequest(BaseModel):
    client_id: uuid.UUID
    channel: NotificationChannel
    message: str
    template: str | None = None


class NotificationLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: uuid.UUID
    channel: NotificationChannel
    template: str | None
    content: str
    status: NotificationStatus
    sent_at: datetime | None
    sender_id: uuid.UUID | None
    error_message: str | None
    created_at: datetime
