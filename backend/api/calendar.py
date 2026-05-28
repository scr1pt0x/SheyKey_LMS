import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.calendar_task import CalendarTask, CalendarTaskStatus
from backend.models.payment import PaymentSchedule, PaymentStatus
from backend.models.deal import Deal, DealStatus
from backend.models.user import User

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CalendarTaskCreate(BaseModel):
    client_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1)
    description: str | None = None
    due_date: date


class CalendarTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: CalendarTaskStatus | None = None


class CalendarTaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    client_id: uuid.UUID | None
    deal_id: uuid.UUID | None
    title: str
    description: str | None
    due_date: date
    status: CalendarTaskStatus


class ScheduledPaymentItem(BaseModel):
    schedule_id: uuid.UUID
    deal_id: uuid.UUID
    client_id: uuid.UUID
    due_date: date
    amount: float
    status: str


@router.get("/today")
async def payments_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> list[ScheduledPaymentItem]:
    today = datetime.now(timezone.utc).date()
    rows = await db.execute(
        select(PaymentSchedule, Deal)
        .join(Deal, PaymentSchedule.deal_id == Deal.id)
        .where(PaymentSchedule.due_date == today)
        .where(PaymentSchedule.status == PaymentStatus.pending)
        .where(Deal.manager_id == current_user.id)
        .where(Deal.status == DealStatus.active)
    )
    result = []
    for schedule, deal in rows.all():
        result.append(
            ScheduledPaymentItem(
                schedule_id=schedule.id,
                deal_id=deal.id,
                client_id=deal.client_id,
                due_date=schedule.due_date,
                amount=float(schedule.amount),
                status=schedule.status.value,
            )
        )
    return result


@router.get("/week")
async def payments_week(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> list[ScheduledPaymentItem]:
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    week_end = today + timedelta(days=7)

    rows = await db.execute(
        select(PaymentSchedule, Deal)
        .join(Deal, PaymentSchedule.deal_id == Deal.id)
        .where(PaymentSchedule.due_date >= today)
        .where(PaymentSchedule.due_date <= week_end)
        .where(PaymentSchedule.status == PaymentStatus.pending)
        .where(Deal.manager_id == current_user.id)
        .where(Deal.status == DealStatus.active)
        .order_by(PaymentSchedule.due_date)
    )
    result = []
    for schedule, deal in rows.all():
        result.append(
            ScheduledPaymentItem(
                schedule_id=schedule.id,
                deal_id=deal.id,
                client_id=deal.client_id,
                due_date=schedule.due_date,
                amount=float(schedule.amount),
                status=schedule.status.value,
            )
        )
    return result


@router.get("/tasks", response_model=list[CalendarTaskResponse])
async def get_tasks(
    status_filter: CalendarTaskStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> list[CalendarTaskResponse]:
    query = select(CalendarTask).where(CalendarTask.user_id == current_user.id)
    if status_filter:
        query = query.where(CalendarTask.status == status_filter)
    query = query.order_by(CalendarTask.due_date)
    rows = await db.execute(query)
    return [CalendarTaskResponse.model_validate(t) for t in rows.scalars().all()]


@router.post("/tasks", response_model=CalendarTaskResponse)
async def create_task(
    body: CalendarTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> CalendarTaskResponse:
    task = CalendarTask(
        user_id=current_user.id,
        client_id=body.client_id,
        deal_id=body.deal_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return CalendarTaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=CalendarTaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: CalendarTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> CalendarTaskResponse:
    from fastapi import HTTPException

    task = await db.get(CalendarTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return CalendarTaskResponse.model_validate(task)
