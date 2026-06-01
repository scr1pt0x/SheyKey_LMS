"""Payment schedule logic ported from dogovorshikbot/utils.py."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_UP

from dateutil.relativedelta import relativedelta


def round_up_amount(value) -> int:
    d = Decimal(str(value))
    return int(d.to_integral_value(rounding=ROUND_UP))


def add_months_with_payday(base_date: datetime, months: int, payday: int) -> datetime:
    target = base_date + relativedelta(months=+months)
    days_in_month = (target + relativedelta(months=+1, day=1) - timedelta(days=1)).day
    return target.replace(day=min(payday, days_in_month))


def generate_bot_payment_schedule(
    start_date: date | datetime,
    term: int,
    payday: int,
    cost: int,
    advance: int,
) -> list[dict]:
    """
    Build payment schedule rows: date (DD.MM.YYYY), amount, balance (remaining debt).
    """
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_dt = datetime.combine(start_date, datetime.min.time())
    else:
        start_dt = start_date

    balance = max(0, int(cost) - int(advance))
    if term <= 0:
        return []

    base_payment = round_up_amount(Decimal(balance) / Decimal(term))
    schedule: list[dict] = []
    current_date = start_dt

    for _ in range(term):
        current_date = add_months_with_payday(current_date, 1, payday)
        payment = min(base_payment, balance)
        balance -= payment
        schedule.append(
            {
                "date": current_date.strftime("%d.%m.%Y"),
                "amount": payment,
                "balance": balance,
            }
        )

    return schedule
