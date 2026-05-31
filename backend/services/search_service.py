"""Global search and client profile helpers."""
import re
import uuid
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.client import Client
from backend.models.deal import Deal
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.payment import PaymentSchedule
from backend.models.user import User, UserRole
from backend.services.deal_display import deal_purchase_summary, deal_params_dict
from backend.schemas.search import (
    ClientDealBrief,
    ClientOverdueCaseBrief,
    ScheduleBrief,
    SearchCaseBrief,
    SearchClientHit,
)


def client_text_filter(q: str):
    like = f"%{q}%"
    conditions = [
        Client.full_name.ilike(like),
        Client.phone.ilike(like),
    ]
    digits = re.sub(r"\D", "", q)
    if len(digits) >= 4:
        conditions.append(Client.phone.ilike(f"%{digits}%"))
    if len(q) >= 2:
        conditions.append(Client.passport.ilike(like))
    return or_(*conditions)


async def client_has_open_sb_case(db: AsyncSession, client_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(OverdueCase.id)
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .where(Deal.client_id == client_id)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _cases_for_client(
    db: AsyncSession, client_id: uuid.UUID, sb_only_open: bool
) -> list[SearchCaseBrief]:
    query = (
        select(OverdueCase, Deal)
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .where(Deal.client_id == client_id)
    )
    if sb_only_open:
        query = query.where(OverdueCase.status != OverdueCaseStatus.closed)

    rows = await db.execute(query.order_by(OverdueCase.days_overdue.desc()))
    return [
        SearchCaseBrief(
            case_id=case.id,
            deal_id=deal.id,
            status=case.status.value,
            total_debt=Decimal(str(case.total_debt)),
            days_overdue=case.days_overdue,
            sb_user_id=case.sb_user_id,
            deal_type=deal.type.value,
            deal_status=deal.status.value,
            deal_total=Decimal(str(deal.total)),
        )
        for case, deal in rows.all()
    ]


async def _deals_as_cases_for_client(
    db: AsyncSession, client_id: uuid.UUID
) -> list[SearchCaseBrief]:
    deals = (
        await db.execute(select(Deal).where(Deal.client_id == client_id).order_by(Deal.created_at.desc()))
    ).scalars().all()

    case_by_deal: dict[uuid.UUID, OverdueCase] = {}
    oc_rows = await db.execute(
        select(OverdueCase).join(Deal, OverdueCase.deal_id == Deal.id).where(Deal.client_id == client_id)
    )
    for oc in oc_rows.scalars().all():
        case_by_deal[oc.deal_id] = oc

    items: list[SearchCaseBrief] = []
    for deal in deals:
        oc = case_by_deal.get(deal.id)
        items.append(
            SearchCaseBrief(
                case_id=oc.id if oc else None,
                deal_id=deal.id,
                status=oc.status.value if oc else None,
                total_debt=Decimal(str(oc.total_debt)) if oc else None,
                days_overdue=oc.days_overdue if oc else None,
                sb_user_id=oc.sb_user_id if oc else None,
                deal_type=deal.type.value,
                deal_status=deal.status.value,
                deal_total=Decimal(str(deal.total)),
            )
        )
    return items


async def search_clients(
    db: AsyncSession,
    current_user: User,
    q: str,
    limit: int,
) -> list[SearchClientHit]:
    text_filter = client_text_filter(q)
    hits: list[SearchClientHit] = []

    if current_user.role == UserRole.manager:
        client_rows = await db.execute(
            select(Client).where(text_filter).limit(limit)
        )
        for client in client_rows.scalars().all():
            cases = await _deals_as_cases_for_client(db, client.id)
            hits.append(
                SearchClientHit(
                    id=client.id,
                    full_name=client.full_name,
                    phone=client.phone,
                    cases=cases,
                )
            )

    elif current_user.role == UserRole.sb:
        client_rows = await db.execute(
            select(Client)
            .join(Deal, Deal.client_id == Client.id)
            .join(OverdueCase, OverdueCase.deal_id == Deal.id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
            .where(text_filter)
            .distinct()
            .limit(limit)
        )
        for client in client_rows.scalars().all():
            cases = await _cases_for_client(db, client.id, sb_only_open=True)
            if cases:
                hits.append(
                    SearchClientHit(
                        id=client.id,
                        full_name=client.full_name,
                        phone=client.phone,
                        cases=cases,
                    )
                )

    else:
        client_rows = await db.execute(
            select(Client).where(text_filter).limit(limit)
        )
        for client in client_rows.scalars().all():
            cases = await _deals_as_cases_for_client(db, client.id)
            hits.append(
                SearchClientHit(
                    id=client.id,
                    full_name=client.full_name,
                    phone=client.phone,
                    cases=cases,
                )
            )

    return hits


def hits_to_legacy_clients_deals(hits: list[SearchClientHit]) -> tuple[list[dict], list[dict]]:
    clients: list[dict] = []
    deals: list[dict] = []
    seen_deals: set[str] = set()

    for hit in hits:
        clients.append(
            {
                "id": str(hit.id),
                "full_name": hit.full_name,
                "phone": hit.phone,
            }
        )
        for c in hit.cases:
            did = str(c.deal_id)
            if did not in seen_deals:
                seen_deals.add(did)
                deals.append(
                    {
                        "id": did,
                        "client_id": str(hit.id),
                        "type": c.deal_type,
                        "status": c.deal_status,
                        "total": float(c.deal_total),
                    }
                )
    return clients, deals


async def build_client_profile(
    db: AsyncSession,
    client: Client,
) -> tuple[list[ClientOverdueCaseBrief], list[ClientDealBrief]]:
    oc_rows = await db.execute(
        select(OverdueCase, Deal)
        .join(Deal, OverdueCase.deal_id == Deal.id)
        .where(Deal.client_id == client.id)
        .where(OverdueCase.status != OverdueCaseStatus.closed)
        .order_by(OverdueCase.days_overdue.desc())
    )
    overdue_cases = [
        ClientOverdueCaseBrief(
            case_id=case.id,
            deal_id=deal.id,
            status=case.status.value,
            total_debt=Decimal(str(case.total_debt)),
            days_overdue=case.days_overdue,
            sb_user_id=case.sb_user_id,
        )
        for case, deal in oc_rows.all()
    ]

    deal_rows = await db.execute(
        select(Deal)
        .where(Deal.client_id == client.id)
        .options(
            selectinload(Deal.payment_schedules),
            selectinload(Deal.params),
            selectinload(Deal.manager),
        )
        .order_by(Deal.created_at.desc())
    )
    deals_list: list[ClientDealBrief] = []
    case_by_deal = {oc.deal_id: oc for oc in overdue_cases}

    for deal in deal_rows.scalars().all():
        oc = case_by_deal.get(deal.id)
        schedules = sorted(deal.payment_schedules, key=lambda s: s.installment_number)
        manager = deal.manager
        params = deal_params_dict(deal)
        deals_list.append(
            ClientDealBrief(
                deal_id=deal.id,
                deal_type=deal.type.value,
                deal_status=deal.status.value,
                deal_total=Decimal(str(deal.total)),
                duration_months=deal.duration_months,
                start_date=deal.start_date,
                product_description=deal.product_description,
                purchase_summary=deal_purchase_summary(
                    deal.type, deal.principal, deal.product_description, params
                ),
                manager_id=deal.manager_id,
                manager_name=manager.name if manager else "—",
                case_id=oc.case_id if oc else None,
                case_status=oc.status if oc else None,
                schedules=[
                    ScheduleBrief(
                        id=s.id,
                        installment_number=s.installment_number,
                        due_date=s.due_date,
                        amount=Decimal(str(s.amount)),
                        paid_amount=Decimal(str(s.paid_amount)),
                        status=s.status,
                    )
                    for s in schedules
                ],
            )
        )

    return overdue_cases, deals_list
