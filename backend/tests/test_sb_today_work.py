"""Unit tests for SB today work schemas."""
from decimal import Decimal
from uuid import uuid4

from backend.schemas.sb import SbTodayWorkItem, SbTodayWorkResponse


def test_sb_today_work_item():
    item = SbTodayWorkItem(
        case_id=uuid4(),
        deal_id=uuid4(),
        total_debt=Decimal("20000"),
        days_overdue=55,
        status="new",
    )
    assert item.status == "new"


def test_sb_today_work_response_empty():
    resp = SbTodayWorkResponse(
        red_zone_cases=[],
        promises_today=[],
        promises_overdue=[],
        unassigned_top=[],
    )
    assert len(resp.unassigned_top) == 0
