"""Contract number counters setting and murabaha seller FIO

Revision ID: 016
Revises: 015
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import json
    import uuid as uuid_mod

    conn = op.get_bind()
    defaults = [
        ("contract_number_counters", {}),
        ("murabaha_seller_fio", "SheyKey Finance"),
    ]
    for key, val in defaults:
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
    conn = op.get_bind()
    for key in ("contract_number_counters", "murabaha_seller_fio"):
        conn.execute(sa.text("DELETE FROM system_settings WHERE key = :key").bindparams(key=key))
