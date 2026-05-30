import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    share_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    investment_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    joined_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    distributions: Mapped[list["ProfitDistribution"]] = relationship(
        "ProfitDistribution", back_populates="investor"
    )
