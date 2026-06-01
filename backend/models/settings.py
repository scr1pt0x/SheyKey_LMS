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
    NOTIFICATION_TEMPLATES = "notification_templates"
    SMS_API_KEY = "sms_api_key"
    SMS_FROM = "sms_from"
    TG_BOT_URL = "tg_bot_url"
    BOT_SECRET = "bot_secret"
    MURABAHA_RATE_WITH_DOWN_PCT = "murabaha_rate_with_down_pct"
    MURABAHA_RATE_WITHOUT_DOWN_PCT = "murabaha_rate_without_down_pct"
    MURABAHA_RATE_AUTO_PCT = "murabaha_rate_auto_pct"
    MURABAHA_SELLER_FIO = "murabaha_seller_fio"
    IJARA_DEFAULT_PARAMS = "ijara_default_params"
    RED_ZONE_DAYS = "red_zone_days"
    DIRECTOR_EMAIL = "director_email"
    MANAGER_BONUS_PCT = "manager_bonus_pct"
    DEBT_STAGE_2_DAYS = "debt_stage_2_days"
    DEBT_STAGE_2_INSTALLMENTS = "debt_stage_2_installments"
    DEBT_STAGE_3_DAYS = "debt_stage_3_days"
    DEBT_STAGE_3_INSTALLMENTS = "debt_stage_3_installments"
    DEBT_STAGE_4_DAYS = "debt_stage_4_days"
    DEBT_STAGE_2_SB_USER_ID = "debt_stage_2_sb_user_id"
    DEBT_STAGE_3_SB_USER_ID = "debt_stage_3_sb_user_id"
    DEBT_STAGE_4_SB_USER_ID = "debt_stage_4_sb_user_id"
    MANAGER_PAYMENT_COMMISSION_PCT = "manager_payment_commission_pct"
    MANAGER_PAYMENT_COMMISSION_FROM_STAGE_3_PCT = "manager_payment_commission_from_stage_3_pct"
    SB_COMMISSION_STAGE_2_PCT = "sb_commission_stage_2_pct"
    SB_COMMISSION_STAGE_3_PCT = "sb_commission_stage_3_pct"
    SB_COMMISSION_STAGE_4_PCT = "sb_commission_stage_4_pct"

    DEFAULTS: dict = {
        RED_ZONE_DAYS: 14,
        MURABAHA_RATE_WITH_DOWN_PCT: 4,
        MURABAHA_RATE_WITHOUT_DOWN_PCT: 5,
        MURABAHA_RATE_AUTO_PCT: 3.3,
        MURABAHA_SELLER_FIO: "SheyKey Finance",
        DEBT_STAGE_2_DAYS: 30,
        DEBT_STAGE_2_INSTALLMENTS: 2,
        DEBT_STAGE_3_DAYS: 60,
        DEBT_STAGE_3_INSTALLMENTS: 3,
        DEBT_STAGE_4_DAYS: 90,
        MANAGER_PAYMENT_COMMISSION_PCT: 0,
        MANAGER_PAYMENT_COMMISSION_FROM_STAGE_3_PCT: 0,
        SB_COMMISSION_STAGE_2_PCT: 0,
        SB_COMMISSION_STAGE_3_PCT: 0,
        SB_COMMISSION_STAGE_4_PCT: 0,
        NOTIFICATION_TEMPLATES: {
            "reminder_3d": "Уважаемый {name}, напоминаем о платеже {amount} ₽, ожидаемом {date}.",
            "reminder_1d": "Уважаемый {name}, завтра {date} ожидается платёж {amount} ₽.",
            "overdue": "Уважаемый {name}, платёж {amount} ₽ просрочен с {date}. Просим связаться с банком.",
        },
    }
