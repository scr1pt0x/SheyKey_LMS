"""
Step 3: Bulk insert clean data into PostgreSQL.
Run: DATABASE_URL=... python load.py
"""
import asyncio
import json
import os
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CLEAN_FILE = Path(__file__).parent / "clean_data" / "clean.json"
DATABASE_URL = os.environ["DATABASE_URL"]
DEFAULT_MANAGER_ID = os.environ.get("DEFAULT_MANAGER_ID", "")


async def load() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    data = json.loads(CLEAN_FILE.read_text())
    clients = data.get("clients", [])
    deals = data.get("deals", [])

    async with SessionLocal() as db:
        from sqlalchemy import text

        # Verify default manager exists
        if DEFAULT_MANAGER_ID:
            result = await db.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": DEFAULT_MANAGER_ID},
            )
            if not result.scalar_one_or_none():
                print(f"WARNING: Manager {DEFAULT_MANAGER_ID} not found. Using NULL.")
                manager_id = None
            else:
                manager_id = DEFAULT_MANAGER_ID
        else:
            # Use first manager found
            result = await db.execute(
                text("SELECT id FROM users WHERE role = 'manager' LIMIT 1")
            )
            row = result.scalar_one_or_none()
            manager_id = str(row) if row else None
            print(f"Using manager_id={manager_id}")

        # Insert clients in batches
        BATCH_SIZE = 100
        inserted_clients = 0
        for i in range(0, len(clients), BATCH_SIZE):
            batch = clients[i:i + BATCH_SIZE]
            for client in batch:
                await db.execute(
                    text(
                        """
                        INSERT INTO clients
                          (id, manager_id, full_name, phone, passport, address, kyc_status, is_archived)
                        VALUES
                          (:id, :manager_id, :full_name, :phone, :passport, :address, 'pending', false)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "id": client.get("id", str(uuid.uuid4())),
                        "manager_id": manager_id,
                        "full_name": client["full_name"],
                        "phone": client["phone"],
                        "passport": client.get("passport"),
                        "address": client.get("address"),
                    },
                )
            await db.commit()
            inserted_clients += len(batch)
            print(f"Clients: {inserted_clients}/{len(clients)} inserted")

        print(f"Load complete: {inserted_clients} clients, {len(deals)} deals pending manual review")
        await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load())
