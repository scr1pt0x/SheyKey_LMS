import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.access import load_deal_for_user
from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.payment import Payment, PaymentSchedule, PaymentStatus
from backend.models.user import User
from backend.schemas.common import PaginatedResponse
from backend.schemas.payment import (
    PaymentAllocateCreate,
    PaymentAllocateResponse,
    PaymentCreate,
    PaymentResponse,
)
from backend.services.audit_service import AuditService
from backend.services.overdue_case_service import refresh_overdue_case_after_payment
from backend.services.payment_allocation_service import (
    apply_amount_to_schedule,
    schedule_remaining,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    body: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director", "sb")),
) -> PaymentResponse:
    schedule = await db.get(PaymentSchedule, body.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Строка графика не найдена")
    await load_deal_for_user(db, schedule.deal_id, current_user)
    if schedule.status == PaymentStatus.paid:
        raise HTTPException(status_code=400, detail="Платёж уже полностью оплачен")

    remaining = schedule_remaining(schedule)
    if body.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Сумма платежа превышает остаток {remaining}",
        )

    payment = apply_amount_to_schedule(
        schedule,
        body.amount,
        deal_id=schedule.deal_id,
        paid_at=body.paid_at,
        method=body.method,
        recorded_by=current_user.id,
        notes=body.notes,
    )
    db.add(payment)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="PAYMENT_RECORDED",
        entity="payments",
        entity_id=None,
        new_val={
            "schedule_id": str(body.schedule_id),
            "amount": str(body.amount),
            "method": body.method.value,
        },
        ip=get_client_ip(request),
    )
    await refresh_overdue_case_after_payment(db, schedule.deal_id)
    await db.commit()
    await db.refresh(payment)
    return PaymentResponse.model_validate(payment)


@router.post("/allocate", response_model=PaymentAllocateResponse, status_code=status.HTTP_201_CREATED)
async def allocate_payment(
    body: PaymentAllocateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director", "sb")),
) -> PaymentAllocateResponse:
    from backend.services.payment_allocation_service import allocate_payment_across_schedules

    await load_deal_for_user(db, body.deal_id, current_user)

    payments = await allocate_payment_across_schedules(
        db=db,
        deal_id=body.deal_id,
        total_amount=body.amount,
        paid_at=body.paid_at,
        method=body.method,
        recorded_by=current_user.id,
        notes=body.notes,
    )

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="PAYMENT_ALLOCATED",
        entity="payments",
        entity_id=None,
        new_val={
            "deal_id": str(body.deal_id),
            "amount": str(body.amount),
            "parts": len(payments),
            "method": body.method.value,
        },
        ip=get_client_ip(request),
    )
    await refresh_overdue_case_after_payment(db, body.deal_id)
    await db.commit()
    for p in payments:
        await db.refresh(p)

    return PaymentAllocateResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total_applied=body.amount,
        deal_id=body.deal_id,
    )


@router.get("/deal/{deal_id}", response_model=PaginatedResponse[PaymentResponse])
async def get_deal_payments(
    deal_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[PaymentResponse]:
    await load_deal_for_user(db, deal_id, current_user)
    total = (
        await db.execute(
            select(func.count()).where(Payment.deal_id == deal_id)
        )
    ).scalar_one()

    rows = await db.execute(
        select(Payment)
        .where(Payment.deal_id == deal_id)
        .order_by(Payment.paid_at.desc())
        .limit(limit)
        .offset(offset)
    )
    payments = rows.scalars().all()
    return PaginatedResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> dict:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    await load_deal_for_user(db, payment.deal_id, current_user)
    if payment.confirmed_by:
        raise HTTPException(status_code=400, detail="Платёж уже подтверждён")

    payment.confirmed_by = current_user.id
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="PAYMENT_CONFIRMED",
        entity="payments",
        entity_id=str(payment_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Платёж подтверждён"}


@router.patch("/{payment_id}/receipt")
async def attach_receipt(
    payment_id: uuid.UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> dict:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    await load_deal_for_user(db, payment.deal_id, current_user)

    receipt_url = body.get("receipt_url")
    if not receipt_url:
        raise HTTPException(status_code=400, detail="receipt_url is required")

    payment.receipt_url = receipt_url
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="RECEIPT_ATTACHED",
        entity="payments",
        entity_id=str(payment_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Чек прикреплён"}
