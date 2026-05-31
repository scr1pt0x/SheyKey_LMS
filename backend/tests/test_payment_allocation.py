"""Tests for payment allocation across schedule lines."""
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from backend.models.payment import PaymentMethod, PaymentStatus
from backend.services.payment_allocation_service import (
    apply_amount_to_schedule,
    schedule_remaining,
)


def _schedule(
    amount: str,
    paid: str = "0",
    due: date = date(2026, 6, 5),
    num: int = 1,
    status: PaymentStatus = PaymentStatus.overdue,
):
    return SimpleNamespace(
        id=uuid4(),
        amount=Decimal(amount),
        paid_amount=Decimal(paid),
        due_date=due,
        installment_number=num,
        status=status,
    )


def test_schedule_remaining():
    s = _schedule("10000", "3000")
    assert schedule_remaining(s) == Decimal("7000")


def test_apply_amount_to_schedule_partial():
    s = _schedule("10000", "0")
    payment = apply_amount_to_schedule(
        s,
        Decimal("3000"),
        deal_id=uuid4(),
        paid_at=datetime.now(timezone.utc),
        method=PaymentMethod.cash,
        recorded_by=uuid4(),
        notes=None,
    )
    assert payment.amount == Decimal("3000")
    assert s.paid_amount == Decimal("3000")
    assert s.status == PaymentStatus.partial


def test_apply_amount_to_schedule_closes_line():
    s = _schedule("10000", "7000")
    apply_amount_to_schedule(
        s,
        Decimal("3000"),
        deal_id=uuid4(),
        paid_at=datetime.now(timezone.utc),
        method=PaymentMethod.cash,
        recorded_by=uuid4(),
        notes=None,
    )
    assert s.status == PaymentStatus.paid


def test_allocate_order_simulation():
    """Simulate allocation: 5000 across 3000 remaining + next lines."""
    s1 = _schedule("10000", "7000", due=date(2026, 6, 5), num=3)
    s2 = _schedule("10000", "0", due=date(2026, 7, 5), num=4)
    left = Decimal("5000")
    parts = []
    for s in [s1, s2]:
        if left <= 0:
            break
        rem = schedule_remaining(s)
        if rem <= 0:
            continue
        chunk = min(left, rem)
        apply_amount_to_schedule(
            s,
            chunk,
            deal_id=uuid4(),
            paid_at=datetime.now(timezone.utc),
            method=PaymentMethod.cash,
            recorded_by=uuid4(),
            notes=None,
        )
        parts.append(chunk)
        left -= chunk
    assert parts == [Decimal("3000"), Decimal("2000")]
    assert s1.status == PaymentStatus.paid
    assert s2.paid_amount == Decimal("2000")
    assert s2.status == PaymentStatus.partial
