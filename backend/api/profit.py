"""
Profit distribution module: investors, expenses, period calculation and approval.
All endpoints are director-only.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.models.expense import Expense, ExpenseCategory, EXPENSE_CATEGORY_LABELS
from backend.models.investor import Investor
from backend.models.payment import Payment
from backend.models.profit_period import ProfitDistribution, ProfitPeriod, ProfitPeriodStatus
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User
from backend.services.audit_service import AuditService
from backend.services.investor_share_service import recalculate_active_investor_shares

router = APIRouter(prefix="/api/director/profit", tags=["profit"])

# ─── Schemas ─────────────────────────────────────────────────────────────────


class InvestorCreate(BaseModel):
    name: str = Field(..., min_length=2)
    phone: str | None = None
    investment_amount: float = Field(..., gt=0)
    joined_at: date | None = None
    notes: str | None = None


class InvestorUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    investment_amount: float | None = Field(None, gt=0)
    joined_at: date | None = None
    notes: str | None = None


class InvestorResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    phone: str | None
    share_pct: float
    investment_amount: float | None
    joined_at: date | None
    notes: str | None
    is_active: bool
    created_at: datetime


class ExpenseCreate(BaseModel):
    category: ExpenseCategory
    amount: float = Field(..., gt=0)
    description: str | None = None
    expense_date: date


class ExpenseResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    period_id: uuid.UUID | None
    category: ExpenseCategory
    category_label: str = ""
    amount: float
    description: str | None
    expense_date: date
    created_at: datetime

    def model_post_init(self, __context) -> None:
        self.category_label = EXPENSE_CATEGORY_LABELS.get(self.category, str(self.category))


class CalculateRequest(BaseModel):
    period_start: date
    period_end: date


class DistributionItem(BaseModel):
    investor_id: uuid.UUID
    investor_name: str
    share_pct: float
    amount: float


class ProfitPeriodResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    period_start: date
    period_end: date
    status: ProfitPeriodStatus
    gross_revenue: float
    total_expenses: float
    manager_bonus_pct: float
    manager_bonus_amount: float
    net_distributable: float
    partner_remainder: float = 0.0
    distributions: list[DistributionItem] = []
    approved_at: datetime | None
    created_at: datetime


# ─── Investors ───────────────────────────────────────────────────────────────


@router.get("/investors", response_model=list[InvestorResponse])
async def list_investors(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[InvestorResponse]:
    query = select(Investor)
    if not include_inactive:
        query = query.where(Investor.is_active == True)  # noqa
    rows = await db.execute(query.order_by(Investor.joined_at.desc().nullslast(), Investor.created_at))
    investors = rows.scalars().all()
    return [InvestorResponse.model_validate(inv) for inv in investors]


@router.get("/investors/summary")
async def investors_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    rows = await db.execute(
        select(Investor).where(Investor.is_active == True)  # noqa
    )
    investors = rows.scalars().all()
    total_share = sum(float(inv.share_pct) for inv in investors)
    total_invested = sum(float(inv.investment_amount or 0) for inv in investors)
    return {
        "total_investors": len(investors),
        "total_share_pct": round(total_share, 2),
        "partner_remainder_pct": round(max(0, 100 - total_share), 2),
        "total_invested": total_invested,
    }


@router.post("/investors", response_model=InvestorResponse)
async def create_investor(
    body: InvestorCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> InvestorResponse:
    investor = Investor(
        name=body.name,
        phone=body.phone,
        share_pct=0,
        investment_amount=body.investment_amount,
        joined_at=body.joined_at,
        notes=body.notes,
    )
    db.add(investor)
    await db.flush()
    await recalculate_active_investor_shares(db)
    await AuditService.log(
        db=db, user_id=str(current_user.id), action="CREATE",
        entity="investors",
        new_val={"name": body.name, "investment_amount": body.investment_amount},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(investor)
    return InvestorResponse.model_validate(investor)


@router.patch("/investors/{investor_id}", response_model=InvestorResponse)
async def update_investor(
    investor_id: uuid.UUID,
    body: InvestorUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> InvestorResponse:
    investor = await db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(status_code=404, detail="Инвестор не найден")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(investor, field, value)

    if body.investment_amount is not None or investor.is_active:
        await recalculate_active_investor_shares(db)

    await AuditService.log(
        db=db, user_id=str(current_user.id), action="UPDATE",
        entity="investors", entity_id=str(investor_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(investor)
    return InvestorResponse.model_validate(investor)


@router.delete("/investors/{investor_id}")
async def deactivate_investor(
    investor_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    investor = await db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(status_code=404, detail="Инвестор не найден")

    pending_period = (
        await db.execute(
            select(ProfitDistribution.id)
            .join(ProfitPeriod, ProfitDistribution.period_id == ProfitPeriod.id)
            .where(ProfitDistribution.investor_id == investor_id)
            .where(ProfitPeriod.status == ProfitPeriodStatus.draft)
            .limit(1)
        )
    ).scalar_one_or_none()

    if pending_period:
        raise HTTPException(
            status_code=400,
            detail="Нельзя деактивировать инвестора с незакрытым расчётным периодом",
        )

    investor.is_active = False
    await recalculate_active_investor_shares(db)
    await AuditService.log(
        db=db, user_id=str(current_user.id), action="DEACTIVATE",
        entity="investors", entity_id=str(investor_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Инвестор деактивирован"}


# ─── Expenses ────────────────────────────────────────────────────────────────


@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[ExpenseResponse]:
    query = select(Expense)
    if date_from:
        query = query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
    rows = await db.execute(query.order_by(Expense.expense_date.desc()))
    return [ExpenseResponse.model_validate(e) for e in rows.scalars().all()]


@router.get("/expenses/total")
async def expenses_total(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    rows = await db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0).label("total"))
        .where(Expense.expense_date >= date_from)
        .where(Expense.expense_date <= date_to)
        .group_by(Expense.category)
    )
    by_category = {
        EXPENSE_CATEGORY_LABELS.get(r[0], str(r[0])): float(r[1])
        for r in rows.all()
    }
    grand_total = sum(by_category.values())
    return {"by_category": by_category, "total": grand_total}


@router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(
    body: ExpenseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> ExpenseResponse:
    expense = Expense(
        category=body.category,
        amount=body.amount,
        description=body.description,
        expense_date=body.expense_date,
        created_by=current_user.id,
    )
    db.add(expense)
    await AuditService.log(
        db=db, user_id=str(current_user.id), action="CREATE",
        entity="expenses",
        new_val={"amount": str(body.amount), "category": body.category.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


@router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    if expense.period_id:
        period = await db.get(ProfitPeriod, expense.period_id)
        if period and period.status == ProfitPeriodStatus.approved:
            raise HTTPException(status_code=400, detail="Нельзя удалить расход из утверждённого периода")

    await db.delete(expense)
    await AuditService.log(
        db=db, user_id=str(current_user.id), action="DELETE",
        entity="expenses", entity_id=str(expense_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Расход удалён"}


# ─── Profit periods ──────────────────────────────────────────────────────────


@router.get("/periods", response_model=list[ProfitPeriodResponse])
async def list_periods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[ProfitPeriodResponse]:
    rows = await db.execute(
        select(ProfitPeriod)
        .options(selectinload(ProfitPeriod.distributions).selectinload(ProfitDistribution.investor))
        .order_by(ProfitPeriod.period_start.desc())
    )
    return [_build_period_response(p) for p in rows.scalars().all()]


@router.get("/periods/{period_id}", response_model=ProfitPeriodResponse)
async def get_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> ProfitPeriodResponse:
    result = await db.execute(
        select(ProfitPeriod)
        .where(ProfitPeriod.id == period_id)
        .options(selectinload(ProfitPeriod.distributions).selectinload(ProfitDistribution.investor))
    )
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    return _build_period_response(period)


@router.post("/calculate", response_model=ProfitPeriodResponse)
async def calculate_period(
    body: CalculateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> ProfitPeriodResponse:
    if body.period_end < body.period_start:
        raise HTTPException(status_code=400, detail="Дата окончания должна быть позже даты начала")

    # Check no duplicate draft for same period
    existing = (
        await db.execute(
            select(ProfitPeriod)
            .where(ProfitPeriod.period_start == body.period_start)
            .where(ProfitPeriod.period_end == body.period_end)
            .where(ProfitPeriod.status == ProfitPeriodStatus.draft)
        )
    ).scalar_one_or_none()
    if existing:
        # Recalculate existing draft
        await _delete_period_distributions(db, existing.id)
        period = existing
    else:
        period = ProfitPeriod(period_start=body.period_start, period_end=body.period_end)
        db.add(period)
        await db.flush()

    # Gross revenue from payments in period
    from datetime import datetime as dt
    period_start_dt = dt.combine(body.period_start, dt.min.time()).replace(tzinfo=__import__("datetime").timezone.utc)
    period_end_dt = dt.combine(body.period_end, dt.max.time()).replace(tzinfo=__import__("datetime").timezone.utc)

    gross = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.paid_at >= period_start_dt)
            .where(Payment.paid_at <= period_end_dt)
        )
    ).scalar_one()

    # Total expenses in period
    total_exp = (
        await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.expense_date >= body.period_start)
            .where(Expense.expense_date <= body.period_end)
        )
    ).scalar_one()

    # Manager bonus % from settings
    bonus_pct_setting = (
        await db.execute(
            select(SystemSetting.value).where(SystemSetting.key == SettingKey.MANAGER_BONUS_PCT)
        )
    ).scalar_one_or_none()
    bonus_pct = float(bonus_pct_setting) if bonus_pct_setting is not None else 5.0

    net_company = float(gross) - float(total_exp)
    if net_company < 0:
        net_company = 0.0
    bonus_amount = round(net_company * bonus_pct / 100, 2)
    net_distributable = round(net_company - bonus_amount, 2)

    period.gross_revenue = gross
    period.total_expenses = total_exp
    period.manager_bonus_pct = bonus_pct
    period.manager_bonus_amount = bonus_amount
    period.net_distributable = net_distributable

    # Create distributions for each active investor
    investors_q = await db.execute(
        select(Investor).where(Investor.is_active == True).order_by(Investor.created_at)  # noqa
    )
    investors = investors_q.scalars().all()

    for inv in investors:
        amount = round(net_distributable * float(inv.share_pct) / 100, 2)
        dist = ProfitDistribution(
            period_id=period.id,
            investor_id=inv.id,
            share_pct=float(inv.share_pct),
            amount=amount,
        )
        db.add(dist)

    await AuditService.log(
        db=db, user_id=str(current_user.id), action="CREATE",
        entity="profit_periods", entity_id=str(period.id),
        new_val={
            "period": f"{body.period_start} — {body.period_end}",
            "gross": str(gross),
            "net_distributable": str(net_distributable),
        },
        ip=get_client_ip(request),
    )
    await db.commit()

    result = await db.execute(
        select(ProfitPeriod)
        .where(ProfitPeriod.id == period.id)
        .options(selectinload(ProfitPeriod.distributions).selectinload(ProfitDistribution.investor))
    )
    return _build_period_response(result.scalar_one())


@router.post("/periods/{period_id}/approve")
async def approve_period(
    period_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    period = await db.get(ProfitPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    if period.status == ProfitPeriodStatus.approved:
        raise HTTPException(status_code=400, detail="Период уже утверждён")

    period.status = ProfitPeriodStatus.approved
    period.approved_by = current_user.id
    period.approved_at = datetime.now(timezone.utc)

    # Link expenses in the period to this period record
    await db.execute(
        __import__("sqlalchemy").update(Expense)
        .where(Expense.expense_date >= period.period_start)
        .where(Expense.expense_date <= period.period_end)
        .where(Expense.period_id == None)  # noqa
        .values(period_id=period_id)
    )

    await AuditService.log(
        db=db, user_id=str(current_user.id),         action="PROFIT_PERIOD_APPROVED",
        entity="profit_periods", entity_id=str(period_id),
        new_val={"status": "approved", "net_distributable": str(period.net_distributable)},
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Распределение утверждено"}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _build_period_response(period: ProfitPeriod) -> ProfitPeriodResponse:
    distributions = [
        DistributionItem(
            investor_id=d.investor_id,
            investor_name=d.investor.name if d.investor else "—",
            share_pct=float(d.share_pct),
            amount=float(d.amount),
        )
        for d in sorted(period.distributions, key=lambda x: x.share_pct, reverse=True)
    ]
    total_distributed = sum(d.amount for d in distributions)
    partner_remainder = round(float(period.net_distributable) - total_distributed, 2)

    return ProfitPeriodResponse(
        id=period.id,
        period_start=period.period_start,
        period_end=period.period_end,
        status=period.status,
        gross_revenue=float(period.gross_revenue),
        total_expenses=float(period.total_expenses),
        manager_bonus_pct=float(period.manager_bonus_pct),
        manager_bonus_amount=float(period.manager_bonus_amount),
        net_distributable=float(period.net_distributable),
        partner_remainder=max(0.0, partner_remainder),
        distributions=distributions,
        approved_at=period.approved_at,
        created_at=period.created_at,
    )


async def _delete_period_distributions(db, period_id: uuid.UUID) -> None:
    from sqlalchemy import delete
    await db.execute(
        delete(ProfitDistribution).where(ProfitDistribution.period_id == period_id)
    )
