"""Backfill deal.manager_id from client when director owns deal but manager owns client

Revision ID: 010
Revises: 009
"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE deals d
        SET manager_id = c.manager_id
        FROM clients c, users deal_mgr, users client_mgr
        WHERE d.client_id = c.id
          AND d.manager_id = deal_mgr.id
          AND c.manager_id = client_mgr.id
          AND deal_mgr.role = 'director'
          AND client_mgr.role = 'manager'
          AND d.manager_id != c.manager_id
        """
    )


def downgrade() -> None:
    pass
