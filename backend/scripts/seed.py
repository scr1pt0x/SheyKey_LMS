"""
Seed script: creates an initial director account and default system settings.
Run: python -m backend.scripts.seed
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.database import AsyncSessionLocal
from backend.core.security import hash_password
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User, UserRole


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        existing_director = (
            await db.execute(select(User).where(User.role == UserRole.director))
        ).scalar_one_or_none()

        if not existing_director:
            director = User(
                name="Руководитель",
                phone="+79000000001",
                role=UserRole.director,
                password_hash=hash_password("Admin12345!"),
                is_active=True,
            )
            db.add(director)
            print("✓ Director account created: phone=+79000000001, password=Admin12345!")
        else:
            print("✓ Director already exists")

        for key, default_value in SettingKey.DEFAULTS.items():
            existing = (
                await db.execute(select(SystemSetting).where(SystemSetting.key == key))
            ).scalar_one_or_none()
            if not existing:
                db.add(SystemSetting(key=key, value=default_value))
                print(f"✓ Setting created: {key}")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
