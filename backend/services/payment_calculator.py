"""
Payment schedule calculators for all three Islamic finance deal types.

All amounts use Python Decimal for precision.
"""
from dataclasses import dataclass
from datetime import date, datetime
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


def generate_murabaha_schedule_bot(
    total: Decimal,
    advance: Decimal,
    duration_months: int,
    start_date: date,
    payday: int,
) -> list[ScheduleItem]:
    """Murabaha schedule: dogovorshikbot logic (advance, payday, ceil monthly)."""
    from backend.services.murabaha_bot_schedule import generate_bot_payment_schedule

    rows = generate_bot_payment_schedule(
        start_date=start_date,
        term=duration_months,
        payday=payday,
        cost=int(total),
        advance=int(advance),
    )
    items: list[ScheduleItem] = []
    for i, row in enumerate(rows, start=1):
        due = datetime.strptime(row["date"], "%d.%m.%Y").date()
        items.append(
            ScheduleItem(
                installment_number=i,
                due_date=due,
                amount=Decimal(str(row["amount"])),
                installment_type="principal",
            )
        )
    return items


def generate_murabaha_schedule(
    principal: Decimal,
    markup: Decimal,
    duration_months: int,
    start_date: date,
    advance: Decimal = Decimal("0"),
    payday: int | None = None,
) -> list[ScheduleItem]:
    total = principal + markup
    payday_val = payday if payday is not None else start_date.day
    return generate_murabaha_schedule_bot(
        total=total,
        advance=advance,
        duration_months=duration_months,
        start_date=start_date,
        payday=payday_val,
    )


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
        advance = Decimal(str(params.get("down_payment_amount") or 0))
        payday = int(params["payday"]) if params.get("payday") is not None else start_date.day
        return generate_murabaha_schedule(
            principal=Decimal(str(params["principal"])),
            markup=Decimal(str(params["markup"])),
            duration_months=int(params["duration_months"]),
            start_date=start_date,
            advance=advance,
            payday=payday,
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
