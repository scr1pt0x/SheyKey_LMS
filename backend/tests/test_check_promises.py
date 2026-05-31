"""Tests for payment promise notification messages."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from backend.services.promise_notification_service import build_promise_alert

CASE_ID = UUID("12345678-abcd-4000-8000-000000000001")


def test_build_promise_alert_on_promised_day():
    promised = date(2026, 6, 1)
    title, body = build_promise_alert(
        promised_date=promised,
        promised_amount=Decimal("10000"),
        case_id=CASE_ID,
        today=promised,
    )
    assert title == "Обещание платежа сегодня"
    assert "обещал сегодня оплатить" in body
    assert "10 000,00 ₽" in body
    assert "Просрочено" not in body


def test_build_promise_alert_overdue():
    promised = date(2026, 6, 1)
    title, body = build_promise_alert(
        promised_date=promised,
        promised_amount=Decimal("10000"),
        case_id=CASE_ID,
        today=date(2026, 6, 3),
    )
    assert title == "Обещание платежа не выполнено"
    assert "Просрочено на 2 дн." in body
