import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.payment import PaymentMethod


class ManagerCashEntryKind(str, PyEnum):
    income = "income"
    expense = "expense"


class ManagerCashEntry(Base):
    """Ручная операция по кассе менеджера (приход или расход)."""

    __tablename__ = "manager_cash_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_kind: Mapped[ManagerCashEntryKind] = mapped_column(
        Enum(ManagerCashEntryKind, name="manager_cash_entry_kind"),
        nullable=False,
        default=ManagerCashEntryKind.income,
        server_default=ManagerCashEntryKind.income.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    manager: Mapped["User"] = relationship("User", foreign_keys=[manager_id])
