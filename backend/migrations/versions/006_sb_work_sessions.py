"""Add sb_work_sessions for SB presence tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sb_work_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "work_date", name="uq_sb_work_sessions_user_date"),
    )
    op.create_index("ix_sb_work_sessions_user_id", "sb_work_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sb_work_sessions_user_id", table_name="sb_work_sessions")
    op.drop_table("sb_work_sessions")
