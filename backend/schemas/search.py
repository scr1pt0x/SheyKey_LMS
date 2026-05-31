import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from backend.models.payment import PaymentStatus


class SearchCaseBrief(BaseModel):
    case_id: uuid.UUID | None = None
    deal_id: uuid.UUID
    status: str | None = None
    total_debt: Decimal | None = None
    days_overdue: int | None = None
    sb_user_id: uuid.UUID | None = None
    deal_type: str
    deal_status: str
    deal_total: Decimal


class SearchClientHit(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    cases: list[SearchCaseBrief]


class GlobalSearchResponse(BaseModel):
    clients: list[dict]
    deals: list[dict]
    hits: list[SearchClientHit]
    query: str


class ScheduleBrief(BaseModel):
    id: uuid.UUID
    installment_number: int
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    status: PaymentStatus


class ClientDealBrief(BaseModel):
    deal_id: uuid.UUID
    deal_type: str
    deal_status: str
    deal_total: Decimal
    duration_months: int
    start_date: date | None
    product_description: str | None = None
    purchase_summary: str
    manager_id: uuid.UUID
    manager_name: str
    case_id: uuid.UUID | None = None
    case_status: str | None = None
    schedules: list[ScheduleBrief]


class ClientOverdueCaseBrief(BaseModel):
    case_id: uuid.UUID
    deal_id: uuid.UUID
    status: str
    total_debt: Decimal
    days_overdue: int
    sb_user_id: uuid.UUID | None


class ClientSearchProfile(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    manager_id: uuid.UUID
    manager_name: str
    overdue_cases: list[ClientOverdueCaseBrief]
    deals: list[ClientDealBrief]
