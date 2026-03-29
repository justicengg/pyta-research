"""Unit tests for AssumptionChecker and PathForkService."""

import pytest

from src.sandbox.schemas.primary_market import (
    AssumptionLevel,
    AssumptionStatus,
    FinancialLens,
    KeyAssumption,
    KeyAssumptions,
)
from src.sandbox.services.assumption_checker import AssumptionChecker
from src.sandbox.services.path_fork import PathForkService


def _make_ltv_cac_assumption(status=AssumptionStatus.UNVERIFIED) -> KeyAssumption:
    return KeyAssumption(
        level=AssumptionLevel.HARD,
        description="企业客户 LTV/CAC > 3x，获客效率可持续",
        status=status,
        triggers_path_fork=True,
    )


def _make_runway_assumption(status=AssumptionStatus.UNVERIFIED) -> KeyAssumption:
    return KeyAssumption(
        level=AssumptionLevel.HARD,
        description="在 14 个月 runway 内完成 B 轮融资或达到盈亏平衡",
        status=status,
        triggers_path_fork=True,
    )


def _make_soft_assumption() -> KeyAssumption:
    return KeyAssumption(
        level=AssumptionLevel.SOFT,
        description="大厂不会在 18 个月内推出直接竞争产品",
        status=AssumptionStatus.UNVERIFIED,
    )


class TestAssumptionChecker:
    def setup_method(self):
        self.checker = AssumptionChecker()

    def test_ltv_cac_confirmed_when_above_threshold(self):
        ka = KeyAssumptions(items=[_make_ltv_cac_assumption()])
        fl = FinancialLens(ltv_cac_ratio=4.5)
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.CONFIRMED

    def test_ltv_cac_violated_when_below_threshold(self):
        ka = KeyAssumptions(items=[_make_ltv_cac_assumption()])
        fl = FinancialLens(ltv_cac_ratio=1.8)
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.VIOLATED

    def test_ltv_cac_unverified_when_no_data(self):
        ka = KeyAssumptions(items=[_make_ltv_cac_assumption()])
        fl = FinancialLens()
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.UNVERIFIED

    def test_runway_confirmed_when_sufficient(self):
        ka = KeyAssumptions(items=[_make_runway_assumption()])
        fl = FinancialLens(runway_months=18)
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.CONFIRMED

    def test_runway_violated_when_insufficient(self):
        ka = KeyAssumptions(items=[_make_runway_assumption()])
        fl = FinancialLens(runway_months=10)
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.VIOLATED

    def test_soft_assumption_unchanged(self):
        ka = KeyAssumptions(items=[_make_soft_assumption()])
        fl = FinancialLens(ltv_cac_ratio=5.0, runway_months=20)
        result = self.checker.check(ka, fl)
        assert result.items[0].status == AssumptionStatus.UNVERIFIED

    def test_mixed_assumptions(self):
        ka = KeyAssumptions(items=[
            _make_ltv_cac_assumption(),
            _make_runway_assumption(),
            _make_soft_assumption(),
        ])
        fl = FinancialLens(ltv_cac_ratio=2.0, runway_months=20)
        result = self.checker.check(ka, fl)
        statuses = {a.description[:10]: a.status for a in result.items}
        # LTV/CAC violated (2.0 < 3.0)
        assert result.items[0].status == AssumptionStatus.VIOLATED
        # Runway confirmed (20 >= 14)
        assert result.items[1].status == AssumptionStatus.CONFIRMED
        # Soft unchanged
        assert result.items[2].status == AssumptionStatus.UNVERIFIED


class TestPathForkService:
    def setup_method(self):
        self.service = PathForkService()

    def test_no_forks_when_no_violations(self):
        ka = KeyAssumptions(items=[
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="LTV/CAC > 3x",
                status=AssumptionStatus.CONFIRMED,
                triggers_path_fork=True,
            )
        ])
        forks = self.service.generate(ka)
        assert forks == []

    def test_fork_generated_for_violated_hard(self):
        ka = KeyAssumptions(items=[
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="14-month runway",
                status=AssumptionStatus.VIOLATED,
                triggers_path_fork=True,
            )
        ])
        forks = self.service.generate(ka)
        assert len(forks) == 1
        assert forks[0].trigger_assumption == "14-month runway"
        assert forks[0].fork_id  # non-empty

    def test_two_violations_produce_two_forks(self):
        ka = KeyAssumptions(items=[
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="LTV/CAC > 3x",
                status=AssumptionStatus.VIOLATED,
                triggers_path_fork=True,
            ),
            KeyAssumption(
                level=AssumptionLevel.HARD,
                description="14-month runway",
                status=AssumptionStatus.VIOLATED,
                triggers_path_fork=True,
            ),
        ])
        forks = self.service.generate(ka)
        assert len(forks) == 2

    def test_soft_assumption_violation_not_forked(self):
        """软假设即使 violated 也不生成 PathFork（violated_hard 只返回硬假设）。"""
        ka = KeyAssumptions(items=[
            KeyAssumption(
                level=AssumptionLevel.SOFT,
                description="No big-tech competitor",
                status=AssumptionStatus.VIOLATED,
            )
        ])
        forks = self.service.generate(ka)
        assert forks == []
