import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


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


class ManagerDashboardResponse(BaseModel):
    active_deals: int
    overdue_deals: int
    pending_deals: int
    draft_deals: int
    portfolio_active_total: Decimal
    payments_today: Decimal
    payments_week: Decimal
    payments_month: Decimal
    clients_kyc_pending: int
    deals_created_month: int = 0
    schedules_today: list[ScheduledPaymentBrief]
    schedules_week: list[ScheduledPaymentBrief]
    overdue_deals_list: list[DealBrief] = []
    pending_deals_list: list[DealBrief] = []


class ManagerStatsResponse(BaseModel):
    deals_created: int
    payments_collected: Decimal
    bonus_note: str = "Бонус рассчитывается руководителем в разделе «Прибыль»"
