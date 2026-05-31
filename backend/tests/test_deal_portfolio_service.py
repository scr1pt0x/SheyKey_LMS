"""Tests for responsible manager assignment."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.models.user import UserRole
from backend.services.deal_portfolio_service import (
    assign_deal_portfolio,
    resolve_responsible_manager_id,
    user_is_manager,
)


def _user(role: UserRole, user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_resolve_responsible_manager_id_manager():
    db = AsyncMock()
    manager = _user(UserRole.manager)
    result = await resolve_responsible_manager_id(db, manager, uuid.uuid4())
    assert result == manager.id


@pytest.mark.asyncio
async def test_resolve_responsible_manager_id_director_with_choice():
    db = AsyncMock()
    manager_id = uuid.uuid4()
    manager = MagicMock()
    manager.id = manager_id
    manager.role = UserRole.manager
    manager.is_active = True
    db.get = AsyncMock(return_value=manager)

    director = _user(UserRole.director)
    result = await resolve_responsible_manager_id(db, director, manager_id)
    assert result == manager_id


@pytest.mark.asyncio
async def test_resolve_responsible_manager_id_director_invalid():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    director = _user(UserRole.director)
    with pytest.raises(HTTPException) as exc:
        await resolve_responsible_manager_id(db, director, uuid.uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_resolve_responsible_manager_id_director_default():
    db = AsyncMock()
    director = _user(UserRole.director)
    result = await resolve_responsible_manager_id(db, director, None)
    assert result == director.id


@pytest.mark.asyncio
async def test_assign_deal_portfolio():
    deal = MagicMock()
    client = MagicMock()
    responsible = uuid.uuid4()
    await assign_deal_portfolio(AsyncMock(), deal, client, responsible)
    assert deal.manager_id == responsible
    assert client.manager_id == responsible


@pytest.mark.asyncio
async def test_user_is_manager():
    db = AsyncMock()
    manager = _user(UserRole.manager)
    db.get = AsyncMock(return_value=manager)
    assert await user_is_manager(db, manager.id) is True

    director = _user(UserRole.director)
    db.get = AsyncMock(return_value=director)
    assert await user_is_manager(db, director.id) is False
