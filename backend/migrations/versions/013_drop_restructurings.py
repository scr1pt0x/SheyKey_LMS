"""Drop restructurings table

Revision ID: 013
Revises: 012
"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_restructurings_status", table_name="restructurings")
    op.drop_index("ix_restructurings_deal_id", table_name="restructurings")
    op.drop_table("restructurings")
    op.execute("DROP TYPE IF EXISTS restructuring_status")


def downgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    restructuring_status = postgresql.ENUM(
        "pending", "approved", "rejected", name="restructuring_status", create_type=False
    )
    restructuring_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "restructurings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=True),
        sa.Column("initiated_by", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("new_schedule", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            restructuring_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["overdue_cases.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_restructurings_deal_id", "restructurings", ["deal_id"])
    op.create_index("ix_restructurings_status", "restructurings", ["status"])
