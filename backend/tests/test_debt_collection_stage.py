"""Tests for debt collection stage computation."""
from backend.services.debt_collection_stage_service import (
    DebtStageSettings,
    compute_collection_stage,
)


def _settings() -> DebtStageSettings:
    return DebtStageSettings(
        stage_2_days=30,
        stage_2_installments=2,
        stage_3_days=60,
        stage_3_installments=3,
        stage_4_days=90,
    )


def test_stage_1_below_thresholds():
    assert compute_collection_stage(29, 2, _settings()) == 1
    assert compute_collection_stage(30, 1, _settings()) == 1


def test_stage_2_requires_days_and_installments():
    assert compute_collection_stage(30, 2, _settings()) == 2
    assert compute_collection_stage(45, 2, _settings()) == 2


def test_stage_3_requires_days_and_installments():
    assert compute_collection_stage(60, 3, _settings()) == 3
    assert compute_collection_stage(60, 2, _settings()) == 2


def test_stage_4_by_days_only():
    assert compute_collection_stage(90, 1, _settings()) == 4
    assert compute_collection_stage(120, 2, _settings()) == 4


def test_stage_downgrade_when_metrics_improve():
    s = _settings()
    assert compute_collection_stage(90, 3, s) == 4
    assert compute_collection_stage(45, 2, s) == 2
    assert compute_collection_stage(10, 1, s) == 1


def test_manager_pct_stage_3_zero():
    from backend.services.payment_commission_service import _manager_pct_for_stage

    cfg = {"manager_pct": 5.0, "manager_stage3_pct": 0.0}
    assert _manager_pct_for_stage(2, cfg) == 5.0
    assert _manager_pct_for_stage(3, cfg) == 0.0
    assert _manager_pct_for_stage(4, cfg) == 0.0
