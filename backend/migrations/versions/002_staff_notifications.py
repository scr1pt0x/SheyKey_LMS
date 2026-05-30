"""Add staff_notifications and push_subscriptions tables; drop telegram_chat_id from users

Revision ID: 002
Revises: 001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove telegram_chat_id from users
    op.drop_column("users", "telegram_chat_id")

    # staff_notifications
    op.create_table(
        "staff_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_staff_notif_user_id", "staff_notifications", ["user_id"])
    op.create_index("ix_staff_notif_is_read", "staff_notifications", ["is_read"])
    op.create_index("ix_staff_notif_created_at", "staff_notifications", ["created_at"])

    # Trigger so audit_log captures staff_notifications inserts
    op.execute("""
        CREATE TRIGGER audit_staff_notifications
        AFTER INSERT OR UPDATE OR DELETE ON staff_notifications
        FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();
    """)

    # push_subscriptions
    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_push_sub_user_id", "push_subscriptions", ["user_id"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_staff_notifications ON staff_notifications")
    op.drop_table("push_subscriptions")
    op.drop_table("staff_notifications")
    op.add_column(
        "users",
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=True),
    )
