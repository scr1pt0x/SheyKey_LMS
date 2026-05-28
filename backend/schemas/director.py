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


class SbPerformanceItem(BaseModel):
    sb_user_id: uuid.UUID
    sb_name: str
    cases_total: int
    cases_closed: int
    recovered_amount: Decimal


class ConversionFunnelResponse(BaseModel):
    draft: int
    pending: int
    active: int
    closed: int
    overdue: int


class ManagerPortfolioItem(BaseModel):
    manager_id: uuid.UUID
    manager_name: str
    active_deals: int
    overdue_deals: int
    total_portfolio: Decimal
    last_activity: datetime | None


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


class ApprovalDecision(BaseModel):
    comment: str = Field(default="")


class RejectDecision(BaseModel):
    comment: str = Field(..., min_length=3)
