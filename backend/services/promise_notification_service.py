"""Helpers for payment promise notifications to SB staff."""
import uuid
from datetime import date
from decimal import Decimal


def build_promise_alert(
    promised_date: date,
    promised_amount: Decimal,
    case_id: uuid.UUID,
    today: date,
) -> tuple[str, str]:
    """Return (title, body) for an unfulfilled promise alert."""
    days_late = (today - promised_date).days
    short_id = str(case_id)[:8]
    amount_str = f"{promised_amount:,.2f}".replace(",", " ").replace(".", ",")

    if days_late == 0:
        return (
            "Обещание платежа сегодня",
            f"Дело #{short_id} · Должник обещал сегодня оплатить {amount_str} ₽",
        )

    return (
        "Обещание платежа не выполнено",
        f"Дело #{short_id} · Сумма: {amount_str} ₽ · Просрочено на {days_late} дн.",
    )
