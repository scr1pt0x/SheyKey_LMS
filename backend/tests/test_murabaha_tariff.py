from decimal import Decimal

import pytest

from backend.services.murabaha_tariff_service import (
    MurabahaRateSettings,
    MurabahaTariff,
    ProductCategory,
    allowed_tariffs_for_amount,
    compute_murabaha_quote,
    min_down_payment_pct,
    pick_default_tariff,
    rate_per_month,
    validate_murabaha_deal,
)


def test_consumer_rate_with_and_without_down():
    rates = MurabahaRateSettings()
    assert rate_per_month(ProductCategory.consumer.value, MurabahaTariff.NO_DOWNPAYMENT.value, rates) == Decimal(
        "0.05"
    )
    assert rate_per_month(ProductCategory.consumer.value, MurabahaTariff.NO_GUARANTOR.value, rates) == Decimal(
        "0.04"
    )


def test_auto_only_with_down_tariff():
    assert MurabahaTariff.NO_DOWNPAYMENT.value not in allowed_tariffs_for_amount(
        ProductCategory.auto.value, 300_000
    )
    assert rate_per_month(ProductCategory.auto.value, MurabahaTariff.ONE_GUARANTOR.value) == Decimal("0.033")


def test_min_down_pct_by_term():
    assert min_down_payment_pct(ProductCategory.consumer.value, 6, MurabahaTariff.NO_GUARANTOR.value) == 20
    assert min_down_payment_pct(ProductCategory.consumer.value, 7, MurabahaTariff.NO_GUARANTOR.value) == 25
    assert min_down_payment_pct(ProductCategory.consumer.value, 6, MurabahaTariff.NO_DOWNPAYMENT.value) == 0


def test_quote_consumer_50k_6m_no_guarantor_20pct():
    q = compute_murabaha_quote(
        category=ProductCategory.consumer.value,
        amount=50_000,
        term_months=6,
        tariff=MurabahaTariff.NO_GUARANTOR.value,
        down_payment_pct=20,
    )
    assert q.markup == Decimal("12000")
    assert q.total == Decimal("62000")
    assert q.down_payment_amount == Decimal("12400")
    assert q.financed_amount == Decimal("49600")
    assert q.monthly_payment == Decimal("8267")


def test_quote_without_down_5pct():
    q = compute_murabaha_quote(
        category=ProductCategory.consumer.value,
        amount=50_000,
        term_months=6,
        tariff=MurabahaTariff.NO_DOWNPAYMENT.value,
        down_payment_pct=0,
    )
    assert q.markup == Decimal("15000")
    assert q.monthly_payment == Decimal("10834")


def test_validate_accepts_matching_markup():
    q = validate_murabaha_deal(
        category=ProductCategory.consumer.value,
        amount=Decimal("50000"),
        term_months=6,
        tariff=MurabahaTariff.NO_GUARANTOR.value,
        down_payment_pct=20,
        principal=Decimal("50000"),
        markup=Decimal("12000"),
    )
    assert q.markup == Decimal("12000")


def test_validate_rejects_wrong_markup():
    with pytest.raises(ValueError, match="Наценка"):
        validate_murabaha_deal(
            category=ProductCategory.consumer.value,
            amount=Decimal("50000"),
            term_months=6,
            tariff=MurabahaTariff.NO_GUARANTOR.value,
            down_payment_pct=20,
            principal=Decimal("50000"),
            markup=Decimal("10000"),
        )


def test_pick_default_tariff():
    assert pick_default_tariff(ProductCategory.consumer.value, 50_000) == MurabahaTariff.ONE_GUARANTOR.value
