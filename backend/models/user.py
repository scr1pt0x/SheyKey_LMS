import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class UserRole(str, PyEnum):
    manager = "manager"
    sb = "sb"
    director = "director"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    clients: Mapped[list["Client"]] = relationship(
        "Client", back_populates="manager", foreign_keys="[Client.manager_id]"
    )
    deals: Mapped[list["Deal"]] = relationship(
        "Deal", back_populates="manager", foreign_keys="[Deal.manager_id]"
    )
    overdue_cases: Mapped[list["OverdueCase"]] = relationship(
        "OverdueCase", back_populates="sb_user", foreign_keys="[OverdueCase.sb_user_id]"
    )
    calendar_tasks: Mapped[list["CalendarTask"]] = relationship(
        "CalendarTask", back_populates="user"
    )
