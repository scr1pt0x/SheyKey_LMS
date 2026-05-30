"""
Step 3: Bulk insert clean data into PostgreSQL.
Inserts clients, deals, payment schedules and partial payments.
Run: DATABASE_URL=... python load.py
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

CLEAN_FILE = Path(__file__).parent / "clean_data" / "clean.json"
DATABASE_URL = os.environ["DATABASE_URL"]
DEFAULT_MANAGER_ID = os.environ.get("DEFAULT_MANAGER_ID", "")


def _next_month(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    from calendar import monthrange
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _generate_murabaha_schedule(
    deal_id: str,
    principal: float,
    markup: float,
    duration_months: int,
    start_date: date,
) -> list[dict]:
    total = Decimal(str(principal)) + Decimal(str(markup))
    base = (total / duration_months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    schedule = []
    accumulated = Decimal("0")
    for i in range(1, duration_months + 1):
        due = _next_month(start_date, i)
        amount = base if i < duration_months else (total - accumulated)
        accumulated += amount
        schedule.append({
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "installment_number": i,
            "due_date": due.isoformat(),
            "amount": str(amount.quantize(Decimal("0.01"))),
            "paid_amount": "0.00",
            "installment_type": "principal",
        })
    return schedule


def _generate_ijara_schedule(
    deal_id: str,
    monthly_rent: float,
    duration_months: int,
    start_date: date,
    buyout_amount: float | None = None,
) -> list[dict]:
    schedule = []
    for i in range(1, duration_months + 1):
        due = _next_month(start_date, i)
        schedule.append({
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "installment_number": i,
            "due_date": due.isoformat(),
            "amount": str(Decimal(str(monthly_rent)).quantize(Decimal("0.01"))),
            "paid_amount": "0.00",
            "installment_type": "rent",
        })
    if buyout_amount:
        due = _next_month(start_date, duration_months + 1)
        schedule.append({
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "installment_number": duration_months + 1,
            "due_date": due.isoformat(),
            "amount": str(Decimal(str(buyout_amount)).quantize(Decimal("0.01"))),
            "paid_amount": "0.00",
            "installment_type": "buyout",
        })
    return schedule


async def load() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    data = json.loads(CLEAN_FILE.read_text())
    clients = data.get("clients", [])
    deals = data.get("deals", [])

    async with SessionLocal() as db:
        # Resolve manager
        if DEFAULT_MANAGER_ID:
            r = await db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": DEFAULT_MANAGER_ID})
            manager_id = DEFAULT_MANAGER_ID if r.scalar_one_or_none() else None
        else:
            r = await db.execute(text("SELECT id FROM users WHERE role = 'manager' LIMIT 1"))
            row = r.scalar_one_or_none()
            manager_id = str(row) if row else None

        if not manager_id:
            print("ОШИБКА: Нет активных менеджеров. Сначала запустите make seed.")
            return

        print(f"Используется manager_id={manager_id}")

        # ── Insert clients ───────────────────────────────────────────────────
        inserted_clients = 0
        for client in clients:
            await db.execute(
                text("""
                    INSERT INTO clients
                      (id, manager_id, full_name, phone, passport, address, kyc_status, is_archived)
                    VALUES
                      (CAST(:id AS uuid), CAST(:manager_id AS uuid), :full_name, :phone,
                       :passport, :address, 'pending', false)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": client.get("id", str(uuid.uuid4())),
                    "manager_id": manager_id,
                    "full_name": client["full_name"],
                    "phone": client["phone"],
                    "passport": client.get("passport"),
                    "address": client.get("address"),
                },
            )
            inserted_clients += 1

        await db.commit()
        print(f"Клиенты: {inserted_clients} вставлено")

        # ── Insert deals ─────────────────────────────────────────────────────
        today = datetime.now(timezone.utc).date()
        inserted_deals = 0
        inserted_schedules = 0
        inserted_payments = 0

        for deal in deals:
            deal_id = deal.get("id", str(uuid.uuid4()))
            client_id = deal["client_id"]
            deal_type = deal["deal_type"]
            principal = float(deal["principal"])
            markup = float(deal.get("markup") or 0)
            monthly_rent = float(deal["monthly_rent"]) if deal.get("monthly_rent") else None
            buyout_amount = float(deal["buyout_amount"]) if deal.get("buyout_amount") else None
            duration_months = int(deal["duration_months"])
            status = deal.get("status", "active")
            paid_installments = int(deal.get("paid_installments") or 0)

            start_date_str = deal.get("start_date")
            start_date = date.fromisoformat(start_date_str) if start_date_str else today

            # Calculate total
            if deal_type == "murabaha":
                total = principal + markup
            elif deal_type == "ijara":
                rent = monthly_rent or 0
                total = rent * duration_months + (buyout_amount or 0)
            else:
                total = principal

            end_date = _next_month(start_date, duration_months)

            # Determine final deal status
            # If status from Sheets says overdue/closed — use that
            # Otherwise compute from dates and paid installments
            if status == "closed":
                final_status = "closed"
            elif status == "overdue":
                final_status = "overdue"
            elif status == "active":
                # Check if any past-due unpaid schedules exist
                last_due = _next_month(start_date, duration_months - paid_installments)
                if last_due < today and paid_installments < duration_months:
                    final_status = "overdue"
                else:
                    final_status = "active"
            else:
                final_status = "active"

            await db.execute(
                text("""
                    INSERT INTO deals
                      (id, client_id, manager_id, type, status, principal, markup, total,
                       duration_months, start_date, end_date, approved_by, approved_at)
                    VALUES
                      (CAST(:id AS uuid), CAST(:client_id AS uuid), CAST(:manager_id AS uuid),
                       CAST(:type AS deal_type), CAST(:status AS deal_status),
                       :principal, :markup, :total, :duration_months, :start_date, :end_date,
                       CAST(:manager_id AS uuid), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": deal_id,
                    "client_id": client_id,
                    "manager_id": manager_id,
                    "type": deal_type,
                    "status": final_status,
                    "principal": principal,
                    "markup": markup,
                    "total": total,
                    "duration_months": duration_months,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            inserted_deals += 1

            # Generate schedule
            if deal_type == "murabaha":
                schedule = _generate_murabaha_schedule(deal_id, principal, markup, duration_months, start_date)
            elif deal_type == "ijara":
                schedule = _generate_ijara_schedule(deal_id, monthly_rent or 0, duration_months, start_date, buyout_amount)
            else:
                schedule = _generate_murabaha_schedule(deal_id, principal, markup, duration_months, start_date)

            for i, sched in enumerate(schedule):
                due_date = date.fromisoformat(sched["due_date"])
                is_paid = i < paid_installments
                is_overdue = not is_paid and due_date < today

                sched_status = "paid" if is_paid else ("overdue" if is_overdue else "pending")
                paid_amount = sched["amount"] if is_paid else "0.00"

                await db.execute(
                    text("""
                        INSERT INTO payment_schedules
                          (id, deal_id, installment_number, due_date, amount, paid_amount,
                           status, installment_type)
                        VALUES
                          (CAST(:id AS uuid), CAST(:deal_id AS uuid), :installment_number,
                           :due_date, :amount, :paid_amount, CAST(:status AS payment_status),
                           CAST(:installment_type AS installment_type))
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": sched["id"],
                        "deal_id": deal_id,
                        "installment_number": sched["installment_number"],
                        "due_date": due_date.isoformat(),
                        "amount": sched["amount"],
                        "paid_amount": paid_amount,
                        "status": sched_status,
                        "installment_type": sched["installment_type"],
                    },
                )
                inserted_schedules += 1

                # Create payment record for paid installments
                if is_paid:
                    await db.execute(
                        text("""
                            INSERT INTO payments
                              (id, schedule_id, deal_id, amount, paid_at, method, recorded_by)
                            VALUES
                              (CAST(:id AS uuid), CAST(:schedule_id AS uuid),
                               CAST(:deal_id AS uuid), :amount,
                               :paid_at, CAST('transfer' AS payment_method),
                               CAST(:recorded_by AS uuid))
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "schedule_id": sched["id"],
                            "deal_id": deal_id,
                            "amount": sched["amount"],
                            "paid_at": datetime.combine(due_date, datetime.min.time()).isoformat() + "Z",
                            "recorded_by": manager_id,
                        },
                    )
                    inserted_payments += 1

            # Create overdue_case for overdue deals
            if final_status == "overdue":
                overdue_total = sum(
                    float(s["amount"])
                    for i, s in enumerate(schedule)
                    if i >= paid_installments and date.fromisoformat(s["due_date"]) < today
                )
                earliest_due = next(
                    (date.fromisoformat(s["due_date"]) for i, s in enumerate(schedule) if i >= paid_installments),
                    today,
                )
                days_overdue = (today - earliest_due).days

                await db.execute(
                    text("""
                        INSERT INTO overdue_cases (id, deal_id, status, total_debt, days_overdue)
                        VALUES (CAST(:id AS uuid), CAST(:deal_id AS uuid),
                                CAST('new' AS overdue_case_status), :total_debt, :days_overdue)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "deal_id": deal_id,
                        "total_debt": overdue_total,
                        "days_overdue": days_overdue,
                    },
                )

        await db.commit()
        print(f"Сделки: {inserted_deals} вставлено")
        print(f"Строки графика: {inserted_schedules} вставлено")
        print(f"Платежи: {inserted_payments} вставлено")
        print("Загрузка завершена успешно.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load())
