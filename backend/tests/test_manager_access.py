"""Unit tests for manager portfolio access helpers."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.core.access import (
    CLIENT_NOT_IN_PORTFOLIO,
    MANAGER_FORBIDDEN_DETAIL,
    list_manager_filter,
    require_client_access,
    require_deal_access,
)
from backend.models.user import UserRole


def _user(role: UserRole, user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.role = role
    return user


def test_list_manager_filter_manager_ignores_param():
    manager = _user(UserRole.manager)
    other_id = uuid.uuid4()
    assert list_manager_filter(manager, other_id) == manager.id


def test_list_manager_filter_director_optional():
    director = _user(UserRole.director)
    filter_id = uuid.uuid4()
    assert list_manager_filter(director, filter_id) == filter_id
    assert list_manager_filter(director, None) is None


def test_list_manager_filter_sb_no_filter():
    sb = _user(UserRole.sb)
    assert list_manager_filter(sb, uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_require_client_access_manager_own():
    from unittest.mock import AsyncMock

    manager = _user(UserRole.manager)
    client = MagicMock()
    client.manager_id = manager.id
    db = AsyncMock()
    await require_client_access(db, client, manager)


@pytest.mark.asyncio
async def test_require_client_access_manager_any_client():
    from unittest.mock import AsyncMock

    manager = _user(UserRole.manager)
    client = MagicMock()
    client.manager_id = uuid.uuid4()
    db = AsyncMock()
    await require_client_access(db, client, manager)


@pytest.mark.asyncio
async def test_require_client_access_director_any():
    from unittest.mock import AsyncMock

    director = _user(UserRole.director)
    client = MagicMock()
    client.manager_id = uuid.uuid4()
    db = AsyncMock()
    await require_client_access(db, client, director)


@pytest.mark.asyncio
async def test_require_deal_access_sb_any():
    sb = _user(UserRole.sb)
    deal = MagicMock()
    deal.manager_id = uuid.uuid4()
    db = AsyncMock()
    await require_deal_access(db, deal, sb)


@pytest.mark.asyncio
async def test_require_deal_access_manager_own_deal():
    manager = _user(UserRole.manager)
    deal = MagicMock()
    deal.manager_id = manager.id
    deal.client_id = uuid.uuid4()
    db = AsyncMock()
    await require_deal_access(db, deal, manager)


@pytest.mark.asyncio
async def test_require_deal_access_manager_via_client():
    manager = _user(UserRole.manager)
    deal = MagicMock()
    deal.manager_id = uuid.uuid4()
    deal.client_id = uuid.uuid4()
    db = AsyncMock()
    with patch(
        "backend.core.access.load_client_for_user", new=AsyncMock()
    ) as load_client:
        await require_deal_access(db, deal, manager)
        load_client.assert_awaited_once_with(db, deal.client_id, manager)


@pytest.mark.asyncio
async def test_require_deal_access_manager_forbidden():
    manager = _user(UserRole.manager)
    deal = MagicMock()
    deal.manager_id = uuid.uuid4()
    deal.client_id = uuid.uuid4()
    db = AsyncMock()
    with patch(
        "backend.core.access.load_client_for_user",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail=MANAGER_FORBIDDEN_DETAIL)),
    ):
        with pytest.raises(HTTPException) as exc:
            await require_deal_access(db, deal, manager)
        assert exc.value.status_code == 403


def test_list_deals_manager_filter_skipped_with_client_id():
    manager = _user(UserRole.manager)
    client_id = uuid.uuid4()
    effective_manager_id = list_manager_filter(manager, None)
    apply_manager_filter = effective_manager_id and not (
        manager.role == UserRole.manager and client_id
    )
    assert effective_manager_id == manager.id
    assert apply_manager_filter is False


def test_constants():
    assert CLIENT_NOT_IN_PORTFOLIO == "Клиент не в вашем портфеле"


@pytest.mark.asyncio
async def test_require_sb_case_on_deal_blocks_unassigned():
    from unittest.mock import AsyncMock, MagicMock

    from backend.core.access import require_sb_case_on_deal

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    with pytest.raises(HTTPException) as exc:
        await require_sb_case_on_deal(db, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 403
