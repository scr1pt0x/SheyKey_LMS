"""Remove musharaka from deal_type enum and related settings

Revision ID: 003
Revises: 002
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safety: ensure no musharaka deals exist before removing the enum value
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM deals WHERE type = 'musharaka'")).scalar()
    if result and result > 0:
        raise RuntimeError(
            f"Cannot remove musharaka: {result} existing deal(s) use this type. "
            "Convert or delete them first."
        )

    # PostgreSQL does not support dropping enum values directly.
    # Workaround: rename old type, create new one, alter column, drop old type.
    op.execute("ALTER TYPE deal_type RENAME TO deal_type_old")
    op.execute("CREATE TYPE deal_type AS ENUM ('murabaha', 'ijara')")
    op.execute(
        "ALTER TABLE deals ALTER COLUMN type TYPE deal_type "
        "USING type::text::deal_type"
    )
    op.execute("DROP TYPE deal_type_old")

    # Remove musharaka default setting
    op.execute(
        sa.text("DELETE FROM system_settings WHERE key = 'musharaka_default_bank_share'")
    )


def downgrade() -> None:
    op.execute("ALTER TYPE deal_type RENAME TO deal_type_old")
    op.execute("CREATE TYPE deal_type AS ENUM ('murabaha', 'ijara', 'musharaka')")
    op.execute(
        "ALTER TABLE deals ALTER COLUMN type TYPE deal_type "
        "USING type::text::deal_type"
    )
    op.execute("DROP TYPE deal_type_old")
