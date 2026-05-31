"""Manager manual cash register entries

Revision ID: 008
Revises: 007
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_cash_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "method",
            postgresql.ENUM(
                "cash", "transfer", "card", "other", name="payment_method", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manager_cash_entries_manager_id", "manager_cash_entries", ["manager_id"])
    op.create_index("ix_manager_cash_entries_paid_at", "manager_cash_entries", ["paid_at"])


def downgrade() -> None:
    op.drop_index("ix_manager_cash_entries_paid_at", table_name="manager_cash_entries")
    op.drop_index("ix_manager_cash_entries_manager_id", table_name="manager_cash_entries")
    op.drop_table("manager_cash_entries")
