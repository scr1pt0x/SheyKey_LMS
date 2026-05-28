import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.payment import Payment, PaymentSchedule, PaymentStatus
from backend.models.user import User
from backend.schemas.common import PaginatedResponse
from backend.schemas.payment import PaymentCreate, PaymentResponse
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    body: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> PaymentResponse:
    schedule = await db.get(PaymentSchedule, body.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Строка графика не найдена")
    if schedule.status == PaymentStatus.paid:
        raise HTTPException(status_code=400, detail="Платёж уже полностью оплачен")

    remaining = Decimal(str(schedule.amount)) - Decimal(str(schedule.paid_amount))
    if body.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Сумма платежа превышает остаток {remaining}",
        )

    payment = Payment(
        schedule_id=body.schedule_id,
        deal_id=schedule.deal_id,
        amount=body.amount,
        paid_at=body.paid_at,
        method=body.method,
        notes=body.notes,
        recorded_by=current_user.id,
    )
    db.add(payment)

    new_paid = Decimal(str(schedule.paid_amount)) + body.amount
    schedule.paid_amount = new_paid
    if new_paid >= Decimal(str(schedule.amount)):
        schedule.status = PaymentStatus.paid
    else:
        schedule.status = PaymentStatus.partial

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
    await db.commit()
    await db.refresh(payment)
    return PaymentResponse.model_validate(payment)


@router.get("/deal/{deal_id}", response_model=PaginatedResponse[PaymentResponse])
async def get_deal_payments(
    deal_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "sb", "director")),
) -> PaginatedResponse[PaymentResponse]:
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
