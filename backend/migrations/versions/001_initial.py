"""Initial schema: all 14 tables, ENUMs, indexes, audit trigger, REVOKE on audit_log

Revision ID: 001
Revises:
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION audit_trigger_fn()
RETURNS trigger AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_action   VARCHAR(10);
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_new_data := to_jsonb(NEW);
        v_old_data := NULL;
        v_action   := 'INSERT';
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        v_action   := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        v_action   := 'DELETE';
    END IF;

    INSERT INTO audit_log (action, entity, entity_id, old_val, new_val, created_at)
    VALUES (
        v_action,
        TG_TABLE_NAME,
        COALESCE(
            CASE WHEN TG_OP = 'DELETE' THEN (v_old_data->>'id')::uuid
                 ELSE (v_new_data->>'id')::uuid
            END,
            NULL
        ),
        v_old_data,
        v_new_data,
        NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

AUDITED_TABLES = [
    "users", "clients", "deals", "deal_params",
    "payment_schedules", "payments", "overdue_cases",
    "contact_logs", "payment_promises", "restructurings",
    "documents", "notifications_log", "system_settings", "calendar_tasks",
]


def upgrade() -> None:
    # ─── ENUMs ────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('manager', 'sb', 'director')")
    op.execute("CREATE TYPE kyc_status AS ENUM ('pending', 'verified', 'rejected')")
    op.execute("CREATE TYPE deal_type AS ENUM ('murabaha', 'ijara', 'musharaka')")
    op.execute("CREATE TYPE deal_status AS ENUM ('draft', 'pending', 'active', 'closed', 'overdue')")
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'overdue', 'partial')")
    op.execute("CREATE TYPE payment_method AS ENUM ('cash', 'transfer', 'card', 'other')")
    op.execute("CREATE TYPE installment_type AS ENUM ('rent', 'buyout', 'principal')")
    op.execute("CREATE TYPE overdue_case_status AS ENUM ('new', 'in_progress', 'agreed', 'closed')")
    op.execute("CREATE TYPE contact_type AS ENUM ('call', 'meeting', 'sms', 'telegram', 'other')")
    op.execute("CREATE TYPE restructuring_status AS ENUM ('pending', 'approved', 'rejected')")
    op.execute("CREATE TYPE document_entity_type AS ENUM ('client', 'deal', 'payment', 'overdue_case', 'contact_log')")
    op.execute("CREATE TYPE document_type AS ENUM ('contract', 'collateral', 'photo', 'receipt', 'act', 'notification', 'other')")
    op.execute("CREATE TYPE notification_channel AS ENUM ('sms', 'telegram')")
    op.execute("CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed')")
    op.execute("CREATE TYPE calendar_task_status AS ENUM ('pending', 'done', 'cancelled')")

    # ─── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", postgresql.ENUM("manager", "sb", "director", name="user_role", create_type=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # ─── audit_log (created before triggers) ──────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_val", postgresql.JSONB, nullable=True),
        sa.Column("new_val", postgresql.JSONB, nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ─── clients ──────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("passport", sa.String(50), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("kyc_status", postgresql.ENUM("pending", "verified", "rejected", name="kyc_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clients_manager_id", "clients", ["manager_id"])
    op.create_index("ix_clients_full_name", "clients", ["full_name"])
    op.create_index("ix_clients_phone", "clients", ["phone"])
    op.create_index("ix_clients_passport", "clients", ["passport"])
    op.create_index("ix_clients_kyc_status", "clients", ["kyc_status"])
    op.create_index("ix_clients_is_archived", "clients", ["is_archived"])

    # ─── deals ────────────────────────────────────────────────────────────────
    op.create_table(
        "deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", postgresql.ENUM("murabaha", "ijara", "musharaka", name="deal_type", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("draft", "pending", "active", "closed", "overdue", name="deal_status", create_type=False), nullable=False, server_default="draft"),
        sa.Column("principal", sa.Numeric(15, 2), nullable=False),
        sa.Column("markup", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(15, 2), nullable=False),
        sa.Column("duration_months", sa.Integer, nullable=False),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deals_client_id", "deals", ["client_id"])
    op.create_index("ix_deals_manager_id", "deals", ["manager_id"])
    op.create_index("ix_deals_type", "deals", ["type"])
    op.create_index("ix_deals_status", "deals", ["status"])

    # ─── deal_params ──────────────────────────────────────────────────────────
    op.create_table(
        "deal_params",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_deal_params_deal_id", "deal_params", ["deal_id"])

    # ─── payment_schedules ────────────────────────────────────────────────────
    op.create_table(
        "payment_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installment_number", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", postgresql.ENUM("pending", "paid", "overdue", "partial", name="payment_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("installment_type", postgresql.ENUM("rent", "buyout", "principal", name="installment_type", create_type=False), nullable=False, server_default="principal"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payment_schedules_deal_id", "payment_schedules", ["deal_id"])
    op.create_index("ix_payment_schedules_due_date", "payment_schedules", ["due_date"])
    op.create_index("ix_payment_schedules_status", "payment_schedules", ["status"])

    # ─── payments ─────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payment_schedules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", postgresql.ENUM("cash", "transfer", "card", "other", name="payment_method", create_type=False), nullable=False),
        sa.Column("receipt_url", sa.Text, nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_schedule_id", "payments", ["schedule_id"])
    op.create_index("ix_payments_deal_id", "payments", ["deal_id"])

    # ─── overdue_cases ────────────────────────────────────────────────────────
    op.create_table(
        "overdue_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sb_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", postgresql.ENUM("new", "in_progress", "agreed", "closed", name="overdue_case_status", create_type=False), nullable=False, server_default="new"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_debt", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("days_overdue", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_overdue_cases_deal_id", "overdue_cases", ["deal_id"])
    op.create_index("ix_overdue_cases_sb_user_id", "overdue_cases", ["sb_user_id"])
    op.create_index("ix_overdue_cases_status", "overdue_cases", ["status"])

    # ─── contact_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "contact_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("overdue_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sb_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", postgresql.ENUM("call", "meeting", "sms", "telegram", "other", name="contact_type", create_type=False), nullable=False),
        sa.Column("result", sa.Text, nullable=False),
        sa.Column("next_action", sa.Text, nullable=True),
        sa.Column("next_action_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contact_logs_case_id", "contact_logs", ["case_id"])

    # ─── payment_promises ─────────────────────────────────────────────────────
    op.create_table(
        "payment_promises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("overdue_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("promised_date", sa.Date, nullable=False),
        sa.Column("promised_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("is_fulfilled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payment_promises_case_id", "payment_promises", ["case_id"])
    op.create_index("ix_payment_promises_promised_date", "payment_promises", ["promised_date"])

    # ─── restructurings ───────────────────────────────────────────────────────
    op.create_table(
        "restructurings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("overdue_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("new_schedule", postgresql.JSONB, nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "approved", "rejected", name="restructuring_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision_comment", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_restructurings_deal_id", "restructurings", ["deal_id"])
    op.create_index("ix_restructurings_status", "restructurings", ["status"])

    # ─── documents ────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", postgresql.ENUM("client", "deal", "payment", "overdue_case", "contact_log", name="document_entity_type", create_type=False), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_url", sa.String(2048), nullable=False),
        sa.Column("doc_type", postgresql.ENUM("contract", "collateral", "photo", "receipt", "act", "notification", "other", name="document_type", create_type=False), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_entity_type", "documents", ["entity_type"])
    op.create_index("ix_documents_entity_id", "documents", ["entity_id"])

    # ─── notifications_log ────────────────────────────────────────────────────
    op.create_table(
        "notifications_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("channel", postgresql.ENUM("sms", "telegram", name="notification_channel", create_type=False), nullable=False),
        sa.Column("template", sa.String(100), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "sent", "failed", name="notification_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_log_client_id", "notifications_log", ["client_id"])
    op.create_index("ix_notifications_log_status", "notifications_log", ["status"])

    # ─── system_settings ──────────────────────────────────────────────────────
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)

    # ─── calendar_tasks ───────────────────────────────────────────────────────
    op.create_table(
        "calendar_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "done", "cancelled", name="calendar_task_status", create_type=False), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_calendar_tasks_user_id", "calendar_tasks", ["user_id"])
    op.create_index("ix_calendar_tasks_due_date", "calendar_tasks", ["due_date"])

    # ─── Audit trigger function ────────────────────────────────────────────────
    op.execute(AUDIT_TRIGGER_FUNCTION)

    for table_name in AUDITED_TABLES:
        op.execute(f"""
            CREATE TRIGGER audit_{table_name}
            AFTER INSERT OR UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();
        """)

    # ─── REVOKE DELETE and UPDATE on audit_log ────────────────────────────────
    # This prevents accidental modifications via ORM or direct SQL
    op.execute("""
        DO $$
        BEGIN
            -- Revoke from all non-superuser roles that may exist
            -- In production: create a dedicated app_user role and revoke there
            -- This is a belt-and-suspenders protection
            EXECUTE 'REVOKE DELETE ON audit_log FROM ' || current_user;
            EXECUTE 'REVOKE UPDATE ON audit_log FROM ' || current_user;
        EXCEPTION WHEN others THEN
            -- Ignore if the role doesn't have the privilege to begin with
            NULL;
        END
        $$;
    """)

    # ─── Seed default system settings ─────────────────────────────────────────
    import uuid as uuid_mod
    import json
    from datetime import datetime

    defaults = [
        ("sb_threshold_days", 7),
        ("red_zone_days", 14),
        ("murabaha_default_markup_pct", 15),
        ("musharaka_default_bank_share", 0.3),
        ("notification_templates", {
            "reminder_3d": "Уважаемый {name}, напоминаем о платеже {amount} ₽, ожидаемом {date}.",
            "reminder_1d": "Уважаемый {name}, завтра {date} ожидается платёж {amount} ₽.",
            "overdue": "Уважаемый {name}, платёж {amount} ₽ просрочен с {date}. Просим связаться с банком.",
        }),
    ]
    for key, value in defaults:
        op.execute(
            sa.text(
                "INSERT INTO system_settings (id, key, value) "
                "VALUES (CAST(:id AS uuid), :key, CAST(:val AS jsonb))"
            ).bindparams(
                id=str(uuid_mod.uuid4()),
                key=key,
                val=json.dumps(value),
            )
        )


def downgrade() -> None:
    for table_name in reversed(AUDITED_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS audit_{table_name} ON {table_name}")

    op.execute("DROP FUNCTION IF EXISTS audit_trigger_fn() CASCADE")

    for table in [
        "calendar_tasks", "system_settings", "notifications_log", "documents",
        "restructurings", "payment_promises", "contact_logs", "overdue_cases",
        "payments", "payment_schedules", "deal_params", "deals", "clients",
        "audit_log", "users",
    ]:
        op.drop_table(table)

    for enum in [
        "calendar_task_status", "notification_status", "notification_channel",
        "document_type", "document_entity_type", "restructuring_status",
        "contact_type", "overdue_case_status", "installment_type",
        "payment_method", "payment_status", "deal_status", "deal_type",
        "kyc_status", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
