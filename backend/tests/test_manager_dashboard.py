"""Unit tests for manager dashboard schema and access patterns."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from backend.schemas.manager import ManagerDashboardResponse, ScheduledPaymentBrief


def test_manager_dashboard_response_defaults():
    data = ManagerDashboardResponse(
        active_deals=1,
        overdue_deals=0,
        draft_deals=1,
        portfolio_active_total=Decimal("100000"),
        payments_today=Decimal("0"),
        payments_week=Decimal("5000"),
        payments_month=Decimal("5000"),
        schedules_today=[],
        schedules_week=[],
    )
    assert data.deals_created_month == 0
    assert data.overdue_deals_list == []


def test_scheduled_payment_brief():
    item = ScheduledPaymentBrief(
        schedule_id=uuid4(),
        deal_id=uuid4(),
        client_id=uuid4(),
        due_date=date(2026, 5, 30),
        amount=Decimal("10000"),
        status="pending",
    )
    assert item.status == "pending"
