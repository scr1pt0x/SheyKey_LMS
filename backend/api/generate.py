"""Document generation endpoints: murabaha DOCX, director reports."""
import uuid
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.access import require_deal_access
from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.user import User
from backend.services.excel_exporter import export_audit_log, export_overdue, export_portfolio
from backend.services.pdf_generator import generate_overdue_pdf, generate_portfolio_pdf

router = APIRouter(prefix="/api/documents/generate", tags=["generate"])


class ReportType(str, Enum):
    portfolio = "portfolio"
    overdue = "overdue"


class ExportFormat(str, Enum):
    pdf = "pdf"
    xlsx = "xlsx"


@router.post("/murabaha-docx/{deal_id}")
async def generate_murabaha_docx(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "director")),
) -> Response:
    from backend.models.deal import Deal

    from backend.services.murabaha_contract_service import generate_murabaha_docx_for_deal

    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    await require_deal_access(db, deal, current_user)
    try:
        content = await generate_murabaha_docx_for_deal(db, deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="murabaha_{deal_id}.zip"'},
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
