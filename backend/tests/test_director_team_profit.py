"""Tests for director manager control and profit period deletion."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.models.profit_period import ProfitPeriodStatus
from backend.schemas.director import ManagerControlItem
from backend.services.manager_control_service import _overdue_pct


def test_manager_control_item_defaults():
    item = ManagerControlItem(
        user_id=uuid.uuid4(),
        name="Менеджер",
        active_deals=3,
        overdue_deals=1,
        total_portfolio=Decimal("100000"),
    )
    assert item.draft_deals == 0
    assert item.clients_count == 0
    assert item.overdue_pct == 0.0


def test_manager_control_item_full_metrics():
    item = ManagerControlItem(
        user_id=uuid.uuid4(),
        name="М1",
        active_deals=8,
        overdue_deals=2,
        draft_deals=1,
        total_portfolio=Decimal("500000"),
        overdue_pct=20.0,
        clients_count=12,
        payments_month=Decimal("75000"),
        deals_created_month=4,
    )
    assert item.active_deals == 8
    assert item.overdue_deals == 2
    assert item.total_portfolio == Decimal("500000")


def test_overdue_pct_zero_when_no_deals():
    assert _overdue_pct(0, 0) == 0.0


def test_overdue_pct_only_active():
    assert _overdue_pct(5, 0) == 0.0


def test_overdue_pct_mixed():
    assert _overdue_pct(3, 1) == 25.0


def test_overdue_pct_all_overdue():
    assert _overdue_pct(0, 4) == 100.0


@pytest.mark.asyncio
async def test_delete_period_rejects_approved():
    from backend.api.profit import delete_period

    period = MagicMock()
    period.status = ProfitPeriodStatus.approved
    db = AsyncMock()
    db.get = AsyncMock(return_value=period)

    with pytest.raises(HTTPException) as exc:
        await delete_period(uuid.uuid4(), MagicMock(), db, MagicMock())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_period_draft_success():
    from backend.api.profit import delete_period

    period_id = uuid.uuid4()
    period = MagicMock()
    period.status = ProfitPeriodStatus.draft
    period.id = period_id

    db = AsyncMock()
    db.get = AsyncMock(return_value=period)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    with patch("backend.api.profit._delete_period_distributions", new=AsyncMock()) as del_dist:
        result = await delete_period(period_id, MagicMock(), db, MagicMock())

    assert result["detail"] == "Черновик периода удалён"
    del_dist.assert_awaited_once_with(db, period_id)
    db.delete.assert_awaited_once_with(period)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_period_not_found():
    from backend.api.profit import delete_period

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await delete_period(uuid.uuid4(), MagicMock(), db, MagicMock())
    assert exc.value.status_code == 404
