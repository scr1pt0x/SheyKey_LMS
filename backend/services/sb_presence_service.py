import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.redis_client import get_redis
from backend.models.sb_work_session import SbWorkSession

MSK = ZoneInfo("Europe/Moscow")
PRESENCE_THROTTLE_SECONDS = 60
ONLINE_THRESHOLD_SECONDS = 300


def moscow_today() -> date:
    return datetime.now(MSK).date()


async def _is_throttled(user_id: uuid.UUID) -> bool:
    try:
        redis = await get_redis()
        key = f"sb:presence:{user_id}"
        if await redis.get(key):
            return True
        await redis.setex(key, PRESENCE_THROTTLE_SECONDS, "1")
    except Exception:
        pass
    return False


async def record_sb_presence(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Record SB cabinet activity: first hit of the day sets started_at, always updates last_seen_at."""
    if await _is_throttled(user_id):
        return

    now = datetime.now(timezone.utc)
    work_date = moscow_today()

    result = await db.execute(
        select(SbWorkSession).where(
            SbWorkSession.user_id == user_id,
            SbWorkSession.work_date == work_date,
        )
    )
    session = result.scalar_one_or_none()
    if session:
        session.last_seen_at = now
    else:
        db.add(
            SbWorkSession(
                user_id=user_id,
                work_date=work_date,
                started_at=now,
                last_seen_at=now,
            )
        )
    await db.commit()


def is_sb_online(last_seen_at: datetime | None, now: datetime | None = None) -> bool:
    if last_seen_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    return (now - last_seen_at).total_seconds() < ONLINE_THRESHOLD_SECONDS
