"""Add product_description to deals

Revision ID: 007
Revises: 006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "product_description" not in [c["name"] for c in insp.get_columns("deals")]:
        op.add_column("deals", sa.Column("product_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("deals", "product_description")
