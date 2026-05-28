import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog


class AuditService:
    """Central service for writing to the append-only audit_log table."""

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        entity: str,
        user_id: str | None = None,
        entity_id: str | None = None,
        old_val: dict | None = None,
        new_val: dict | None = None,
        ip: str | None = None,
    ) -> None:
        entry = AuditLog(
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            entity=entity,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            old_val=old_val,
            new_val=new_val,
            ip=ip,
        )
        db.add(entry)
        # Do not commit here — caller commits the parent transaction
