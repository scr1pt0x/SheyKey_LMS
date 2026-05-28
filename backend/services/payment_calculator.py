"""
Payment schedule calculators for all three Islamic finance deal types.

All amounts use Python Decimal for precision.
"""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta


@dataclass
class ScheduleItem:
    installment_number: int
    due_date: date
    amount: Decimal
    installment_type: str = "principal"


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_murabaha_schedule(
    principal: Decimal,
    markup: Decimal,
    duration_months: int,
    start_date: date,
) -> list[ScheduleItem]:
    """
    Murabaha: total = principal + markup (fixed at deal creation).
    Equal monthly instalments: total / duration_months.
    Last instalment absorbs rounding difference.
    """
    total = principal + markup
    base_payment = _round(total / duration_months)
    schedule: list[ScheduleItem] = []

    accumulated = Decimal("0")
    for i in range(1, duration_months + 1):
        due = start_date + relativedelta(months=i)
        if i < duration_months:
            amount = base_payment
        else:
            amount = _round(total - accumulated)
        accumulated += amount
        schedule.append(
            ScheduleItem(
                installment_number=i,
                due_date=due,
                amount=amount,
                installment_type="principal",
            )
        )
    return schedule


def generate_ijara_schedule(
    monthly_rent: Decimal,
    duration_months: int,
    start_date: date,
    buyout_amount: Decimal | None = None,
) -> list[ScheduleItem]:
    """
    Ijara: fixed monthly rent for the lease period.
    Optional buyout payment appended as a separate last instalment.
    """
    schedule: list[ScheduleItem] = []
    for i in range(1, duration_months + 1):
        due = start_date + relativedelta(months=i)
        schedule.append(
            ScheduleItem(
                installment_number=i,
                due_date=due,
                amount=_round(monthly_rent),
                installment_type="rent",
            )
        )
    if buyout_amount is not None and buyout_amount > Decimal("0"):
        due = start_date + relativedelta(months=duration_months + 1)
        schedule.append(
            ScheduleItem(
                installment_number=duration_months + 1,
                due_date=due,
                amount=_round(buyout_amount),
                installment_type="buyout",
            )
        )
    return schedule


def generate_schedule(deal_type: str, params: dict, start_date: date) -> list[ScheduleItem]:
    """Dispatcher: returns schedule for any deal type from its params dict."""
    if deal_type == "murabaha":
        return generate_murabaha_schedule(
            principal=Decimal(str(params["principal"])),
            markup=Decimal(str(params["markup"])),
            duration_months=int(params["duration_months"]),
            start_date=start_date,
        )
    elif deal_type == "ijara":
        buyout = Decimal(str(params["buyout_amount"])) if params.get("buyout_amount") else None
        return generate_ijara_schedule(
            monthly_rent=Decimal(str(params["monthly_rent"])),
            duration_months=int(params["duration_months"]),
            start_date=start_date,
            buyout_amount=buyout,
        )
    else:
        raise ValueError(f"Unknown deal type: {deal_type}")
