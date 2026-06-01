"""
File-based import: upload CSV or XLSX exported from Google Sheets.
No Google API credentials needed — user just downloads the file manually.

Endpoints:
  POST /api/director/import/preview   → parse file, return first 10 rows + detected columns
  POST /api/director/import/clients   → actually import clients into DB
"""
import csv
import io
import uuid
import re
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.client import Client
from backend.models.deal import Deal, DealStatus, DealType, DealParam
from backend.models.payment import Payment, PaymentMethod, PaymentSchedule, PaymentStatus
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService
from backend.services.payment_calculator import generate_schedule

router = APIRouter(prefix="/api/director/import", tags=["import"])

# ─── Column name aliases ──────────────────────────────────────────────────────

ALIASES = {
    "full_name": ["фио", "full_name", "имя", "клиент", "ф.и.о", "ф.и.о.", "name"],
    "phone":     ["телефон", "phone", "тел", "моб", "мобильный", "номер", "тел.", "mobile"],
    "passport":  ["паспорт", "passport", "серия", "документ", "удостоверение"],
    "address":   ["адрес", "address", "место жительства", "прописка"],
}


def detect_column(header: str, mapping: dict[str, list[str]]) -> str | None:
    """Return field name if header matches any known alias."""
    h = header.strip().lower()
    for field, aliases in mapping.items():
        if any(h.startswith(a) or a in h for a in aliases):
            return field
    return None


def build_column_map(headers: list[str]) -> dict[str, int]:
    """Return {field: column_index} for detected columns."""
    result: dict[str, int] = {}
    for i, h in enumerate(headers):
        field = detect_column(h, ALIASES)
        if field and field not in result:
            result[field] = i
    return result


def normalize_phone(raw: str) -> str:
    digits = "".join(c for c in str(raw) if c.isdigit())
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    return "+" + digits if digits else raw


