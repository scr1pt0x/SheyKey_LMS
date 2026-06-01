"""Atomic Murabaha contract numbers (format N-YY/MM/DD)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.settings import SettingKey, SystemSetting

COUNTERS_KEY = "contract_number_counters"


async def allocate_contract_number(db: AsyncSession, contract_date: date | None = None) -> str:
    contract_date = contract_date or datetime.now().date()
    date_key = contract_date.strftime("%Y-%m-%d")

    row = (
        await db.execute(select(SystemSetting).where(SystemSetting.key == COUNTERS_KEY))
    ).scalar_one_or_none()

    if row and isinstance(row.value, dict):
        counters = dict(row.value)
    else:
        counters = {}

    current_count = int(counters.get(date_key, 0)) + 1
    counters[date_key] = current_count

    if row:
        row.value = counters
    else:
        db.add(SystemSetting(key=COUNTERS_KEY, value=counters))

    await db.flush()
    return f"{current_count}-{contract_date.strftime('%y/%m/%d')}"
