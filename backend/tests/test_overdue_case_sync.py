"""Tests for overdue case debt recalculation after payments."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.models.payment import PaymentStatus
from backend.services.overdue_case_service import (
    _schedule_outstanding,
    schedule_counts_toward_sb_debt,
)


def _schedule(
    amount: str,
    paid: str,
    status: PaymentStatus,
    due: date,
):
    return SimpleNamespace(
        amount=Decimal(amount),
        paid_amount=Decimal(paid),
        status=status,
        due_date=due,
    )


TODAY = date(2026, 5, 31)


def test_outstanding_on_partial_line():
    s = _schedule("10000", "7000", PaymentStatus.partial, date(2026, 4, 5))
    assert _schedule_outstanding(s) == Decimal("3000")


def test_outstanding_zero_when_paid():
    s = _schedule("10000", "10000", PaymentStatus.paid, date(2026, 4, 5))
    assert _schedule_outstanding(s) == Decimal("0")


def test_future_partial_not_sb_debt():
    """Partial prepayment on a future installment (e.g. №3 due 05.06) is not overdue debt."""
    s = _schedule("10000", "7000", PaymentStatus.partial, date(2026, 6, 5))
    assert not schedule_counts_toward_sb_debt(s, TODAY)


def test_past_due_partial_is_sb_debt():
    s = _schedule("10000", "7000", PaymentStatus.partial, date(2026, 5, 1))
    assert schedule_counts_toward_sb_debt(s, TODAY)


def test_overdue_status_counts_even_if_due_today():
    s = _schedule("10000", "5000", PaymentStatus.overdue, date(2026, 5, 31))
    assert schedule_counts_toward_sb_debt(s, TODAY)


def test_pending_past_due_counts():
    s = _schedule("10000", "0", PaymentStatus.pending, date(2026, 5, 1))
    assert schedule_counts_toward_sb_debt(s, TODAY)


def test_future_pending_not_sb_debt():
    s = _schedule("10000", "0", PaymentStatus.pending, date(2026, 6, 5))
    assert not schedule_counts_toward_sb_debt(s, TODAY)


def test_sb_debt_sum_excludes_future_partial():
    lines = [
        _schedule("10000", "7000", PaymentStatus.partial, date(2026, 6, 5)),
        _schedule("20000", "20000", PaymentStatus.paid, date(2026, 4, 5)),
    ]
    total = sum(
        _schedule_outstanding(s)
        for s in lines
        if schedule_counts_toward_sb_debt(s, TODAY)
    )
    assert total == Decimal("0")


def test_sb_debt_sum_includes_past_due_partial_only():
    lines = [
        _schedule("10000", "7000", PaymentStatus.partial, date(2026, 6, 5)),
        _schedule("20000", "17000", PaymentStatus.partial, date(2026, 5, 1)),
    ]
    total = sum(
        _schedule_outstanding(s)
        for s in lines
        if schedule_counts_toward_sb_debt(s, TODAY)
    )
    assert total == Decimal("3000")
