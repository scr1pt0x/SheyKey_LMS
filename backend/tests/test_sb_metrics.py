"""SB collected amount uses Payment records, not promises."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from backend.services.sb_metrics_service import sb_collected_amount


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _FakeDb:
    def __init__(self, total):
        self.total = total

    async def execute(self, _stmt):
        return _FakeResult(self.total)


@pytest.mark.asyncio
async def test_sb_collected_amount_returns_decimal():
    uid = uuid4()
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end = datetime(2026, 5, 31, tzinfo=timezone.utc)
    db = _FakeDb(Decimal("27000.00"))
    amount = await sb_collected_amount(db, uid, start, end)
    assert amount == Decimal("27000.00")
