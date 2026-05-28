"""
Rollback: truncate all migrated data (use with caution in dev only).
Run: DATABASE_URL=... python rollback.py --confirm
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


async def rollback() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        # Truncate in dependency order
        tables = [
            "payment_promises",
            "contact_logs",
            "overdue_cases",
            "payments",
            "payment_schedules",
            "deal_params",
            "deals",
            "clients",
        ]
        for table in tables:
            await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"Truncated: {table}")

        await db.commit()
        print("Rollback complete.")

    await engine.dispose()


if __name__ == "__main__":
    if "--confirm" not in sys.argv:
        print("WARNING: This will DELETE all migrated data!")
        print("Run with --confirm to proceed.")
        sys.exit(1)

    confirm = input("Type 'ROLLBACK' to confirm: ")
    if confirm != "ROLLBACK":
        print("Aborted.")
        sys.exit(1)

    asyncio.run(rollback())
