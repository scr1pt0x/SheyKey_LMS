"""Касса менеджера: платежи по рассрочке портфеля + ручные поступления."""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.client import Client
from backend.models.deal import Deal, DealType
from backend.models.manager_cash_entry import ManagerCashEntry, ManagerCashEntryKind
from backend.models.payment import Payment, PaymentMethod


@dataclass
class CashLedgerRow:
    id: str
    entry_type: str
    amount: Decimal
    paid_at: datetime
    method: str
    description: str
    deal_id: uuid.UUID | None
    client_name: str | None


def _payment_method_value(method: PaymentMethod | str) -> str:
    return method.value if hasattr(method, "value") else str(method)


def _installment_description(client_name: str | None, deal: Deal) -> str:
    name = client_name or "Клиент"
    if deal.product_description and str(deal.product_description).strip():
        return f"{name} — {deal.product_description.strip()}"
    type_label = "Мурабаха" if deal.type == DealType.murabaha else "Иджара"
    return f"{name} — {type_label}"


async def _fetch_installment_rows(
    db: AsyncSession,
    manager_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[CashLedgerRow]:
    query = (
        select(Payment, Client.full_name, Deal)
        .join(Deal, Payment.deal_id == Deal.id)
        .join(Client, Deal.client_id == Client.id)
        .where(Deal.manager_id == manager_id)
        .options(selectinload(Deal.params))
    )
    if date_from:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        query = query.where(Payment.paid_at >= start)
    if date_to:
        end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        query = query.where(Payment.paid_at <= end)

    rows = await db.execute(query)
    result: list[CashLedgerRow] = []
    for payment, client_name, deal in rows.all():
        result.append(
            CashLedgerRow(
                id=f"payment-{payment.id}",
                entry_type="installment",
                amount=Decimal(str(payment.amount)),
                paid_at=payment.paid_at,
                method=_payment_method_value(payment.method),
                description=_installment_description(client_name, deal),
                deal_id=deal.id,
                client_name=client_name,
            )
        )
    return result


async def _fetch_manual_rows(
    db: AsyncSession,
    manager_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[CashLedgerRow]:
    try:
        query = select(ManagerCashEntry).where(ManagerCashEntry.manager_id == manager_id)
        if date_from:
            start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
            query = query.where(ManagerCashEntry.paid_at >= start)
        if date_to:
            end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
            query = query.where(ManagerCashEntry.paid_at <= end)

        rows = await db.execute(query)
        result: list[CashLedgerRow] = []
        for entry in rows.scalars().all():
            kind = getattr(entry, "entry_kind", ManagerCashEntryKind.income)
            if hasattr(kind, "value"):
                kind = kind.value
            result.append(
                CashLedgerRow(
                    id=f"manual-{entry.id}",
                    entry_type="expense" if kind == ManagerCashEntryKind.expense.value else "manual",
                    amount=Decimal(str(entry.amount)),
                    paid_at=entry.paid_at,
                    method=_payment_method_value(entry.method),
                    description=entry.description,
                    deal_id=None,
                    client_name=None,
                )
            )
        return result
    except Exception:
        # Таблица ручных поступлений может отсутствовать до миграции 008
        return []


async def build_cash_ledger(
    db: AsyncSession,
    manager_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CashLedgerRow], int]:
    installment = await _fetch_installment_rows(db, manager_id, date_from, date_to)
    manual = await _fetch_manual_rows(db, manager_id, date_from, date_to)
    merged = sorted(installment + manual, key=lambda r: r.paid_at, reverse=True)
    total = len(merged)
    page = merged[offset : offset + limit]
    return page, total


async def cash_balance(
    db: AsyncSession,
    manager_id: uuid.UUID,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Decimal:
    """Остаток кассы: поступления (рассрочка + приходы) минус расходы."""
    income = await _sum_cash_income(db, manager_id, since, until)
    expense = await _sum_cash_expense(db, manager_id, since, until)
    return income - expense


async def _sum_cash_income(
    db: AsyncSession,
    manager_id: uuid.UUID,
    since: datetime | None,
    until: datetime | None,
) -> Decimal:
    q = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Deal, Payment.deal_id == Deal.id)
        .where(Deal.manager_id == manager_id)
    )
    if since is not None:
        q = q.where(Payment.paid_at >= since)
    if until is not None:
        q = q.where(Payment.paid_at <= until)
    payments = Decimal(str((await db.execute(q)).scalar_one()))
    manual = await _sum_manual_by_kind(
        db, manager_id, since, until, ManagerCashEntryKind.income
    )
    return payments + manual


async def _sum_cash_expense(
    db: AsyncSession,
    manager_id: uuid.UUID,
    since: datetime | None,
    until: datetime | None,
) -> Decimal:
    return await _sum_manual_by_kind(
        db, manager_id, since, until, ManagerCashEntryKind.expense
    )


async def _sum_manual_by_kind(
    db: AsyncSession,
    manager_id: uuid.UUID,
    since: datetime | None,
    until: datetime | None,
    kind: ManagerCashEntryKind,
) -> Decimal:
    try:
        q = (
            select(func.coalesce(func.sum(ManagerCashEntry.amount), 0))
            .where(ManagerCashEntry.manager_id == manager_id)
            .where(ManagerCashEntry.entry_kind == kind)
        )
        if since is not None:
            q = q.where(ManagerCashEntry.paid_at >= since)
        if until is not None:
            q = q.where(ManagerCashEntry.paid_at <= until)
        return Decimal(str((await db.execute(q)).scalar_one()))
    except Exception:
        if kind == ManagerCashEntryKind.expense:
            return Decimal("0")
        try:
            q = select(func.coalesce(func.sum(ManagerCashEntry.amount), 0)).where(
                ManagerCashEntry.manager_id == manager_id
            )
            if since is not None:
                q = q.where(ManagerCashEntry.paid_at >= since)
            if until is not None:
                q = q.where(ManagerCashEntry.paid_at <= until)
            return Decimal(str((await db.execute(q)).scalar_one()))
        except Exception:
            return Decimal("0")


async def cash_totals(
    db: AsyncSession,
    manager_id: uuid.UUID,
    day_start: datetime,
    day_end: datetime,
    month_start: datetime,
) -> tuple[Decimal, Decimal, Decimal]:
    """Остаток кассы: сегодня, за месяц, за всё время."""
    today = await cash_balance(db, manager_id, day_start, day_end)
    month = await cash_balance(db, manager_id, month_start, day_end)
    all_time = await cash_balance(db, manager_id, None, None)
    return today, month, all_time


async def create_cash_entry(
    db: AsyncSession,
    manager_id: uuid.UUID,
    *,
    amount: Decimal,
    paid_at: datetime,
    method: PaymentMethod,
    description: str,
    entry_kind: ManagerCashEntryKind,
) -> ManagerCashEntry:
    entry = ManagerCashEntry(
        manager_id=manager_id,
        amount=amount,
        paid_at=paid_at,
        method=method,
        description=description.strip(),
        entry_kind=entry_kind,
    )
    db.add(entry)
    await db.flush()
    return entry


async def create_manual_entry(
    db: AsyncSession,
    manager_id: uuid.UUID,
    *,
    amount: Decimal,
    paid_at: datetime,
    method: PaymentMethod,
    description: str,
) -> ManagerCashEntry:
    return await create_cash_entry(
        db,
        manager_id,
        amount=amount,
        paid_at=paid_at,
        method=method,
        description=description,
        entry_kind=ManagerCashEntryKind.income,
    )
