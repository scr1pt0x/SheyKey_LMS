"""
Test configuration and fixtures.
Uses an in-memory SQLite database for unit tests.
Integration tests require a real PostgreSQL instance.
"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use in-memory SQLite for unit tests
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

os.environ.setdefault("JWT_PRIVATE_KEY", "test-key")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from backend.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
