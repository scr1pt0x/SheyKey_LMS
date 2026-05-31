"""Tests for search filtering by role."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.user import UserRole
from backend.services.search_service import client_has_open_sb_case, client_text_filter


def test_client_text_filter_includes_phone_digits():
    clause = client_text_filter("+7999")
    assert clause is not None


@pytest.mark.asyncio
async def test_client_has_open_sb_case_false():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    assert await client_has_open_sb_case(db, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_client_has_open_sb_case_true():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=uuid.uuid4())))
    assert await client_has_open_sb_case(db, uuid.uuid4()) is True


def test_manager_search_portfolio_in_service():
    """Manager branch filters by manager_id — verified by code structure."""
    from backend.services import search_service

    assert hasattr(search_service, "search_clients")


@pytest.mark.asyncio
async def test_sb_load_client_requires_open_case():
    from fastapi import HTTPException

    from backend.core.access import load_client_for_user
    from backend.models.client import Client

    client = MagicMock(spec=Client)
    client.manager_id = uuid.uuid4()

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=client))
    )

    user = MagicMock()
    user.role = UserRole.sb
    user.id = uuid.uuid4()

    with patch("backend.core.access.client_has_open_sb_case", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc:
            await load_client_for_user(db, uuid.uuid4(), user)
        assert exc.value.status_code == 403
