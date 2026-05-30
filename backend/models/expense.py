import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class ExpenseCategory(str, PyEnum):
    cost_of_goods = "cost_of_goods"
    operational = "operational"
    salary = "salary"
    rent = "rent"
    other = "other"


EXPENSE_CATEGORY_LABELS = {
    ExpenseCategory.cost_of_goods: "Себестоимость",
    ExpenseCategory.operational: "Операционные расходы",
    ExpenseCategory.salary: "Зарплаты",
    ExpenseCategory.rent: "Аренда",
    ExpenseCategory.other: "Прочее",
}


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profit_periods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    period: Mapped["ProfitPeriod | None"] = relationship("ProfitPeriod", back_populates="expenses")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
