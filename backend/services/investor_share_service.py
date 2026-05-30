"""Automatic investor share calculation from investment amounts."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.investor import Investor


async def recalculate_active_investor_shares(db: AsyncSession) -> list[Investor]:
    """
    Set share_pct for each active investor proportionally:
    share = investment / sum(investments) * 100.
    Last investor gets remainder so shares sum to exactly 100%.
    """
    result = await db.execute(
        select(Investor)
        .where(Investor.is_active == True)  # noqa: E712
        .order_by(Investor.created_at)
    )
    investors = list(result.scalars().all())

    eligible = [
        inv
        for inv in investors
        if inv.investment_amount is not None and float(inv.investment_amount) > 0
    ]

    if not eligible:
        for inv in investors:
            inv.share_pct = 0
        await db.flush()
        return investors

    total_invested = sum(float(inv.investment_amount) for inv in eligible)

    running = 0.0
    for i, inv in enumerate(eligible):
        if i == len(eligible) - 1:
            inv.share_pct = round(100.0 - running, 2)
        else:
            pct = round(float(inv.investment_amount) / total_invested * 100, 2)
            inv.share_pct = pct
            running += pct

    inactive_or_zero = [inv for inv in investors if inv not in eligible]
    for inv in inactive_or_zero:
        inv.share_pct = 0

    await db.flush()
    return investors
