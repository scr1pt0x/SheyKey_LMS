import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class DocumentEntityType(str, PyEnum):
    client = "client"
    deal = "deal"
    payment = "payment"
    overdue_case = "overdue_case"
    contact_log = "contact_log"


class DocumentType(str, PyEnum):
    contract = "contract"
    collateral = "collateral"
    photo = "photo"
    receipt = "receipt"
    act = "act"
    notification = "notification"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[DocumentEntityType] = mapped_column(
        Enum(DocumentEntityType, name="document_entity_type"), nullable=False, index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])
