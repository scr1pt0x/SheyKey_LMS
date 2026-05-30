"""
Director API: dashboard (Redis-cached), analytics, team management,
approval queue, audit log, system settings, user management.
"""
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, case as sa_case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.core.dependencies import get_client_ip, require_role
from backend.core.redis_client import (
    CACHE_TTL_DASHBOARD,
    DASHBOARD_CACHE_PREFIX,
    cache_delete,
    cache_get,
    cache_set,
)
from backend.models.audit import AuditLog
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus, DealType
from backend.models.overdue import ContactLog, OverdueCase, OverdueCaseStatus, PaymentPromise
from backend.models.payment import Payment, PaymentSchedule
from backend.models.restructuring import Restructuring, RestructuringStatus
from backend.models.settings import SystemSetting
from backend.models.user import User, UserRole
from backend.schemas.common import PaginatedResponse
from backend.schemas.director import (
    ApprovalDecision,
    AuditLogItem,
    ConversionFunnelResponse,
    DirectorDashboardResponse,
    IssuanceDynamicsItem,
    ManagerPortfolioItem,
    PortfolioByTypeItem,
    ReassignRequest,
    RejectDecision,
    SbPerformanceItem,
    SettingUpdate,
    TopDebtorItem,
)
from backend.schemas.sb import RestructuringResponse
from backend.schemas.user import UserCreate, UserListResponse, UserResponse
from backend.services.audit_service import AuditService
from backend.core.security import hash_password
from backend.services.push_service import notify_staff

router = APIRouter(prefix="/api/director", tags=["director"])

# ─── Dashboard ───────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DirectorDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> DirectorDashboardResponse:
    cache_key = f"{DASHBOARD_CACHE_PREFIX}main"
    cached = await cache_get(cache_key)
    if cached:
        return DirectorDashboardResponse.model_validate(json.loads(cached))

    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    total_portfolio = (
        await db.execute(
            select(func.coalesce(func.sum(Deal.total), 0))
            .where(Deal.status == DealStatus.active)
        )
    ).scalar_one()

    active_deals = (
        await db.execute(select(func.count()).where(Deal.status == DealStatus.active))
    ).scalar_one()

    overdue_deals = (
        await db.execute(select(func.count()).where(Deal.status == DealStatus.overdue))
    ).scalar_one()

    closed_deals = (
        await db.execute(select(func.count()).where(Deal.status == DealStatus.closed))
    ).scalar_one()

    total_active_overdue = active_deals + overdue_deals
    overdue_pct = (overdue_deals / total_active_overdue * 100) if total_active_overdue > 0 else 0.0

    cash_flow_today = (
        await db.execute(
            select(func.coalesce(func.sum(PaymentSchedule.amount), 0))
            .where(PaymentSchedule.due_date == today)
            .where(PaymentSchedule.status.in_(["pending", "partial"]))
        )
    ).scalar_one()

    cash_flow_week = (
        await db.execute(
            select(func.coalesce(func.sum(PaymentSchedule.amount - PaymentSchedule.paid_amount), 0))
            .where(PaymentSchedule.due_date >= today)
            .where(PaymentSchedule.due_date <= today + timedelta(days=7))
            .where(PaymentSchedule.status.in_(["pending", "partial"]))
        )
    ).scalar_one()

    cash_flow_month = (
        await db.execute(
            select(func.coalesce(func.sum(PaymentSchedule.amount - PaymentSchedule.paid_amount), 0))
            .where(PaymentSchedule.due_date >= today)
            .where(PaymentSchedule.due_date <= today.replace(day=28) + timedelta(days=4))
            .where(PaymentSchedule.status.in_(["pending", "partial"]))
        )
    ).scalar_one()

    new_deals_month = (
        await db.execute(
            select(func.count())
            .where(Deal.created_at >= datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc))
        )
    ).scalar_one()

    income_month = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.paid_at >= datetime.combine(month_start, datetime.min.time(), tzinfo=timezone.utc))
        )
    ).scalar_one()

    data = DirectorDashboardResponse(
        total_portfolio=Decimal(str(total_portfolio)),
        active_deals=active_deals,
        overdue_deals=overdue_deals,
        closed_deals=closed_deals,
        cash_flow_today=Decimal(str(cash_flow_today)),
        cash_flow_week=Decimal(str(cash_flow_week)),
        cash_flow_month=Decimal(str(cash_flow_month)),
        overdue_pct=round(overdue_pct, 2),
        new_deals_month=new_deals_month,
        income_month=Decimal(str(income_month)),
    )
    await cache_set(cache_key, data.model_dump_json(), CACHE_TTL_DASHBOARD)
    return data


