import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.models.payment import PaymentMethod


class PaymentCreate(BaseModel):
    schedule_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    paid_at: datetime
    method: PaymentMethod
    notes: str | None = None


class PaymentAllocateCreate(BaseModel):
    deal_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    paid_at: datetime
    method: PaymentMethod
    notes: str | None = None


class PaymentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    schedule_id: uuid.UUID
    deal_id: uuid.UUID
    amount: Decimal
    paid_at: datetime
    method: PaymentMethod
    receipt_url: str | None
    confirmed_by: uuid.UUID | None
    recorded_by: uuid.UUID
    notes: str | None
    created_at: datetime


class PaymentAllocateResponse(BaseModel):
    payments: list[PaymentResponse]
    total_applied: Decimal
    deal_id: uuid.UUID


class PresignedUrlRequest(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    doc_type: str
    file_name: str
    content_type: str = "application/octet-stream"


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str


class DocumentConfirmRequest(BaseModel):
    object_key: str
    entity_type: str
    entity_id: uuid.UUID
    doc_type: str
    file_name: str
    file_size: int | None = None


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    file_url: str
    doc_type: str
    uploaded_by: uuid.UUID
    file_name: str
    file_size: int | None
    created_at: datetime
