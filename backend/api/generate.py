"""Document generation endpoints: contracts, schedules, reports."""
import uuid
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.user import User
from backend.services.excel_exporter import export_audit_log, export_overdue, export_portfolio
from backend.services.pdf_generator import (
    generate_contract_pdf,
    generate_overdue_pdf,
    generate_portfolio_pdf,
    generate_schedule_pdf,
)

router = APIRouter(prefix="/api/documents/generate", tags=["generate"])


class ReportType(str, Enum):
    portfolio = "portfolio"
    overdue = "overdue"


class ExportFormat(str, Enum):
    pdf = "pdf"
    xlsx = "xlsx"


@router.post("/contract/{deal_id}")
async def generate_contract(
    deal_id: uuid.UUID,
    current_user: User = Depends(require_role("manager", "director")),
) -> Response:
    try:
        pdf = await generate_contract_pdf(str(deal_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contract_{deal_id}.pdf"'},
    )


@router.post("/schedule/{deal_id}")
async def generate_schedule(
    deal_id: uuid.UUID,
    current_user: User = Depends(require_role("manager", "director")),
) -> Response:
    try:
        pdf = await generate_schedule_pdf(str(deal_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="schedule_{deal_id}.pdf"'},
    )


@router.post("/report/{report_type}")
async def generate_report(
    report_type: ReportType,
    fmt: ExportFormat = ExportFormat.pdf,
    current_user: User = Depends(require_role("director")),
) -> Response:
    if fmt == ExportFormat.pdf:
        if report_type == ReportType.portfolio:
            content = await generate_portfolio_pdf()
        else:
            content = await generate_overdue_pdf()
        media_type = "application/pdf"
        filename = f"report_{report_type.value}.pdf"
    else:
        if report_type == ReportType.portfolio:
            content = export_portfolio([])
        else:
            content = export_overdue([])
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"report_{report_type.value}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
