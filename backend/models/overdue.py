import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class OverdueCaseStatus(str, PyEnum):
    new = "new"
    in_progress = "in_progress"
    agreed = "agreed"
    closed = "closed"


class ContactType(str, PyEnum):
    call = "call"
    meeting = "meeting"
    sms = "sms"
    telegram = "telegram"
    other = "other"


class OverdueCase(Base):
    __tablename__ = "overdue_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sb_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[OverdueCaseStatus] = mapped_column(
        Enum(OverdueCaseStatus, name="overdue_case_status"),
        default=OverdueCaseStatus.new,
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_debt: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deal: Mapped["Deal"] = relationship("Deal", back_populates="overdue_cases")
    sb_user: Mapped["User | None"] = relationship(
        "User", back_populates="overdue_cases", foreign_keys=[sb_user_id]
    )
    contact_logs: Mapped[list["ContactLog"]] = relationship(
        "ContactLog", back_populates="case", cascade="all, delete-orphan"
    )
    payment_promises: Mapped[list["PaymentPromise"]] = relationship(
        "PaymentPromise", back_populates="case", cascade="all, delete-orphan"
    )
    restructurings: Mapped[list["Restructuring"]] = relationship(
        "Restructuring", back_populates="case"
    )


class ContactLog(Base):
    __tablename__ = "contact_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("overdue_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sb_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[ContactType] = mapped_column(
        Enum(ContactType, name="contact_type"), nullable=False
    )
    result: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped["OverdueCase"] = relationship("OverdueCase", back_populates="contact_logs")
    sb_user: Mapped["User"] = relationship("User", foreign_keys=[sb_user_id])


class PaymentPromise(Base):
    __tablename__ = "payment_promises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("overdue_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    promised_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    promised_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    is_fulfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    case: Mapped["OverdueCase"] = relationship("OverdueCase", back_populates="payment_promises")
