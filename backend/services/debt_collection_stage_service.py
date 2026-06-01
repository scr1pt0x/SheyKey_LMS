"""Collection stage (1–4) and SB assignee for overdue cases."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.deal import Deal
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.settings import SettingKey, SystemSetting
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService
from backend.services.overdue_case_service import _load_sb_debt_lines
from backend.services.push_service import notify_staff


@dataclass
class DebtStageSettings:
    stage_2_days: int = 30
    stage_2_installments: int = 2
    stage_3_days: int = 60
    stage_3_installments: int = 3
    stage_4_days: int = 90
    stage_2_sb_user_id: uuid.UUID | None = None
    stage_3_sb_user_id: uuid.UUID | None = None
    stage_4_sb_user_id: uuid.UUID | None = None


def compute_collection_stage(
    days_overdue: int,
    overdue_installments: int,
    settings: DebtStageSettings,
) -> int:
    if days_overdue >= settings.stage_4_days:
        return 4
    if days_overdue >= settings.stage_3_days and overdue_installments >= settings.stage_3_installments:
        return 3
    if days_overdue >= settings.stage_2_days and overdue_installments >= settings.stage_2_installments:
        return 2
    return 1


def _parse_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return int(value) if value else 0


def _parse_uuid(value) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


async def load_debt_stage_settings(db: AsyncSession) -> DebtStageSettings:
    keys = [
        SettingKey.DEBT_STAGE_2_DAYS,
        SettingKey.DEBT_STAGE_2_INSTALLMENTS,
        SettingKey.DEBT_STAGE_3_DAYS,
        SettingKey.DEBT_STAGE_3_INSTALLMENTS,
        SettingKey.DEBT_STAGE_4_DAYS,
        SettingKey.DEBT_STAGE_2_SB_USER_ID,
        SettingKey.DEBT_STAGE_3_SB_USER_ID,
        SettingKey.DEBT_STAGE_4_SB_USER_ID,
    ]
    rows = await db.execute(select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(keys)))
    raw = {k: v for k, v in rows.all()}
    defaults = SettingKey.DEFAULTS
    return DebtStageSettings(
        stage_2_days=_parse_int(raw.get(SettingKey.DEBT_STAGE_2_DAYS, defaults[SettingKey.DEBT_STAGE_2_DAYS])),
        stage_2_installments=_parse_int(
            raw.get(SettingKey.DEBT_STAGE_2_INSTALLMENTS, defaults[SettingKey.DEBT_STAGE_2_INSTALLMENTS])
        ),
        stage_3_days=_parse_int(raw.get(SettingKey.DEBT_STAGE_3_DAYS, defaults[SettingKey.DEBT_STAGE_3_DAYS])),
        stage_3_installments=_parse_int(
            raw.get(SettingKey.DEBT_STAGE_3_INSTALLMENTS, defaults[SettingKey.DEBT_STAGE_3_INSTALLMENTS])
        ),
        stage_4_days=_parse_int(raw.get(SettingKey.DEBT_STAGE_4_DAYS, defaults[SettingKey.DEBT_STAGE_4_DAYS])),
        stage_2_sb_user_id=_parse_uuid(raw.get(SettingKey.DEBT_STAGE_2_SB_USER_ID)),
        stage_3_sb_user_id=_parse_uuid(raw.get(SettingKey.DEBT_STAGE_3_SB_USER_ID)),
        stage_4_sb_user_id=_parse_uuid(raw.get(SettingKey.DEBT_STAGE_4_SB_USER_ID)),
    )


def resolve_sb_collection_stage(user_id: uuid.UUID, settings: DebtStageSettings) -> int | None:
    """Which collection stage (2–4) this SB user owns, if configured."""
    if settings.stage_2_sb_user_id == user_id:
        return 2
    if settings.stage_3_sb_user_id == user_id:
        return 3
    if settings.stage_4_sb_user_id == user_id:
        return 4
    return None


def _sb_user_id_for_stage(stage: int, settings: DebtStageSettings) -> uuid.UUID | None:
    if stage == 2:
        return settings.stage_2_sb_user_id
    if stage == 3:
        return settings.stage_3_sb_user_id
    if stage == 4:
        return settings.stage_4_sb_user_id
    return None


async def _notify_director_missing_assignee(db: AsyncSession, case_id: uuid.UUID, stage: int) -> None:
    directors = (
        await db.execute(
            select(User).where(User.role == UserRole.director).where(User.is_active == True)  # noqa: E712
        )
    ).scalars().all()
    for director in directors:
        await notify_staff(
            db=db,
            user_id=director.id,
            title=f"Этап {stage}: не назначен сотрудник СБ",
            body="Укажите ответственного в настройках системы.",
            entity_type="overdue_cases",
            entity_id=str(case_id),
            action_url=f"/director/settings",
        )


async def apply_collection_stage(
    db: AsyncSession,
    case: OverdueCase,
    deal: Deal,
    *,
    today: date | None = None,
    settings: DebtStageSettings | None = None,
) -> OverdueCase:
    """Recalculate stage metrics and assign SB / manager responsibility."""
    today = today or datetime.now(timezone.utc).date()
    settings = settings or await load_debt_stage_settings(db)

    debt_lines = await _load_sb_debt_lines(db, deal.id, today)
    overdue_count = len(debt_lines)
    stage = compute_collection_stage(case.days_overdue, overdue_count, settings)

    case.overdue_installments_count = overdue_count
    stage_changed = case.collection_stage != stage
    case.collection_stage = stage
    if stage_changed:
        case.stage_changed_at = datetime.now(timezone.utc)

    target_sb_id = _sb_user_id_for_stage(stage, settings)

    if stage == 1:
        if case.sb_user_id is not None:
            case.sb_user_id = None
            case.assigned_at = None
            if case.status == OverdueCaseStatus.in_progress:
                case.status = OverdueCaseStatus.new
    else:
        if target_sb_id is None:
            logger.warning(
                "debt stage {}: no SB user configured for case {}",
                stage,
                case.id,
            )
            await _notify_director_missing_assignee(db, case.id, stage)
        elif case.sb_user_id != target_sb_id:
            case.sb_user_id = target_sb_id
            case.assigned_at = datetime.now(timezone.utc)
            case.status = OverdueCaseStatus.in_progress
            sb_user = await db.get(User, target_sb_id)
            sb_name = sb_user.name if sb_user else "СБ"
            await notify_staff(
                db=db,
                user_id=target_sb_id,
                title=f"Дело на этапе {stage}",
                body=f"Клиент: просрочка {case.days_overdue} дн., долг {case.total_debt} ₽",
                entity_type="overdue_cases",
                entity_id=str(case.id),
                action_url=f"/sb/cases/{case.id}",
            )

    if stage_changed:
        await AuditService.log(
            db=db,
            user_id=None,
            action="STAGE_CHANGE",
            entity="overdue_cases",
            entity_id=str(case.id),
            old_val=None,
            new_val={
                "collection_stage": stage,
                "overdue_installments_count": overdue_count,
                "sb_user_id": str(case.sb_user_id) if case.sb_user_id else None,
                "manager_id": str(deal.manager_id),
            },
            ip=None,
        )

    await db.flush()
    return case
