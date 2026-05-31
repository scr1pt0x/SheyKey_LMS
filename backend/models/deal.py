import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class DealType(str, PyEnum):
    murabaha = "murabaha"
    ijara = "ijara"


class DealStatus(str, PyEnum):
    draft = "draft"
    active = "active"
    closed = "closed"
    overdue = "overdue"


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    type: Mapped[DealType] = mapped_column(
        Enum(DealType, name="deal_type"), nullable=False, index=True
    )
    status: Mapped[DealStatus] = mapped_column(
        Enum(DealStatus, name="deal_status"),
        default=DealStatus.draft,
        nullable=False,
        index=True,
    )
    principal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    markup: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="deals")
    manager: Mapped["User"] = relationship(
        "User", back_populates="deals", foreign_keys=[manager_id]
    )
    approver: Mapped["User | None"] = relationship(
        "User", foreign_keys=[approved_by]
    )
    params: Mapped[list["DealParam"]] = relationship(
        "DealParam", back_populates="deal", cascade="all, delete-orphan"
    )
    payment_schedules: Mapped[list["PaymentSchedule"]] = relationship(
        "PaymentSchedule", back_populates="deal", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="deal"
    )
    overdue_cases: Mapped[list["OverdueCase"]] = relationship(
        "OverdueCase", back_populates="deal"
    )


class DealParam(Base):
    __tablename__ = "deal_params"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[dict | float | str | None] = mapped_column(JSONB, nullable=True)

    deal: Mapped["Deal"] = relationship("Deal", back_populates="params")
