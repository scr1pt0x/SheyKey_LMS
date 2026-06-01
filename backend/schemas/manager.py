import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from backend.models.payment import PaymentMethod


class ScheduledPaymentBrief(BaseModel):
    schedule_id: uuid.UUID
    deal_id: uuid.UUID
    client_id: uuid.UUID
    due_date: date
    amount: Decimal
    status: str


class DealBrief(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    type: str
    status: str
    total: Decimal


class Stage1OverdueBrief(BaseModel):
    case_id: uuid.UUID
    deal_id: uuid.UUID
    client_id: uuid.UUID
    type: str
    total: Decimal
    days_overdue: int
    total_debt: Decimal
    overdue_installments_count: int


class ManagerDashboardResponse(BaseModel):
    active_deals: int
    overdue_deals: int
    draft_deals: int
    portfolio_active_total: Decimal
    payments_today: Decimal
    payments_week: Decimal
    payments_month: Decimal
    deals_created_month: int = 0
    schedules_today: list[ScheduledPaymentBrief]
    schedules_week: list[ScheduledPaymentBrief]
    overdue_deals_list: list[DealBrief] = []
    stage1_overdue_cases: list[Stage1OverdueBrief] = []


class ManagerStatsResponse(BaseModel):
    deals_created: int
    payments_collected: Decimal
    bonus_note: str = "Бонус рассчитывается руководителем в разделе «Прибыль»"


class CashLedgerItem(BaseModel):
    id: str
    entry_type: Literal["installment", "manual", "expense"]
    amount: Decimal
    paid_at: datetime
    method: str
    description: str
    deal_id: uuid.UUID | None = None
    client_name: str | None = None


class ManagerCashResponse(BaseModel):
    items: list[CashLedgerItem]
    total: int
    limit: int
    offset: int
    total_today: Decimal
    total_month: Decimal
    total_all_time: Decimal


class ManagerCashManualCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    paid_at: datetime
    method: PaymentMethod
    description: str = Field(..., min_length=1, max_length=500)
    entry_kind: Literal["income", "expense"] = "income"
