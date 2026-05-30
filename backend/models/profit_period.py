import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class ProfitPeriodStatus(str, PyEnum):
    draft = "draft"
    approved = "approved"


class ProfitPeriod(Base):
    __tablename__ = "profit_periods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ProfitPeriodStatus] = mapped_column(
        Enum(ProfitPeriodStatus, name="profit_period_status"),
        default=ProfitPeriodStatus.draft,
        nullable=False,
        index=True,
    )
    gross_revenue: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_expenses: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    manager_bonus_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    manager_bonus_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    net_distributable: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
    distributions: Mapped[list["ProfitDistribution"]] = relationship(
        "ProfitDistribution", back_populates="period", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="period")


class ProfitDistribution(Base):
    __tablename__ = "profit_distributions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profit_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    share_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    period: Mapped["ProfitPeriod"] = relationship("ProfitPeriod", back_populates="distributions")
    investor: Mapped["Investor"] = relationship("Investor", back_populates="distributions")
