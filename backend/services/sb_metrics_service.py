"""SB performance metrics based on recorded payments."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.payment import Payment


async def sb_collected_amount(
    db: AsyncSession,
    sb_user_id: uuid.UUID,
    start_dt: datetime,
    end_dt: datetime,
) -> Decimal:
    """Sum of payments recorded by this SB officer in the period."""
    total = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.recorded_by == sb_user_id)
            .where(Payment.paid_at >= start_dt)
            .where(Payment.paid_at <= end_dt)
        )
    ).scalar_one()
    return Decimal(str(total or 0))
