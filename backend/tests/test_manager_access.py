"""Unit tests for manager portfolio access helpers."""
import uuid
from unittest.mock import MagicMock

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


def test_require_client_access_manager_own():
    manager = _user(UserRole.manager)
    client = MagicMock()
    client.manager_id = manager.id
    require_client_access(client, manager)


def test_require_client_access_manager_other_forbidden():
    manager = _user(UserRole.manager)
    client = MagicMock()
    client.manager_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        require_client_access(client, manager)
    assert exc.value.status_code == 403
    assert exc.value.detail == MANAGER_FORBIDDEN_DETAIL


def test_require_client_access_director_any():
    director = _user(UserRole.director)
    client = MagicMock()
    client.manager_id = uuid.uuid4()
    require_client_access(client, director)


def test_require_deal_access_sb_any():
    sb = _user(UserRole.sb)
    deal = MagicMock()
    deal.manager_id = uuid.uuid4()
    require_deal_access(deal, sb)


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
