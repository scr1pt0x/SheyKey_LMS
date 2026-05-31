"""Drop kyc_status from clients

Revision ID: 011
Revises: 010
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_clients_kyc_status", table_name="clients")
    op.drop_column("clients", "kyc_status")
    op.execute("DROP TYPE IF EXISTS kyc_status")


def downgrade() -> None:
    kyc_status = sa.Enum("pending", "verified", "rejected", name="kyc_status")
    kyc_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "clients",
        sa.Column(
            "kyc_status",
            kyc_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("ix_clients_kyc_status", "clients", ["kyc_status"])
