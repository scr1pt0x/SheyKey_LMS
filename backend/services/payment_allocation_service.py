"""Allocate a lump-sum payment across deal schedule lines (earliest due first)."""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.payment import Payment, PaymentMethod, PaymentSchedule, PaymentStatus


def schedule_remaining(schedule: PaymentSchedule) -> Decimal:
    return Decimal(str(schedule.amount)) - Decimal(str(schedule.paid_amount))


def apply_amount_to_schedule(
    schedule: PaymentSchedule,
    amount: Decimal,
    *,
    deal_id: uuid.UUID,
    paid_at: datetime,
    method: PaymentMethod,
    recorded_by: uuid.UUID,
    notes: str | None,
) -> Payment:
    payment = Payment(
        schedule_id=schedule.id,
        deal_id=deal_id,
        amount=amount,
        paid_at=paid_at,
        method=method,
        notes=notes,
        recorded_by=recorded_by,
    )
    new_paid = Decimal(str(schedule.paid_amount)) + amount
    schedule.paid_amount = new_paid
    if new_paid >= Decimal(str(schedule.amount)):
        schedule.status = PaymentStatus.paid
    else:
        schedule.status = PaymentStatus.partial
    return payment


async def allocate_payment_across_schedules(
    db: AsyncSession,
    deal_id: uuid.UUID,
    total_amount: Decimal,
    paid_at: datetime,
    method: PaymentMethod,
    recorded_by: uuid.UUID,
    notes: str | None = None,
) -> list[Payment]:
    rows = await db.execute(
        select(PaymentSchedule)
        .where(PaymentSchedule.deal_id == deal_id)
        .where(
            PaymentSchedule.status.in_(
                [PaymentStatus.pending, PaymentStatus.overdue, PaymentStatus.partial]
            )
        )
        .order_by(PaymentSchedule.due_date, PaymentSchedule.installment_number)
    )
    schedules = rows.scalars().all()

    total_remaining = sum(schedule_remaining(s) for s in schedules)
    if total_remaining <= 0:
        raise HTTPException(status_code=400, detail="Нет неоплаченных строк графика")
    if total_amount > total_remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Сумма превышает остаток по графику ({total_remaining})",
        )

    left = total_amount
    payments: list[Payment] = []
    for schedule in schedules:
        if left <= 0:
            break
        remaining = schedule_remaining(schedule)
        if remaining <= 0:
            continue
        chunk = min(left, remaining)
        payment = apply_amount_to_schedule(
            schedule,
            chunk,
            deal_id=deal_id,
            paid_at=paid_at,
            method=method,
            recorded_by=recorded_by,
            notes=notes,
        )
        db.add(payment)
        payments.append(payment)
        left -= chunk

    return payments
