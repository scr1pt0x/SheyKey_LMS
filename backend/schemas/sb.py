import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.models.overdue import ContactType, OverdueCaseStatus
from backend.models.restructuring import RestructuringStatus


class OverdueCaseResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    sb_user_id: uuid.UUID | None
    status: OverdueCaseStatus
    assigned_at: datetime | None
    closed_at: datetime | None
    total_debt: Decimal
    days_overdue: int
    created_at: datetime
    updated_at: datetime


class AssignCaseRequest(BaseModel):
    sb_user_id: uuid.UUID


class CaseStatusUpdate(BaseModel):
    status: OverdueCaseStatus


class ContactLogCreate(BaseModel):
    type: ContactType
    result: str = Field(..., min_length=1)
    next_action: str | None = None
    next_action_date: date | None = None


class ContactLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    case_id: uuid.UUID
    sb_user_id: uuid.UUID
    type: ContactType
    result: str
    next_action: str | None
    next_action_date: date | None
    created_at: datetime


class PaymentPromiseCreate(BaseModel):
    promised_date: date
    promised_amount: Decimal = Field(..., gt=0)


class PaymentPromiseResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    case_id: uuid.UUID
    promised_date: date
    promised_amount: Decimal
    is_fulfilled: bool
    created_at: datetime


class RestructuringCreate(BaseModel):
    reason: str = Field(..., min_length=10)
    new_schedule: list[dict] | None = None


class RestructuringResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    deal_id: uuid.UUID
    case_id: uuid.UUID | None
    initiated_by: uuid.UUID
    reason: str
    new_schedule: list | None
    status: RestructuringStatus
    approved_by: uuid.UUID | None
    decision_comment: str | None
    decided_at: datetime | None
    created_at: datetime


class SbDashboardResponse(BaseModel):
    my_cases_new: int
    my_cases_in_progress: int
    my_cases_agreed: int
    my_cases_closed: int
    promises_today: int
    promises_this_week: int
    recovered_this_month: Decimal
    red_zone_cases: int
