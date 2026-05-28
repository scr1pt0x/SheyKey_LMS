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
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.client import Client, KycStatus
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService

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
                kyc_status=KycStatus.pending,
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
