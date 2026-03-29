"""
AssumptionChecker — 一级市场假设验证服务。

职责：
  - 对 KeyAssumptions 中的每条假设，结合 FinancialLens 数据做自动核查
  - 硬假设违反时标记 status=VIOLATED，触发 PathFork
  - 软假设仅更新状态，不触发分叉
"""

from __future__ import annotations

from src.sandbox.schemas.primary_market import (
    AssumptionLevel,
    AssumptionStatus,
    FinancialLens,
    KeyAssumption,
    KeyAssumptions,
)

# 硬假设的量化核查规则（MVP 内置，后续可配置或由 LLM 判断）
_LTV_CAC_MIN = 3.0   # 企业客户 LTV/CAC 最低门槛
_RUNWAY_MIN = 14     # 最低 runway 月数


class AssumptionChecker:
    """对 KeyAssumptions 集合进行自动核查，返回更新后的集合。"""

    def check(
        self,
        assumptions: KeyAssumptions,
        financial_lens: FinancialLens,
    ) -> KeyAssumptions:
        updated: list[KeyAssumption] = []
        for assumption in assumptions.items:
            updated.append(self._check_one(assumption, financial_lens))
        return KeyAssumptions(items=updated)

    def _check_one(
        self,
        assumption: KeyAssumption,
        financial_lens: FinancialLens,
    ) -> KeyAssumption:
        """
        对单条假设进行核查。
        能自动判断的硬假设直接更新 status；无法自动判断的保持 unverified。
        """
        description = assumption.description.lower()

        # 规则 1：LTV/CAC > 3x
        if "ltv/cac" in description or "ltv_cac" in description:
            if financial_lens.ltv_cac_ratio is not None:
                status = (
                    AssumptionStatus.CONFIRMED
                    if financial_lens.ltv_cac_ratio >= _LTV_CAC_MIN
                    else AssumptionStatus.VIOLATED
                )
                return assumption.model_copy(update={"status": status})

        # 规则 2：Runway 充足（14 个月内完成融资或盈亏平衡）
        if "runway" in description or "14 个月" in description or "14 months" in description:
            if financial_lens.runway_months is not None:
                status = (
                    AssumptionStatus.CONFIRMED
                    if financial_lens.runway_months >= _RUNWAY_MIN
                    else AssumptionStatus.VIOLATED
                )
                return assumption.model_copy(update={"status": status})

        # 其余假设（大厂竞争、监管等）无法从财务数据自动判断，保持原状
        return assumption
