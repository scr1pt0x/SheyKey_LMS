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
    def test_basic_with_advance(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("50000"),
            markup=Decimal("12000"),
            duration_months=6,
            start_date=date(2025, 6, 15),
            advance=Decimal("12400"),
            payday=15,
        )
        assert len(schedules) == 6
        total = sum(s.amount for s in schedules)
        assert total == Decimal("49600")

    def test_no_advance(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("100000"),
            markup=Decimal("20000"),
            duration_months=12,
            start_date=date(2025, 1, 1),
            advance=Decimal("0"),
            payday=1,
        )
        assert len(schedules) == 12
        total = sum(s.amount for s in schedules)
        assert total == Decimal("120000")

    def test_due_dates_payday(self):
        schedules = generate_murabaha_schedule(
            principal=Decimal("12000"),
            markup=Decimal("0"),
            duration_months=3,
            start_date=date(2025, 1, 15),
            advance=Decimal("0"),
            payday=15,
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
            monthly_rent=Decimal("10000"),
            duration_months=12,
            start_date=date(2025, 1, 1),
        )
        assert len(schedules) == 12
        assert sum(s.amount for s in schedules) == Decimal("120000")

    def test_with_buyout(self):
        schedules = generate_ijara_schedule(
            monthly_rent=Decimal("5000"),
            duration_months=6,
            start_date=date(2025, 1, 1),
            buyout_amount=Decimal("50000"),
        )
        assert len(schedules) == 7
        assert schedules[-1].amount == Decimal("50000")
        assert schedules[-1].installment_type == "buyout"


class TestDispatcher:
    def test_murabaha_dispatcher(self):
        schedules = generate_schedule(
            "murabaha",
            {
                "principal": "50000",
                "markup": "12000",
                "duration_months": 6,
                "down_payment_amount": "12400",
                "payday": 15,
            },
            date(2025, 6, 15),
        )
        assert len(schedules) == 6

    def test_ijara_dispatcher(self):
        schedules = generate_schedule(
            "ijara",
            {"monthly_rent": "10000", "duration_months": 3},
            date(2025, 1, 1),
        )
        assert len(schedules) == 3

    def test_unknown_type(self):
        with pytest.raises(ValueError):
            generate_schedule("unknown", {}, date(2025, 1, 1))
