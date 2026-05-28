"""
Integration test: full deal lifecycle.
draft → pending → active → payment → overdue → SB → restructure
Requires real PostgreSQL. Run with TEST_DATABASE_URL env var pointing to test DB.
"""
import pytest


@pytest.mark.skip(reason="Requires real PostgreSQL — run with TEST_DATABASE_URL")
@pytest.mark.asyncio
async def test_full_deal_flow(client):
    """
    Full deal lifecycle integration test.
    Requires a seeded database with director, manager accounts.
    """
    # Step 1: Login as manager
    resp = await client.post(
        "/api/auth/login",
        json={"phone": "+79000000002", "password": "Manager12345!"},
    )
    assert resp.status_code == 200
    manager_data = resp.json()
    assert manager_data["role"] == "manager"

    # Step 2: Create a client
    resp = await client.post(
        "/api/clients",
        json={"full_name": "Тест Тестов", "phone": "+79999999999"},
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # Step 3: Create a Murabaha deal
    resp = await client.post(
        "/api/deals",
        json={
            "client_id": client_id,
            "type": "murabaha",
            "murabaha": {
                "principal": "100000",
                "markup": "15000",
                "duration_months": 12,
                "start_date": "2025-01-01",
            },
        },
    )
    assert resp.status_code == 201
    deal = resp.json()
    deal_id = deal["id"]
    assert deal["status"] == "draft"
    assert len(deal["payment_schedules"]) == 12

    # Step 4: Submit for approval
    resp = await client.post(f"/api/deals/{deal_id}/submit")
    assert resp.status_code == 200

    # Step 5: Login as director and approve
    resp = await client.post(
        "/api/auth/login",
        json={"phone": "+79000000001", "password": "Admin12345!"},
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/director/approval/deals/{deal_id}/approve",
        json={"comment": "Approved"},
    )
    assert resp.status_code == 200

    # Step 6: Verify deal is now active
    resp = await client.get(f"/api/deals/{deal_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Step 7: Login as manager and record a payment
    await client.post(
        "/api/auth/login",
        json={"phone": "+79000000002", "password": "Manager12345!"},
    )
    schedule_id = deal["payment_schedules"][0]["id"]
    resp = await client.post(
        "/api/payments",
        json={
            "schedule_id": schedule_id,
            "amount": "9583.33",
            "paid_at": "2025-02-01T12:00:00Z",
            "method": "transfer",
        },
    )
    assert resp.status_code == 201

    # Step 8: Verify schedule status
    resp = await client.get(f"/api/deals/{deal_id}")
    first_schedule = next(
        s for s in resp.json()["payment_schedules"]
        if s["installment_number"] == 1
    )
    assert first_schedule["status"] == "paid"
