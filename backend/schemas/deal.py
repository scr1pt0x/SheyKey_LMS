import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from backend.models.deal import DealStatus, DealType
from backend.models.payment import PaymentStatus


class MurabahaParams(BaseModel):
    principal: Decimal = Field(..., gt=0)
    markup: Decimal = Field(..., ge=0)
    duration_months: int = Field(..., ge=1, le=360)
    start_date: date


class IjaraParams(BaseModel):
    monthly_rent: Decimal = Field(..., gt=0)
    duration_months: int = Field(..., ge=1, le=360)
    start_date: date
    buyout_amount: Decimal | None = Field(None, ge=0)


class DealCreate(BaseModel):
    client_id: uuid.UUID
    type: DealType
    murabaha: MurabahaParams | None = None
    ijara: IjaraParams | None = None

    @model_validator(mode="after")
    def validate_params(self) -> "DealCreate":
        if self.type == DealType.murabaha and self.murabaha is None:
            raise ValueError("murabaha params are required for Murabaha deal")
        if self.type == DealType.ijara and self.ijara is None:
            raise ValueError("ijara params are required for Ijara deal")
        return self


class DealUpdate(BaseModel):
    murabaha: MurabahaParams | None = None
    ijara: IjaraParams | None = None


class ScheduleItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    installment_number: int
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    status: PaymentStatus
    installment_type: str


class DealResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: uuid.UUID
    manager_id: uuid.UUID
    type: DealType
    status: DealStatus
    principal: Decimal
    markup: Decimal
    total: Decimal
    duration_months: int
    start_date: date | None
    end_date: date | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_comment: str | None
    created_at: datetime
    updated_at: datetime
    payment_schedules: list[ScheduleItemResponse] = []


class DealListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: uuid.UUID
    manager_id: uuid.UUID
    type: DealType
    status: DealStatus
    total: Decimal
    duration_months: int
    start_date: date | None
    created_at: datetime


class ApproveRequest(BaseModel):
    comment: str | None = None


class RejectRequest(BaseModel):
    comment: str = Field(..., min_length=3)


class RestructureRequest(BaseModel):
    reason: str = Field(..., min_length=10)
    new_schedule: list[dict] | None = None
