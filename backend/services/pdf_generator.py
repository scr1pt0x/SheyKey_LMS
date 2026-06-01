"""
PDF generation service using WeasyPrint + Jinja2 (director reports).
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from backend.core.database import AsyncSessionLocal

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


def _render_pdf(template_name: str, context: dict) -> bytes:
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "PDF generation requires system libraries (pango, gobject). "
            "On macOS: brew install pango. "
            f"Original error: {exc}"
        ) from exc

    template = _jinja_env.get_template(template_name)
    html_content = template.render(**context)
    return HTML(string=html_content).write_pdf()


async def generate_portfolio_pdf() -> bytes:
    """Generate a portfolio overview report PDF."""
    from sqlalchemy import func, select

    from backend.models.deal import Deal, DealStatus

    async with AsyncSessionLocal() as db:
        stats = (
            await db.execute(
                select(
                    Deal.status,
                    Deal.type,
                    func.count().label("cnt"),
                    func.coalesce(func.sum(Deal.total), 0).label("total"),
                )
                .group_by(Deal.status, Deal.type)
            )
        ).all()

    context = {"stats": stats, "generated_at": __import__("datetime").datetime.now()}
    return _render_pdf("report_portfolio.html", context)


async def generate_overdue_pdf() -> bytes:
    """Generate an overdue cases report PDF."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.models.overdue import OverdueCase, OverdueCaseStatus
    from backend.models.deal import Deal
    from backend.models.client import Client

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(OverdueCase, Deal, Client)
            .join(Deal, OverdueCase.deal_id == Deal.id)
            .join(Client, Deal.client_id == Client.id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
            .order_by(OverdueCase.total_debt.desc())
        )
        cases = [
            {"case": c, "deal": d, "client": cl}
            for c, d, cl in rows.all()
        ]

    context = {"cases": cases, "generated_at": __import__("datetime").datetime.now()}
    return _render_pdf("report_overdue.html", context)
