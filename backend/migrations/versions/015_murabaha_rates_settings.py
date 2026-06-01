"""Murabaha rate settings; remove obsolete sb_threshold and default markup pct

Revision ID: 015
Revises: 014
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REMOVE_KEYS = ("sb_threshold_days", "murabaha_default_markup_pct")
NEW_DEFAULTS = (
    ("murabaha_rate_with_down_pct", 4),
    ("murabaha_rate_without_down_pct", 5),
    ("murabaha_rate_auto_pct", 3.3),
)


def upgrade() -> None:
    import json
    import uuid as uuid_mod

    conn = op.get_bind()
    for key in REMOVE_KEYS:
        conn.execute(sa.text("DELETE FROM system_settings WHERE key = :key").bindparams(key=key))

    for key, val in NEW_DEFAULTS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM system_settings WHERE key = :key").bindparams(key=key)
        ).scalar()
        if not exists:
            op.execute(
                sa.text(
                    "INSERT INTO system_settings (id, key, value) "
                    "VALUES (CAST(:id AS uuid), :key, CAST(:val AS jsonb))"
                ).bindparams(
                    id=str(uuid_mod.uuid4()),
                    key=key,
                    val=json.dumps(val),
                )
            )


def downgrade() -> None:
    import json
    import uuid as uuid_mod

    conn = op.get_bind()
    for key, _ in NEW_DEFAULTS:
        conn.execute(sa.text("DELETE FROM system_settings WHERE key = :key").bindparams(key=key))

    conn = op.get_bind()
    restore = (
        ("sb_threshold_days", 7),
        ("murabaha_default_markup_pct", 15),
    )
    for key, val in restore:
        exists = conn.execute(
            sa.text("SELECT 1 FROM system_settings WHERE key = :key").bindparams(key=key)
        ).scalar()
        if not exists:
            op.execute(
                sa.text(
                    "INSERT INTO system_settings (id, key, value) "
                    "VALUES (CAST(:id AS uuid), :key, CAST(:val AS jsonb))"
                ).bindparams(
                    id=str(uuid_mod.uuid4()),
                    key=key,
                    val=json.dumps(val),
                )
            )
