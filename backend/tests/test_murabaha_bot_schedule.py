from datetime import date
from decimal import Decimal

from backend.services.murabaha_bot_schedule import generate_bot_payment_schedule
from backend.services.murabaha_tariff_service import compute_murabaha_quote, MurabahaTariff, ProductCategory
from backend.services.payment_calculator import generate_murabaha_schedule


def test_bot_schedule_matches_quote_case():
    q = compute_murabaha_quote(
        category=ProductCategory.consumer.value,
        amount=50_000,
        term_months=6,
        tariff=MurabahaTariff.NO_GUARANTOR.value,
        down_payment_pct=20,
    )
    advance = int(q.down_payment_amount)
    rows = generate_bot_payment_schedule(
        start_date=date(2025, 6, 15),
        term=6,
        payday=15,
        cost=62_000,
        advance=advance,
    )
    assert len(rows) == 6
    assert sum(r["amount"] for r in rows) == 62_000 - advance
    assert rows[0]["amount"] == 8267


def test_payment_calculator_uses_bot_logic():
    items = generate_murabaha_schedule(
        principal=Decimal("50000"),
        markup=Decimal("12000"),
        duration_months=6,
        start_date=date(2025, 6, 15),
        advance=Decimal("12400"),
        payday=15,
    )
    assert len(items) == 6
    assert sum(i.amount for i in items) == Decimal("49600")
