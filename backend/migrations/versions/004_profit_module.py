"""Add profit distribution module: investors, expenses, profit_periods, profit_distributions

Revision ID: 004
Revises: 003
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE expense_category AS ENUM ('cost_of_goods','operational','salary','rent','other')")
    op.execute("CREATE TYPE profit_period_status AS ENUM ('draft','approved')")

    # investors
    op.create_table(
        "investors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("share_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("investment_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("joined_at", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investors_is_active", "investors", ["is_active"])

    # profit_periods (before expenses — FK target)
    op.create_table(
        "profit_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("draft", "approved", name="profit_period_status", create_type=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("gross_revenue", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_expenses", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("manager_bonus_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("manager_bonus_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("net_distributable", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_profit_periods_status", "profit_periods", ["status"])

    # expenses
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profit_periods.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category",
            postgresql.ENUM("cost_of_goods", "operational", "salary", "rent", "other",
                             name="expense_category", create_type=False),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("expense_date", sa.Date, nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_expenses_period_id", "expenses", ["period_id"])
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"])

    # profit_distributions
    op.create_table(
        "profit_distributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profit_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("share_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_profit_dist_period_id", "profit_distributions", ["period_id"])

    # Audit triggers
    for table in ["investors", "expenses", "profit_periods", "profit_distributions"]:
        op.execute(f"""
            CREATE TRIGGER audit_{table}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();
        """)

    # Seed manager_bonus_pct setting (default 5%)
    import uuid as uuid_mod, json
    op.execute(
        sa.text(
            "INSERT INTO system_settings (id, key, value) "
            "VALUES (CAST(:id AS uuid), :key, CAST(:val AS jsonb)) "
            "ON CONFLICT DO NOTHING"
        ).bindparams(
            id=str(uuid_mod.uuid4()),
            key="manager_bonus_pct",
            val=json.dumps(5),
        )
    )


def downgrade() -> None:
    for table in ["profit_distributions", "profit_periods", "expenses", "investors"]:
        op.execute(f"DROP TRIGGER IF EXISTS audit_{table} ON {table}")

    op.drop_table("profit_distributions")
    op.drop_table("expenses")
    op.drop_table("profit_periods")
    op.drop_table("investors")
    op.execute("DROP TYPE IF EXISTS profit_period_status")
    op.execute("DROP TYPE IF EXISTS expense_category")
