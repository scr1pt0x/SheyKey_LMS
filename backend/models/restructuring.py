import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class RestructuringStatus(str, PyEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Restructuring(Base):
    __tablename__ = "restructurings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("overdue_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    new_schedule: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[RestructuringStatus] = mapped_column(
        Enum(RestructuringStatus, name="restructuring_status"),
        default=RestructuringStatus.pending,
        nullable=False,
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deal: Mapped["Deal"] = relationship("Deal", back_populates="restructurings")
    case: Mapped["OverdueCase | None"] = relationship("OverdueCase", back_populates="restructurings")
    initiator: Mapped["User"] = relationship("User", foreign_keys=[initiated_by])
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
