"""
Auto-report tasks: weekly and monthly PDF reports sent to director email.
"""
import asyncio
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.models.settings import SettingKey, SystemSetting
from backend.services.pdf_generator import generate_portfolio_pdf
from backend.tasks.celery_app import celery_app


def _send_email(to: str, subject: str, body: str, pdf_bytes: bytes, pdf_filename: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    pdf_part = MIMEApplication(pdf_bytes, Name=pdf_filename)
    pdf_part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
    msg.attach(pdf_part)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


@celery_app.task(name="backend.tasks.reports.send_weekly_report")
def send_weekly_report() -> dict:
    return asyncio.run(_send_report("weekly"))


@celery_app.task(name="backend.tasks.reports.send_monthly_report")
def send_monthly_report() -> dict:
    return asyncio.run(_send_report("monthly"))


async def _send_report(period: str) -> dict:
    async with AsyncSessionLocal() as db:
        director_email_setting = (
            await db.execute(
                select(SystemSetting.value).where(SystemSetting.key == SettingKey.DIRECTOR_EMAIL)
            )
        ).scalar_one_or_none()

    director_email = director_email_setting or settings.DIRECTOR_EMAIL
    if not director_email:
        logger.warning(f"No director email configured, skipping {period} report")
        return {"status": "skipped", "reason": "no director email"}

    now = datetime.now(timezone.utc)
    pdf_bytes = await generate_portfolio_pdf()
    filename = f"report_{period}_{now.strftime('%Y%m%d')}.pdf"
    subject = f"LMS: {'Еженедельный' if period == 'weekly' else 'Ежемесячный'} отчёт {now.strftime('%d.%m.%Y')}"

    try:
        _send_email(
            to=director_email,
            subject=subject,
            body=f"Отчёт за {'неделю' if period == 'weekly' else 'месяц'} приложен к письму.",
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )
        logger.info(f"Sent {period} report to {director_email}")
        return {"status": "sent", "to": director_email}
    except Exception as exc:
        logger.error(f"Failed to send {period} report: {exc}")
        return {"status": "failed", "error": str(exc)}
