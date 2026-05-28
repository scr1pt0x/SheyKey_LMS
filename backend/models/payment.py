import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class PaymentStatus(str, PyEnum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    partial = "partial"


class PaymentMethod(str, PyEnum):
    cash = "cash"
    transfer = "transfer"
    card = "card"
    other = "other"


class PaymentSchedule(Base):
    __tablename__ = "payment_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.pending,
        nullable=False,
        index=True,
    )
    installment_type: Mapped[str] = mapped_column(
        Enum("rent", "buyout", "principal", name="installment_type"),
        default="principal",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deal: Mapped["Deal"] = relationship("Deal", back_populates="payment_schedules")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="schedule")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_schedules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    receipt_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    schedule: Mapped["PaymentSchedule"] = relationship("PaymentSchedule", back_populates="payments")
    deal: Mapped["Deal"] = relationship("Deal", back_populates="payments")
    confirmed_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[confirmed_by]
    )
    recorded_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[recorded_by]
    )
