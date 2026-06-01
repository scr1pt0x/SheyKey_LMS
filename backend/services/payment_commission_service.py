"""Per-payment commission splits (manager / SB) by collection stage."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.deal import Deal
from backend.models.overdue import OverdueCase, OverdueCaseStatus
from backend.models.payment import Payment
from backend.models.payment_commission import PaymentCommissionSplit
from backend.models.settings import SettingKey, SystemSetting
from backend.services.audit_service import AuditService


def _parse_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _load_commission_settings(db: AsyncSession) -> dict[str, float]:
    keys = [
        SettingKey.MANAGER_PAYMENT_COMMISSION_PCT,
        SettingKey.MANAGER_PAYMENT_COMMISSION_FROM_STAGE_3_PCT,
        SettingKey.SB_COMMISSION_STAGE_2_PCT,
        SettingKey.SB_COMMISSION_STAGE_3_PCT,
        SettingKey.SB_COMMISSION_STAGE_4_PCT,
    ]
    rows = await db.execute(select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(keys)))
    raw = {k: v for k, v in rows.all()}
    defaults = SettingKey.DEFAULTS
    return {
        "manager_pct": _parse_float(
            raw.get(SettingKey.MANAGER_PAYMENT_COMMISSION_PCT),
            defaults.get(SettingKey.MANAGER_PAYMENT_COMMISSION_PCT, 0),
        ),
        "manager_stage3_pct": _parse_float(
            raw.get(SettingKey.MANAGER_PAYMENT_COMMISSION_FROM_STAGE_3_PCT),
            defaults.get(SettingKey.MANAGER_PAYMENT_COMMISSION_FROM_STAGE_3_PCT, 0),
        ),
        "sb_stage_2_pct": _parse_float(
            raw.get(SettingKey.SB_COMMISSION_STAGE_2_PCT),
            defaults.get(SettingKey.SB_COMMISSION_STAGE_2_PCT, 0),
        ),
        "sb_stage_3_pct": _parse_float(
            raw.get(SettingKey.SB_COMMISSION_STAGE_3_PCT),
            defaults.get(SettingKey.SB_COMMISSION_STAGE_3_PCT, 0),
        ),
        "sb_stage_4_pct": _parse_float(
            raw.get(SettingKey.SB_COMMISSION_STAGE_4_PCT),
            defaults.get(SettingKey.SB_COMMISSION_STAGE_4_PCT, 0),
        ),
    }


async def _open_case_stage(db: AsyncSession, deal_id: uuid.UUID) -> int:
    case = (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.deal_id == deal_id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
        )
    ).scalar_one_or_none()
    return case.collection_stage if case else 1


def _manager_pct_for_stage(stage: int, settings: dict[str, float]) -> float:
    if stage >= 3:
        return settings["manager_stage3_pct"]
    return settings["manager_pct"]


def _sb_pct_for_stage(stage: int, settings: dict[str, float]) -> float:
    if stage == 2:
        return settings["sb_stage_2_pct"]
    if stage == 3:
        return settings["sb_stage_3_pct"]
    if stage == 4:
        return settings["sb_stage_4_pct"]
    return 0.0


async def record_commission_splits_for_payments(
    db: AsyncSession,
    deal_id: uuid.UUID,
    payments: list[Payment],
    *,
    actor_user_id: str | None = None,
) -> list[PaymentCommissionSplit]:
    if not payments:
        return []

    deal = await db.get(Deal, deal_id)
    if not deal:
        return []

    stage = await _open_case_stage(db, deal_id)
    cfg = await _load_commission_settings(db)
    manager_pct = _manager_pct_for_stage(stage, cfg)
    sb_pct = _sb_pct_for_stage(stage, cfg)

    open_case = (
        await db.execute(
            select(OverdueCase)
            .where(OverdueCase.deal_id == deal_id)
            .where(OverdueCase.status != OverdueCaseStatus.closed)
        )
    ).scalar_one_or_none()
    sb_user_id = open_case.sb_user_id if open_case else None

    splits: list[PaymentCommissionSplit] = []
    for payment in payments:
        amount = Decimal(str(payment.amount))
        manager_amount = (amount * Decimal(str(manager_pct)) / Decimal("100")).quantize(Decimal("0.01"))
        sb_amount = (amount * Decimal(str(sb_pct)) / Decimal("100")).quantize(Decimal("0.01"))

        split = PaymentCommissionSplit(
            payment_id=payment.id,
            deal_id=deal_id,
            collection_stage_at_payment=stage,
            manager_id=deal.manager_id,
            manager_amount=float(manager_amount),
            manager_pct=manager_pct,
            sb_user_id=sb_user_id,
            sb_amount=float(sb_amount),
            sb_pct=sb_pct,
        )
        db.add(split)
        splits.append(split)

    if splits and actor_user_id:
        await AuditService.log(
            db=db,
            user_id=actor_user_id,
            action="COMMISSION_SPLIT",
            entity="payment_commission_splits",
            entity_id=str(splits[0].id),
            new_val={
                "deal_id": str(deal_id),
                "stage": stage,
                "payments": len(splits),
                "manager_pct": manager_pct,
                "sb_pct": sb_pct,
            },
            ip=None,
        )

    await db.flush()
    return splits