# ─── Analytics ───────────────────────────────────────────────────────────────


@router.get("/analytics/portfolio", response_model=list[PortfolioByTypeItem])
async def portfolio_by_type(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[PortfolioByTypeItem]:
    rows = await db.execute(
        select(Deal.type, func.count().label("cnt"), func.coalesce(func.sum(Deal.total), 0).label("total"))
        .where(Deal.status == DealStatus.active)
        .group_by(Deal.type)
    )
    results = rows.all()
    total_all = sum(r.total for r in results) or 1
    return [
        PortfolioByTypeItem(
            type=r.type.value,
            count=r.cnt,
            total_amount=Decimal(str(r.total)),
            pct=round(float(r.total) / float(total_all) * 100, 2),
        )
        for r in results
    ]


@router.get("/analytics/issuance", response_model=list[IssuanceDynamicsItem])
async def issuance_dynamics(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[IssuanceDynamicsItem]:
    rows = await db.execute(
        select(
            func.to_char(Deal.created_at, "YYYY-MM").label("month"),
            func.count().label("cnt"),
            func.coalesce(func.sum(Deal.total), 0).label("total"),
        )
        .where(Deal.created_at >= datetime.now(timezone.utc) - timedelta(days=months * 31))
        .group_by(func.to_char(Deal.created_at, "YYYY-MM"))
        .order_by(func.to_char(Deal.created_at, "YYYY-MM"))
    )
    return [
        IssuanceDynamicsItem(month=r.month, count=r.cnt, total_amount=Decimal(str(r.total)))
        for r in rows.all()
    ]


@router.get("/analytics/top-debtors", response_model=list[TopDebtorItem])
async def top_debtors(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[TopDebtorItem]:
    rows = await db.execute(
        select(
            Client.id.label("client_id"),
            Client.full_name.label("client_name"),
            OverdueCase.deal_id,
            OverdueCase.total_debt,
            OverdueCase.days_overdue,
            OverdueCase.status.label("sb_status"),
        )
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .join(Client, Deal.client_id == Client.id)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
        .order_by(OverdueCase.total_debt.desc())
        .limit(limit)
    )
    return [
        TopDebtorItem(
            client_id=r.client_id,
            client_name=r.client_name,
            deal_id=r.deal_id,
            total_debt=Decimal(str(r.total_debt)),
            days_overdue=r.days_overdue,
            sb_status=r.sb_status.value if r.sb_status else None,
        )
        for r in rows.all()
    ]


@router.get("/analytics/sb-performance", response_model=list[SbPerformanceItem])
async def sb_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[SbPerformanceItem]:
    rows = await db.execute(
        select(
            User.id.label("sb_user_id"),
            User.name.label("sb_name"),
            func.count(OverdueCase.id).label("cases_total"),
            func.sum(
                sa_case(
                    (OverdueCase.status == OverdueCaseStatus.closed, 1),
                    else_=0,
                )
            ).label("cases_closed"),
        )
        .join(OverdueCase, OverdueCase.sb_user_id == User.id)
        .where(User.role == UserRole.sb)
        .group_by(User.id, User.name)
    )
    results = rows.all()

    items = []
    for r in results:
        recovered = (
            await db.execute(
                select(func.coalesce(func.sum(PaymentPromise.promised_amount), 0))
                .join(OverdueCase, PaymentPromise.case_id == OverdueCase.id)
                .where(OverdueCase.sb_user_id == r.sb_user_id)
                .where(PaymentPromise.is_fulfilled == True)  # noqa
            )
        ).scalar_one()

        items.append(
            SbPerformanceItem(
                sb_user_id=r.sb_user_id,
                sb_name=r.sb_name,
                cases_total=r.cases_total,
                cases_closed=r.cases_closed or 0,
                recovered_amount=Decimal(str(recovered)),
            )
        )
    return items


@router.get("/analytics/avg-deal")
async def avg_deal_size(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    rows = await db.execute(
        select(
            Deal.type,
            func.avg(Deal.total).label("avg"),
            func.count().label("cnt"),
        )
        .where(Deal.status.in_(["active", "closed"]))
        .group_by(Deal.type)
    )
    result = [
        {"type": r.type.value, "avg_amount": round(float(r.avg), 2), "count": r.cnt}
        for r in rows.all()
    ]
    overall_avg = (
        await db.execute(
            select(func.avg(Deal.total)).where(Deal.status.in_(["active", "closed"]))
        )
    ).scalar_one() or 0
    return {"by_type": result, "overall_avg": round(float(overall_avg), 2)}


@router.get("/analytics/income")
async def income_by_type(
    months: int = Query(3, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list:
    """Actual payments received grouped by deal type over last N months."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 31)
    rows = await db.execute(
        select(
            Deal.type,
            func.coalesce(func.sum(Payment.amount), 0).label("income"),
            func.count(Payment.id.distinct()).label("payment_count"),
        )
        .join(Deal, Payment.deal_id == Deal.id)
        .where(Payment.paid_at >= since)
        .group_by(Deal.type)
    )
    return [
        {
            "type": r.type.value,
            "income": float(r.income),
            "payment_count": r.payment_count,
        }
        for r in rows.all()
    ]


@router.get("/analytics/team-activity")
async def team_activity(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list:
    """Actions per staff member over the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = await db.execute(
        select(
            AuditLog.user_id,
            User.name,
            User.role,
            func.count().label("action_count"),
            func.max(AuditLog.created_at).label("last_action"),
        )
        .join(User, AuditLog.user_id == User.id)
        .where(AuditLog.created_at >= since)
        .where(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id, User.name, User.role)
        .order_by(func.count().desc())
    )
    results = rows.all()

    # For each user, get the most frequent action type
    items = []
    for r in results:
        top_action_result = await db.execute(
            select(AuditLog.action, func.count().label("cnt"))
            .where(AuditLog.user_id == r.user_id)
            .where(AuditLog.created_at >= since)
            .group_by(AuditLog.action)
            .order_by(func.count().desc())
            .limit(1)
        )
        top_action_row = top_action_result.first()
        top_action = top_action_row[0] if top_action_row else None

        items.append({
            "user_id": str(r.user_id),
            "name": r.name,
            "role": r.role.value,
            "action_count": r.action_count,
            "last_action": r.last_action.isoformat() if r.last_action else None,
            "top_action": top_action,
        })
    return items


@router.get("/analytics/conversion", response_model=ConversionFunnelResponse)
async def conversion_funnel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> ConversionFunnelResponse:
    rows = await db.execute(
        select(Deal.status, func.count()).group_by(Deal.status)
    )
    counts = {r[0].value: r[1] for r in rows.all()}
    return ConversionFunnelResponse(
        draft=counts.get("draft", 0),
        pending=counts.get("pending", 0),
        active=counts.get("active", 0),
        closed=counts.get("closed", 0),
        overdue=counts.get("overdue", 0),
    )


# ─── Approval queue ──────────────────────────────────────────────────────────


@router.get("/approval/deals")
async def list_pending_deals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> PaginatedResponse:
    from backend.schemas.deal import DealListItem

    total = (
        await db.execute(select(func.count()).where(Deal.status == DealStatus.pending))
    ).scalar_one()
    rows = await db.execute(
        select(Deal)
        .where(Deal.status == DealStatus.pending)
        .order_by(Deal.created_at)
        .limit(limit)
        .offset(offset)
    )
    deals = rows.scalars().all()
    return PaginatedResponse(
        items=[DealListItem.model_validate(d) for d in deals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/approval/deals/{deal_id}/approve")
async def approve_deal(
    deal_id: uuid.UUID,
    body: ApprovalDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    if deal.status != DealStatus.pending:
        raise HTTPException(status_code=400, detail="Сделка не ожидает согласования")

    deal.status = DealStatus.active
    deal.approved_by = current_user.id
    deal.approved_at = datetime.now(timezone.utc)

    # If backdated deal — immediately mark overdue schedules without waiting for Celery
    today = datetime.now(timezone.utc).date()
    if deal.start_date and deal.start_date < today:
        from backend.models.payment import PaymentSchedule, PaymentStatus
        overdue_result = await db.execute(
            select(PaymentSchedule)
            .where(PaymentSchedule.deal_id == deal.id)
            .where(PaymentSchedule.due_date < today)
            .where(PaymentSchedule.status == PaymentStatus.pending)
        )
        has_overdue = False
        for sched in overdue_result.scalars().all():
            sched.status = PaymentStatus.overdue
            has_overdue = True
        if has_overdue:
            deal.status = DealStatus.overdue

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="DEAL_APPROVED",
        entity="deals",
        entity_id=str(deal_id),
        old_val={"status": "pending"},
        new_val={"status": deal.status.value, "comment": body.comment},
        ip=get_client_ip(request),
    )
    await notify_staff(
        db=db,
        user_id=deal.manager_id,
        title="Сделка одобрена",
        body=f"Ваша сделка на {deal.total} ₽ одобрена руководителем.",
        entity_type="deals",
        entity_id=str(deal_id),
        action_url=f"/deals/{deal_id}",
    )
    await cache_delete(f"{DASHBOARD_CACHE_PREFIX}main")
    await db.commit()
    return {"detail": "Сделка одобрена"}


@router.post("/approval/deals/{deal_id}/reject")
async def reject_deal(
    deal_id: uuid.UUID,
    body: RejectDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    if deal.status != DealStatus.pending:
        raise HTTPException(status_code=400, detail="Сделка не ожидает согласования")

    deal.status = DealStatus.draft
    deal.rejection_comment = body.comment
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="DEAL_REJECTED",
        entity="deals",
        entity_id=str(deal_id),
        old_val={"status": "pending"},
        new_val={"status": "draft", "rejection_comment": body.comment},
        ip=get_client_ip(request),
    )
    await notify_staff(
        db=db,
        user_id=deal.manager_id,
        title="Сделка отклонена",
        body=f"Сделка на {deal.total} ₽ отклонена: {body.comment}",
        entity_type="deals",
        entity_id=str(deal_id),
        action_url=f"/deals/{deal_id}",
    )
    await db.commit()
    return {"detail": "Сделка отклонена"}


@router.get("/approval/restructurings")
async def list_pending_restructurings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[RestructuringResponse]:
    rows = await db.execute(
        select(Restructuring)
        .where(Restructuring.status == RestructuringStatus.pending)
        .order_by(Restructuring.created_at)
    )
    return [RestructuringResponse.model_validate(r) for r in rows.scalars().all()]


@router.post("/approval/restructurings/{r_id}/approve")
async def approve_restructuring(
    r_id: uuid.UUID,
    body: ApprovalDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    r = await db.get(Restructuring, r_id)
    if not r:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if r.status != RestructuringStatus.pending:
        raise HTTPException(status_code=400, detail="Запрос уже обработан")

    r.status = RestructuringStatus.approved
    r.approved_by = current_user.id
    r.decision_comment = body.comment
    r.decided_at = datetime.now(timezone.utc)

    if r.new_schedule:
        rows = await db.execute(
            select(PaymentSchedule).where(PaymentSchedule.deal_id == r.deal_id)
        )
        for ps in rows.scalars().all():
            await db.delete(ps)
        await db.flush()

        for item in r.new_schedule:
            ps = PaymentSchedule(
                deal_id=r.deal_id,
                installment_number=item["installment_number"],
                due_date=date.fromisoformat(item["due_date"]),
                amount=Decimal(str(item["amount"])),
                installment_type=item.get("installment_type", "principal"),
            )
            db.add(ps)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="RESTRUCTURING_APPROVED",
        entity="restructurings",
        entity_id=str(r_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Реструктуризация одобрена"}


@router.post("/approval/restructurings/{r_id}/reject")
async def reject_restructuring(
    r_id: uuid.UUID,
    body: RejectDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    r = await db.get(Restructuring, r_id)
    if not r:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if r.status != RestructuringStatus.pending:
        raise HTTPException(status_code=400, detail="Запрос уже обработан")

    r.status = RestructuringStatus.rejected
    r.approved_by = current_user.id
    r.decision_comment = body.comment
    r.decided_at = datetime.now(timezone.utc)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="RESTRUCTURING_REJECTED",
        entity="restructurings",
        entity_id=str(r_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Реструктуризация отклонена"}


# ─── Team management ─────────────────────────────────────────────────────────


@router.get("/team", response_model=list[ManagerPortfolioItem])
async def get_team(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> list[ManagerPortfolioItem]:
    rows = await db.execute(
        select(
            User.id,
            User.name,
            func.count(Deal.id).filter(Deal.status == DealStatus.active).label("active"),
            func.count(Deal.id).filter(Deal.status == DealStatus.overdue).label("overdue"),
            func.coalesce(func.sum(Deal.total).filter(Deal.status == DealStatus.active), 0).label("portfolio"),
            func.max(AuditLog.created_at).label("last_activity"),
        )
        .outerjoin(Deal, and_(Deal.manager_id == User.id))
        .outerjoin(AuditLog, AuditLog.user_id == User.id)
        .where(User.role == UserRole.manager)
        .where(User.is_active == True)  # noqa
        .group_by(User.id, User.name)
    )
    return [
        ManagerPortfolioItem(
            manager_id=r.id,
            manager_name=r.name,
            active_deals=r.active or 0,
            overdue_deals=r.overdue or 0,
            total_portfolio=Decimal(str(r.portfolio)),
            last_activity=r.last_activity,
        )
        for r in rows.all()
    ]


@router.post("/team/reassign")
async def reassign(
    body: ReassignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    new_manager = await db.get(User, body.new_manager_id)
    if not new_manager or new_manager.role != UserRole.manager:
        raise HTTPException(status_code=400, detail="Указанный пользователь не является менеджером")

    if body.client_ids:
        await db.execute(
            update(Client)
            .where(Client.id.in_(body.client_ids))
            .values(manager_id=body.new_manager_id)
        )
    if body.deal_ids:
        await db.execute(
            update(Deal)
            .where(Deal.id.in_(body.deal_ids))
            .values(manager_id=body.new_manager_id)
        )

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="REASSIGN",
        entity="clients",
        entity_id=None,
        new_val={
            "new_manager_id": str(body.new_manager_id),
            "client_ids": [str(c) for c in body.client_ids],
            "deal_ids": [str(d) for d in body.deal_ids],
        },
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Перераспределение выполнено"}


# ─── Audit log ───────────────────────────────────────────────────────────────


@router.get("/sb-control")
async def sb_control(
    status_filter: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    """Director view: all overdue cases with last contact date and SB employee stats."""
    from backend.models.overdue import ContactLog, OverdueCaseStatus

    # Red zone threshold from settings
    red_setting = (
        await db.execute(select(SystemSetting.value).where(SystemSetting.key == "red_zone_days"))
    ).scalar_one_or_none()
    red_zone_days = int(red_setting) if red_setting else 14
    red_cutoff = datetime.now(timezone.utc) - timedelta(days=red_zone_days)

    # Last contact subquery
    last_contact_subq = (
        select(ContactLog.case_id, func.max(ContactLog.created_at).label("last_contact"))
        .group_by(ContactLog.case_id)
        .subquery()
    )

    query = (
        select(
            OverdueCase.id,
            OverdueCase.deal_id,
            OverdueCase.sb_user_id,
            OverdueCase.status,
            OverdueCase.total_debt,
            OverdueCase.days_overdue,
            OverdueCase.created_at,
            last_contact_subq.c.last_contact,
            User.name.label("sb_name"),
        )
        .outerjoin(last_contact_subq, OverdueCase.id == last_contact_subq.c.case_id)
        .outerjoin(User, OverdueCase.sb_user_id == User.id)
    )
    if status_filter:
        query = query.where(OverdueCase.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    rows = await db.execute(
        query
        .order_by(OverdueCase.total_debt.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    for row in rows.all():
        is_red_zone = (
            row.last_contact is None
            or row.last_contact < red_cutoff
        ) and row.status in ("new", "in_progress")
        items.append({
            "id": str(row.id),
            "deal_id": str(row.deal_id),
            "sb_user_id": str(row.sb_user_id) if row.sb_user_id else None,
            "sb_name": row.sb_name or "Не назначен",
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "total_debt": float(row.total_debt),
            "days_overdue": row.days_overdue,
            "last_contact": row.last_contact.isoformat() if row.last_contact else None,
            "is_red_zone": is_red_zone,
            "created_at": row.created_at.isoformat(),
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/audit", response_model=PaginatedResponse[AuditLogItem])
async def get_audit_log(
    user_id: uuid.UUID | None = None,
    entity: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> PaginatedResponse[AuditLogItem]:
    query = (
        select(AuditLog, User.name.label("user_name"))
        .outerjoin(User, AuditLog.user_id == User.id)
    )
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if entity:
        query = query.where(AuditLog.entity == entity)
    if action:
        query = query.where(AuditLog.action == action)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    count_query = select(func.count()).select_from(
        select(AuditLog).where(
            *([AuditLog.user_id == user_id] if user_id else []),
            *([AuditLog.entity == entity] if entity else []),
            *([AuditLog.action == action] if action else []),
            *([AuditLog.created_at >= date_from] if date_from else []),
            *([AuditLog.created_at <= date_to] if date_to else []),
        ).subquery()
    )
    total = (await db.execute(count_query)).scalar_one()

    rows = await db.execute(query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset))

    items = []
    for log, user_name in rows.all():
        item = AuditLogItem.model_validate(log)
        item.user_name = user_name
        items.append(item)

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


# ─── Settings ────────────────────────────────────────────────────────────────


@router.post("/audit/export")
async def export_audit_log(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
):
    from fastapi.responses import Response
    from backend.services.excel_exporter import export_audit_log as _export

    query = select(AuditLog)
    if body.get("entity"):
        query = query.where(AuditLog.entity == body["entity"])
    if body.get("action"):
        query = query.where(AuditLog.action == body["action"])
    query = query.order_by(AuditLog.created_at.desc()).limit(5000)

    rows = (await db.execute(query)).scalars().all()
    data = [
        {
            "id": r.id,
            "user_id": str(r.user_id) if r.user_id else "",
            "action": r.action,
            "entity": r.entity,
            "entity_id": str(r.entity_id) if r.entity_id else "",
            "ip": r.ip or "",
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    xlsx = _export(data)
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="audit_log.xlsx"'},
    )


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    setting = (
        await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    ).scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    return {"key": setting.key, "value": setting.value}


@router.patch("/settings/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    setting = (
        await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    ).scalar_one_or_none()

    if setting:
        old_val = setting.value
        setting.value = body.value
        setting.updated_by = current_user.id
    else:
        setting = SystemSetting(key=key, value=body.value, updated_by=current_user.id)
        db.add(setting)
        old_val = None

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="SETTING_UPDATED",
        entity="system_settings",
        entity_id=str(setting.id) if setting.id else None,
        old_val={"value": old_val},
        new_val={"key": key, "value": body.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Настройка обновлена"}


# ─── User management ─────────────────────────────────────────────────────────


@router.get("/users", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    role: UserRole | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> PaginatedResponse[UserListResponse]:
    query = select(User)
    if role:
        query = query.where(User.role == role)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(query.order_by(User.name).limit(limit).offset(offset))
    users = rows.scalars().all()

    return PaginatedResponse(
        items=[UserListResponse.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> UserResponse:
    existing = (
        await db.execute(select(User).where(User.phone == body.phone))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким телефоном уже существует")

    user = User(
        name=body.name,
        phone=body.phone,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="CREATE",
        entity="users",
        entity_id=None,
        new_val={"name": body.name, "role": body.role.value},
        ip=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    allowed = {"name", "phone", "is_active"}
    update_data = {k: v for k, v in body.items() if k in allowed}
    for field, value in update_data.items():
        setattr(user, field, value)

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="UPDATE",
        entity="users",
        entity_id=str(user_id),
        new_val=update_data,
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Пользователь обновлён"}


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя деактивировать собственный аккаунт")

    user.is_active = False
    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="DEACTIVATE",
        entity="users",
        entity_id=str(user_id),
        ip=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Пользователь деактивирован"}