def parse_file(content: bytes, filename: str) -> tuple[list[str], list[list[str]]]:
    """
    Returns (headers, rows) from CSV or XLSX.
    Raises ValueError on unsupported format.
    """
    name = filename.lower()

    if name.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise ValueError("Файл пустой")
        return rows[0], rows[1:]

    elif name.endswith((".xlsx", ".xls")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        all_rows = [[str(cell.value or "").strip() for cell in row] for row in ws.iter_rows()]
        wb.close()
        if not all_rows:
            raise ValueError("Файл пустой")
        return all_rows[0], all_rows[1:]

    else:
        raise ValueError("Поддерживаются только .csv, .xlsx и .xls файлы")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class PreviewResponse(BaseModel):
    headers: list[str]
    column_map: dict[str, int]
    preview_rows: list[dict[str, str]]
    total_rows: int
    detected_fields: list[str]
    missing_required: list[str]


class ImportResult(BaseModel):
    imported: int
    skipped_duplicate: int
    skipped_no_name: int
    skipped_no_phone: int
    errors: list[str]
    manager_id: str | None


class DealImportResult(BaseModel):
    clients_imported: int
    deals_imported: int
    deals_skipped: int
    errors: list[str]


# ─── Deal column detection ───────────────────────────────────────────────────

DEAL_ALIASES = {
    "client_identifier": ["клиент", "фио", "имя", "телефон", "client", "заёмщик"],
    "deal_type":        ["тип", "type", "вид сделки", "продукт"],
    "principal":        ["сумма", "основной долг", "principal", "amount", "тело"],
    "markup":           ["наценка", "markup", "маржа"],
    "monthly_rent":     ["аренда", "ежемесячный платёж", "rent"],
    "buyout_amount":    ["выкуп", "buyout"],
    "duration_months":  ["срок", "мес", "months", "duration"],
    "start_date":       ["дата начала", "дата выдачи", "start", "выдан"],
    "status":           ["статус", "status", "состояние"],
    "paid_installments":["оплачено", "выплачено", "paid", "погашено"],
}

DEAL_TYPE_MAP = {
    "мурабаха": "murabaha", "murabaha": "murabaha",
    "иджара": "ijara", "ijara": "ijara", "аренда": "ijara",
}

DEAL_STATUS_MAP = {
    "активна": "active", "активная": "active", "active": "active",
    "закрыта": "closed", "closed": "closed", "погашена": "closed",
    "просрочена": "overdue", "overdue": "overdue",
}


def _detect_deal_column(header: str) -> str | None:
    h = header.strip().lower()
    for field, aliases in DEAL_ALIASES.items():
        if any(a in h for a in aliases):
            return field
    return None


def _parse_num(v: Any) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    clean = re.sub(r"[^\d.,]", "", str(v)).replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def _parse_dt(v: Any) -> date | None:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _next_month_local(d: date, months: int) -> date:
    from calendar import monthrange
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/preview", response_model=PreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("director")),
) -> PreviewResponse:
    content = await file.read()
    try:
        headers, rows = parse_file(content, file.filename or "file.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    column_map = build_column_map(headers)
    detected = list(column_map.keys())
    missing = [f for f in ["full_name", "phone"] if f not in column_map]

    preview: list[dict[str, str]] = []
    for row in rows[:10]:
        row_dict: dict[str, str] = {}
        for field, idx in column_map.items():
            row_dict[field] = row[idx] if idx < len(row) else ""
        preview.append(row_dict)

    return PreviewResponse(
        headers=headers,
        column_map=column_map,
        preview_rows=preview,
        total_rows=len(rows),
        detected_fields=detected,
        missing_required=missing,
    )


@router.post("/clients", response_model=ImportResult)
async def import_clients(
    file: UploadFile = File(...),
    manager_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> ImportResult:
    content = await file.read()
    try:
        headers, rows = parse_file(content, file.filename or "file.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    column_map = build_column_map(headers)
    if "full_name" not in column_map or "phone" not in column_map:
        raise HTTPException(
            status_code=400,
            detail="Не удалось определить колонки ФИО и Телефон. Проверьте заголовки таблицы.",
        )

    # Resolve manager
    if manager_id:
        mgr = await db.get(User, uuid.UUID(manager_id))
        resolved_manager_id = mgr.id if mgr else None
    else:
        result = await db.execute(
            select(User.id).where(User.role == UserRole.manager).where(User.is_active == True).limit(1)  # noqa
        )
        resolved_manager_id = result.scalar_one_or_none()

    if not resolved_manager_id:
        raise HTTPException(status_code=400, detail="Нет активных менеджеров в системе. Сначала создайте менеджера.")

    # Load existing phones to detect duplicates
    existing_phones_result = await db.execute(select(Client.phone))
    existing_phones: set[str] = {row[0] for row in existing_phones_result.all()}

    imported = 0
    skipped_dup = 0
    skipped_no_name = 0
    skipped_no_phone = 0
    errors: list[str] = []

    def get_col(row: list[str], field: str) -> str:
        idx = column_map.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    for i, row in enumerate(rows, start=2):
        try:
            full_name = get_col(row, "full_name")
            phone_raw = get_col(row, "phone")
            passport = get_col(row, "passport") or None
            address = get_col(row, "address") or None

            if not full_name:
                skipped_no_name += 1
                continue
            if not phone_raw:
                skipped_no_phone += 1
                continue

            phone = normalize_phone(phone_raw)

            if phone in existing_phones:
                skipped_dup += 1
                continue

            client = Client(
                manager_id=resolved_manager_id,
                full_name=full_name,
                phone=phone,
                passport=passport,
                address=address,
            )
            db.add(client)
            existing_phones.add(phone)
            imported += 1

        except Exception as exc:
            errors.append(f"Строка {i}: {exc}")
            if len(errors) >= 20:
                errors.append("…слишком много ошибок, остальные пропущены")
                break

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="BULK_IMPORT",
        entity="clients",
        new_val={"imported": imported, "skipped": skipped_dup, "source": file.filename},
    )
    await db.commit()

    return ImportResult(
        imported=imported,
        skipped_duplicate=skipped_dup,
        skipped_no_name=skipped_no_name,
        skipped_no_phone=skipped_no_phone,
        errors=errors,
        manager_id=str(resolved_manager_id) if resolved_manager_id else None,
    )


@router.post("/deals", response_model=DealImportResult)
async def import_deals(
    file: UploadFile = File(...),
    manager_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("director")),
) -> DealImportResult:
    """
    Import deals (and clients if not yet in DB) from a XLSX/CSV file.
    The file should contain deal rows with client identifier, type, amounts, dates.
    """
    content = await file.read()
    try:
        headers, rows = parse_file(content, file.filename or "file.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Resolve manager
    if manager_id:
        mgr = await db.get(User, uuid.UUID(manager_id))
        resolved_manager_id = mgr.id if mgr else None
    else:
        result = await db.execute(
            select(User.id).where(User.role == UserRole.manager).where(User.is_active == True).limit(1)  # noqa
        )
        resolved_manager_id = result.scalar_one_or_none()

    if not resolved_manager_id:
        raise HTTPException(status_code=400, detail="Нет активных менеджеров.")

    # Detect deal columns
    col_map: dict[str, int] = {}
    for i, h in enumerate(headers):
        field = _detect_deal_column(h)
        if field and field not in col_map:
            col_map[field] = i

    if "principal" not in col_map:
        raise HTTPException(
            status_code=400,
            detail="Не найдена колонка суммы сделки (Сумма / Principal). Проверьте заголовки.",
        )

    def gcol(row: list[str], field: str) -> str:
        idx = col_map.get(field)
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    # Load existing clients for matching
    clients_q = await db.execute(select(Client.phone, Client.full_name, Client.id))
    clients_by_phone: dict[str, uuid.UUID] = {}
    clients_by_name: dict[str, uuid.UUID] = {}
    for phone, name, cid in clients_q.all():
        if phone:
            clients_by_phone[phone] = cid
        if name:
            clients_by_name[name.lower()] = cid

    today = datetime.now(timezone.utc).date()
    deals_imported = 0
    deals_skipped = 0
    errors: list[str] = []
    clients_created = 0

    for i, row in enumerate(rows, start=2):
        try:
            principal = _parse_num(gcol(row, "principal"))
            if not principal:
                deals_skipped += 1
                continue

            duration = int(_parse_num(gcol(row, "duration_months")) or 12)
            markup = _parse_num(gcol(row, "markup")) or 0.0
            monthly_rent = _parse_num(gcol(row, "monthly_rent"))
            buyout = _parse_num(gcol(row, "buyout_amount"))
            start_date = _parse_dt(gcol(row, "start_date")) or today
            paid_count = int(_parse_num(gcol(row, "paid_installments")) or 0)

            type_raw = gcol(row, "deal_type").lower()
            deal_type_str = DEAL_TYPE_MAP.get(type_raw, "murabaha")
            deal_type = DealType(deal_type_str)

            status_raw = gcol(row, "status").lower()
            status_str = DEAL_STATUS_MAP.get(status_raw, "active")

            # Resolve client
            client_raw = gcol(row, "client_identifier")
            client_id: uuid.UUID | None = None

            digits = re.sub(r"[^\d]", "", client_raw)
            if digits:
                for phone_fmt in [f"+7{digits[-10:]}", f"+{digits}"]:
                    client_id = clients_by_phone.get(phone_fmt)
                    if client_id:
                        break

            if not client_id:
                client_id = clients_by_name.get(client_raw.lower())

            if not client_id:
                errors.append(f"Строка {i}: клиент '{client_raw}' не найден в системе")
                deals_skipped += 1
                continue

            # Calculate total
            if deal_type == DealType.murabaha:
                total = principal + markup
            elif deal_type == DealType.ijara:
                total = (monthly_rent or 0) * duration + (buyout or 0)
            else:
                total = principal

            # Determine actual status
            if status_str == "closed":
                final_status = DealStatus.closed
            elif status_str == "overdue":
                final_status = DealStatus.overdue
            else:
                overdue_cutoff = _next_month_local(start_date, paid_count + 1) if paid_count < duration else today
                final_status = DealStatus.overdue if overdue_cutoff < today and paid_count < duration else DealStatus.active

            end_date = _next_month_local(start_date, duration)

            deal = Deal(
                client_id=client_id,
                manager_id=resolved_manager_id,
                type=deal_type,
                status=final_status,
                principal=Decimal(str(principal)),
                markup=Decimal(str(markup)),
                total=Decimal(str(total)),
                duration_months=duration,
                start_date=start_date,
                end_date=end_date,
                approved_by=resolved_manager_id,
                approved_at=datetime.now(timezone.utc),
            )
            db.add(deal)
            await db.flush()

            # Deal params
            if deal_type == DealType.murabaha:
                params = {
                    "principal": str(principal),
                    "markup": str(markup),
                    "duration_months": duration,
                    "down_payment_amount": "0",
                    "payday": start_date.day,
                }
            elif deal_type == DealType.ijara:
                params = {"monthly_rent": str(monthly_rent or 0), "duration_months": duration,
                          "buyout_amount": str(buyout) if buyout else None}
            else:
                params = {"principal": str(principal), "duration_months": duration}

            for key, value in params.items():
                if value is not None:
                    db.add(DealParam(deal_id=deal.id, key=key, value=value))

            # Generate schedule
            schedule_items = generate_schedule(deal_type.value, params, start_date)

            for j, sched_item in enumerate(schedule_items):
                is_paid = j < paid_count
                is_overdue = not is_paid and sched_item.due_date < today
                sched_status = PaymentStatus.paid if is_paid else (PaymentStatus.overdue if is_overdue else PaymentStatus.pending)
                paid_amount = sched_item.amount if is_paid else Decimal("0")

                sched = PaymentSchedule(
                    deal_id=deal.id,
                    installment_number=sched_item.installment_number,
                    due_date=sched_item.due_date,
                    amount=sched_item.amount,
                    paid_amount=paid_amount,
                    status=sched_status,
                    installment_type=sched_item.installment_type,
                )
                db.add(sched)
                await db.flush()

                if is_paid:
                    db.add(Payment(
                        schedule_id=sched.id,
                        deal_id=deal.id,
                        amount=sched_item.amount,
                        paid_at=datetime.combine(sched_item.due_date, datetime.min.time(), tzinfo=timezone.utc),
                        method=PaymentMethod.transfer,
                        recorded_by=resolved_manager_id,
                    ))

            if final_status == DealStatus.overdue:
                from backend.services.overdue_case_service import sync_overdue_case_for_deal
                await sync_overdue_case_for_deal(db, deal.id)

            deals_imported += 1

        except Exception as exc:
            errors.append(f"Строка {i}: {exc}")
            deals_skipped += 1
            if len(errors) >= 20:
                errors.append("…слишком много ошибок, остальные пропущены")
                break

    await AuditService.log(
        db=db,
        user_id=str(current_user.id),
        action="BULK_IMPORT",
        entity="deals",
        new_val={"imported": deals_imported, "skipped": deals_skipped, "source": file.filename},
    )
    await db.commit()

    return DealImportResult(
        clients_imported=clients_created,
        deals_imported=deals_imported,
        deals_skipped=deals_skipped,
        errors=errors,
    )
