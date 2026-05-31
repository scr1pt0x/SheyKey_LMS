"""Unit tests for payment schedule calculators."""
from datetime import date
from decimal import Decimal

import pytest

from backend.services.payment_calculator import (
    generate_ijara_schedule,
    generate_murabaha_schedule,
    generate_schedule,
)


class TestMurabaha:
    def test_basic(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("100000"),
            markup=Decimal("20000"),
            duration_months=12,
            start_date=date(2025, 1, 1),
        )
        assert len(schedules) == 12
        total = sum(s.amount for s in schedules)
        assert total == Decimal("120000")

    def test_monthly_amount(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("60000"),
            markup=Decimal("0"),
            duration_months=12,
            start_date=date(2025, 1, 1),
        )
        for s in schedules[:-1]:
            assert s.amount == Decimal("5000.00")

    def test_last_installment_rounding(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("100001"),
            markup=Decimal("0"),
            duration_months=3,
            start_date=date(2025, 1, 1),
        )
        total = sum(s.amount for s in schedules)
        assert total == Decimal("100001")

    def test_due_dates(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("12000"),
            markup=Decimal("0"),
            duration_months=3,
            start_date=date(2025, 1, 15),
        )
        assert schedules[0].due_date == date(2025, 2, 15)
        assert schedules[1].due_date == date(2025, 3, 15)
        assert schedules[2].due_date == date(2025, 4, 15)

    def test_installment_numbers(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("10000"),
            markup=Decimal("0"),
            duration_months=5,
            start_date=date(2025, 1, 1),
        )
        for i, s in enumerate(schedules, 1):
            assert s.installment_number == i

    def test_all_principal_type(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("10000"),
            markup=Decimal("2000"),
            duration_months=6,
            start_date=date(2025, 1, 1),
        )
        for s in schedules:
            assert s.installment_type == "principal"


class TestIjara:
    def test_basic(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("5000"),
            duration_months=12,
            start_date=date(2025, 1, 1),
        )
        assert len(schedules) == 12
        for s in schedules:
            assert s.amount == Decimal("5000.00")
            assert s.installment_type == "rent"

    def test_with_buyout(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("5000"),
            duration_months=12,
            start_date=date(2025, 1, 1),
            buyout_amount=Decimal("50000"),
        )
        assert len(schedules) == 13
        assert schedules[-1].installment_type == "buyout"
        assert schedules[-1].amount == Decimal("50000.00")
        assert schedules[-1].installment_number == 13

    def test_without_buyout(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("3000"),
            duration_months=6,
            start_date=date(2025, 3, 1),
            buyout_amount=None,
        )
        assert len(schedules) == 6

    def test_zero_buyout_not_added(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("5000"),
            duration_months=3,
            start_date=date(2025, 1, 1),
            buyout_amount=Decimal("0"),
        )
        assert len(schedules) == 3

    def test_due_dates_with_buyout(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("1000"),
            duration_months=2,
            start_date=date(2025, 1, 1),
            buyout_amount=Decimal("10000"),
        )
        assert schedules[0].due_date == date(2025, 2, 1)
        assert schedules[1].due_date == date(2025, 3, 1)
        assert schedules[2].due_date == date(2025, 4, 1)


class TestDealEndDate:
    def test_start_on_31st_plus_months_no_value_error(self):
        from dateutil.relativedelta import relativedelta

        start = date(2026, 5, 31)
        end = start + relativedelta(months=6)
        assert end == date(2026, 11, 30)


class TestGenerateDispatcher:
    def test_murabaha_dispatch(self):
        schedules = generate_schedule(
            "murabaha",
            {"principal": "100000", "markup": "10000", "duration_months": 12},
            date(2025, 1, 1),
        )
        assert len(schedules) == 12

    def test_ijara_dispatch(self):
        schedules = generate_schedule(
            "ijara",
            {"monthly_rent": "5000", "duration_months": 6},
            date(2025, 1, 1),
        )
        assert len(schedules) == 6

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown deal type"):
            generate_schedule("unknown", {}, date(2025, 1, 1))
