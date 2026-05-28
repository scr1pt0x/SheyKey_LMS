"""
Step 4: Verify migrated data with SQL assertions.
Run: DATABASE_URL=... python verify.py
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


async def verify() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    checks = []

    async with SessionLocal() as db:
        # Check: no clients without manager
        result = await db.execute(
            text("SELECT COUNT(*) FROM clients WHERE manager_id IS NULL")
        )
        orphan_clients = result.scalar_one()
        checks.append(("Clients without manager", orphan_clients == 0, orphan_clients))

        # Check: no deals without client
        result = await db.execute(
            text("SELECT COUNT(*) FROM deals d LEFT JOIN clients c ON d.client_id = c.id WHERE c.id IS NULL")
        )
        orphan_deals = result.scalar_one()
        checks.append(("Deals without client", orphan_deals == 0, orphan_deals))

        # Check: payment schedule amounts positive
        result = await db.execute(
            text("SELECT COUNT(*) FROM payment_schedules WHERE amount <= 0")
        )
        bad_amounts = result.scalar_one()
        checks.append(("Payment schedules with zero/negative amount", bad_amounts == 0, bad_amounts))

        # Check: audit log has entries for new clients
        result = await db.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE action = 'INSERT' AND entity = 'clients'")
        )
        audit_entries = result.scalar_one()
        checks.append(("Audit log entries for clients", audit_entries > 0, audit_entries))

        # Check: total clients
        result = await db.execute(text("SELECT COUNT(*) FROM clients"))
        total_clients = result.scalar_one()
        checks.append(("Total clients imported", total_clients > 0, total_clients))

    await engine.dispose()

    print("\n=== Migration Verification ===")
    all_passed = True
    for name, passed, detail in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} — {name}: {detail}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ All checks passed. Migration successful.")
    else:
        print("\n❌ Some checks failed. Review migration data.")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(verify())
