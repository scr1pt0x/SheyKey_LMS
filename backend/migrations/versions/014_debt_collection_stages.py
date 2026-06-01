"""Debt collection stages on overdue_cases and payment commission splits

Revision ID: 014
Revises: 013
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "overdue_cases",
        sa.Column("collection_stage", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.add_column(
        "overdue_cases",
        sa.Column("overdue_installments_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "overdue_cases",
        sa.Column("stage_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_overdue_cases_collection_stage", "overdue_cases", ["collection_stage"])

    op.create_table(
        "payment_commission_splits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("collection_stage_at_payment", sa.SmallInteger(), nullable=False),
        sa.Column(
            "manager_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("manager_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("manager_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column(
            "sb_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sb_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("sb_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    import json
    import uuid as uuid_mod

    conn = op.get_bind()
    defaults = [
        ("debt_stage_2_days", 30),
        ("debt_stage_2_installments", 2),
        ("debt_stage_3_days", 60),
        ("debt_stage_3_installments", 3),
        ("debt_stage_4_days", 90),
        ("manager_payment_commission_pct", 0),
        ("manager_payment_commission_from_stage_3_pct", 0),
        ("sb_commission_stage_2_pct", 0),
        ("sb_commission_stage_3_pct", 0),
        ("sb_commission_stage_4_pct", 0),
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
    op.drop_table("payment_commission_splits")
    op.drop_index("ix_overdue_cases_collection_stage", table_name="overdue_cases")
    op.drop_column("overdue_cases", "stage_changed_at")
    op.drop_column("overdue_cases", "overdue_installments_count")
    op.drop_column("overdue_cases", "collection_stage")

    for key in (
        "debt_stage_2_days",
        "debt_stage_2_installments",
        "debt_stage_3_days",
        "debt_stage_3_installments",
        "debt_stage_4_days",
        "debt_stage_2_sb_user_id",
        "debt_stage_3_sb_user_id",
        "debt_stage_4_sb_user_id",
        "manager_payment_commission_pct",
        "manager_payment_commission_from_stage_3_pct",
        "sb_commission_stage_2_pct",
        "sb_commission_stage_3_pct",
        "sb_commission_stage_4_pct",
    ):
        op.execute(sa.text("DELETE FROM system_settings WHERE key = :k").bindparams(k=key))
