"""Remove pending from deal_status enum

Revision ID: 012
Revises: 011
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE deals SET status = 'draft' WHERE status = 'pending'")
    op.execute("ALTER TABLE deals ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE deal_status RENAME TO deal_status_old")
    op.execute(
        "CREATE TYPE deal_status AS ENUM ('draft', 'active', 'closed', 'overdue')"
    )
    op.execute(
        "ALTER TABLE deals ALTER COLUMN status TYPE deal_status "
        "USING status::text::deal_status"
    )
    op.execute("ALTER TABLE deals ALTER COLUMN status SET DEFAULT 'draft'::deal_status")
    op.execute("DROP TYPE deal_status_old")


def downgrade() -> None:
    op.execute("ALTER TABLE deals ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE deal_status RENAME TO deal_status_old")
    op.execute(
        "CREATE TYPE deal_status AS ENUM ('draft', 'pending', 'active', 'closed', 'overdue')"
    )
    op.execute(
        "ALTER TABLE deals ALTER COLUMN status TYPE deal_status "
        "USING status::text::deal_status"
    )
    op.execute("ALTER TABLE deals ALTER COLUMN status SET DEFAULT 'draft'::deal_status")
    op.execute("DROP TYPE deal_status_old")
