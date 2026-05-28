from celery import Celery
from celery.schedules import crontab

from backend.core.config import settings

celery_app = Celery(
    "lms",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.check_overdue",
        "backend.tasks.auto_transfer_sb",
        "backend.tasks.check_promises",
        "backend.tasks.notifications",
        "backend.tasks.reports",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "check-overdue-payments": {
        "task": "backend.tasks.check_overdue.check_overdue_payments",
        "schedule": crontab(hour=0, minute=1),
    },
    "auto-transfer-to-sb": {
        "task": "backend.tasks.auto_transfer_sb.auto_transfer_to_sb",
        "schedule": crontab(hour=0, minute=5),
    },
    "check-payment-promises": {
        "task": "backend.tasks.check_promises.check_payment_promises",
        "schedule": crontab(hour=9, minute=0),
    },
    "send-payment-reminders-3d": {
        "task": "backend.tasks.notifications.send_payment_reminders",
        "schedule": crontab(hour=10, minute=0),
        "kwargs": {"days_before": 3},
    },
    "send-payment-reminders-1d": {
        "task": "backend.tasks.notifications.send_payment_reminders",
        "schedule": crontab(hour=10, minute=30),
        "kwargs": {"days_before": 1},
    },
    "weekly-report": {
        "task": "backend.tasks.reports.send_weekly_report",
        "schedule": crontab(day_of_week=1, hour=8, minute=0),
    },
    "monthly-report": {
        "task": "backend.tasks.reports.send_monthly_report",
        "schedule": crontab(day_of_month=1, hour=8, minute=0),
    },
}
