"""Integration tests for auth endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_credentials(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login", json={"phone": "+70000000001", "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_without_cookie(client: AsyncClient):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
