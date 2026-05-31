"""Tests for SB presence tracking."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from backend.schemas.director import SbPresenceItem
from backend.services.sb_presence_service import is_sb_online, moscow_today


def test_is_sb_online_recent():
    now = datetime.now(timezone.utc)
    assert is_sb_online(now - timedelta(minutes=2), now=now) is True


def test_is_sb_online_stale():
    now = datetime.now(timezone.utc)
    assert is_sb_online(now - timedelta(minutes=10), now=now) is False


def test_is_sb_online_none():
    assert is_sb_online(None) is False


def test_moscow_today_returns_date():
    assert hasattr(moscow_today(), "year")


def test_sb_presence_item_schema():
    now = datetime.now(timezone.utc)
    item = SbPresenceItem(
        sb_user_id=uuid4(),
        sb_name="Иванов",
        day_started_at=now,
        last_seen_at=now,
        is_online=True,
    )
    assert item.is_online is True


@pytest.mark.asyncio
async def test_sb_presence_endpoint_requires_auth(client: AsyncClient):
    resp = await client.post("/api/sb/presence")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_director_sb_presence_requires_auth(client: AsyncClient):
    resp = await client.get("/api/director/sb-presence")
    assert resp.status_code == 401
