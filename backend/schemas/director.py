import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DirectorDashboardResponse(BaseModel):
    total_portfolio: Decimal
    active_deals: int
    overdue_deals: int
    closed_deals: int
    cash_flow_today: Decimal
    cash_flow_week: Decimal
    cash_flow_month: Decimal
    overdue_pct: float
    new_deals_month: int
    income_month: Decimal


class PortfolioByTypeItem(BaseModel):
    type: str
    count: int
    total_amount: Decimal
    pct: float


class IssuanceDynamicsItem(BaseModel):
    month: str
    count: int
    total_amount: Decimal


class TopDebtorItem(BaseModel):
    client_id: uuid.UUID
    client_name: str
    deal_id: uuid.UUID
    total_debt: Decimal
    days_overdue: int
    sb_status: str | None


class OverdueDealItem(BaseModel):
    deal_id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    manager_name: str
    deal_total: Decimal
    days_overdue: int


class SbPerformanceItem(BaseModel):
    sb_user_id: uuid.UUID
    sb_name: str
    cases_total: int
    cases_closed: int
    recovered_amount: Decimal


class SbPresenceItem(BaseModel):
    sb_user_id: uuid.UUID
    sb_name: str
    day_started_at: datetime | None
    last_seen_at: datetime | None
    is_online: bool


class ConversionFunnelResponse(BaseModel):
    draft: int
    active: int
    closed: int
    overdue: int


class ManagerControlItem(BaseModel):
    user_id: uuid.UUID
    name: str
    active_deals: int = 0
    overdue_deals: int = 0
    draft_deals: int = 0
    total_portfolio: Decimal = Decimal("0")
    overdue_pct: float = 0.0
    clients_count: int = 0
    payments_today: Decimal = Decimal("0")
    payments_week: Decimal = Decimal("0")
    payments_month: Decimal = Decimal("0")
    cash_month: Decimal = Decimal("0")
    deals_created_month: int = 0
    last_activity: datetime | None = None


class ReassignRequest(BaseModel):
    client_ids: list[uuid.UUID] = []
    deal_ids: list[uuid.UUID] = []
    new_manager_id: uuid.UUID


class AuditLogItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: uuid.UUID | None
    user_name: str | None = None
    action: str
    entity: str
    entity_id: uuid.UUID | None
    old_val: dict | None
    new_val: dict | None
    ip: str | None
    created_at: datetime


class SettingUpdate(BaseModel):
    value: dict | list | str | int | float
