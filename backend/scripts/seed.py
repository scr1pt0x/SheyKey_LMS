"""
Seed script: creates an initial director account, default system settings,
and SB staff for debt collection stages.
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

SB_STAFF = [
    ("Шамиль", "+79000000003", SettingKey.DEBT_STAGE_2_SB_USER_ID),
    ("Усман", "+79000000004", SettingKey.DEBT_STAGE_3_SB_USER_ID),
    ("Докка", "+79000000005", SettingKey.DEBT_STAGE_4_SB_USER_ID),
]
SB_DEFAULT_PASSWORD = "Sb12345!"


async def _ensure_user(db, name: str, phone: str) -> User:
    from sqlalchemy import select

    existing = (
        await db.execute(select(User).where((User.phone == phone) | (User.name == name)))
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        name=name,
        phone=phone,
        role=UserRole.sb,
        password_hash=hash_password(SB_DEFAULT_PASSWORD),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    print(f"✓ SB created: {name} phone={phone} password={SB_DEFAULT_PASSWORD}")
    return user


async def _ensure_setting(db, key: str, value) -> None:
    from sqlalchemy import select

    row = (await db.execute(select(SystemSetting).where(SystemSetting.key == key))).scalar_one_or_none()
    if row:
        row.value = value
        return
    db.add(SystemSetting(key=key, value=value))


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
            await _ensure_setting(db, key, default_value)

        for name, phone, setting_key in SB_STAFF:
            user = await _ensure_user(db, name, phone)
            await _ensure_setting(db, setting_key, str(user.id))

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
