import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class PaymentCommissionSplit(Base):
    __tablename__ = "payment_commission_splits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collection_stage_at_payment: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    manager_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    manager_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    sb_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sb_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    sb_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    payment: Mapped["Payment"] = relationship("Payment", back_populates="commission_split")
    deal: Mapped["Deal"] = relationship("Deal")
