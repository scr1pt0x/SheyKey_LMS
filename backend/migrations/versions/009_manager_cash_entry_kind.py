"""Add entry_kind (income/expense) to manager_cash_entries

Revision ID: 009
Revises: 008
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE manager_cash_entry_kind AS ENUM ('income', 'expense')")
    op.add_column(
        "manager_cash_entries",
        sa.Column(
            "entry_kind",
            postgresql.ENUM(
                "income", "expense", name="manager_cash_entry_kind", create_type=False
            ),
            nullable=False,
            server_default="income",
        ),
    )


def downgrade() -> None:
    op.drop_column("manager_cash_entries", "entry_kind")
    op.execute("DROP TYPE manager_cash_entry_kind")
