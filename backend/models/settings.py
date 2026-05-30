import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_system_settings_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[dict | list | str | int | float | None] = mapped_column(JSONB, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    updater: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by])


# Default system settings keys
class SettingKey:
    SB_THRESHOLD_DAYS = "sb_threshold_days"
    NOTIFICATION_TEMPLATES = "notification_templates"
    SMS_API_KEY = "sms_api_key"
    SMS_FROM = "sms_from"
    TG_BOT_URL = "tg_bot_url"
    BOT_SECRET = "bot_secret"
    MURABAHA_DEFAULT_MARKUP_PCT = "murabaha_default_markup_pct"
    IJARA_DEFAULT_PARAMS = "ijara_default_params"
    RED_ZONE_DAYS = "red_zone_days"
    DIRECTOR_EMAIL = "director_email"
    MANAGER_BONUS_PCT = "manager_bonus_pct"

    DEFAULTS: dict = {
        SB_THRESHOLD_DAYS: 7,
        RED_ZONE_DAYS: 14,
        MURABAHA_DEFAULT_MARKUP_PCT: 15,
        NOTIFICATION_TEMPLATES: {
            "reminder_3d": "Уважаемый {name}, напоминаем о платеже {amount} ₽, ожидаемом {date}.",
            "reminder_1d": "Уважаемый {name}, завтра {date} ожидается платёж {amount} ₽.",
            "overdue": "Уважаемый {name}, платёж {amount} ₽ просрочен с {date}. Просим связаться с банком.",
        },
    }
