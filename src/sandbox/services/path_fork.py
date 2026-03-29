"""
PathForkService — 一级市场路径分叉服务。

职责：
  - 当硬假设被标记为 VIOLATED 时，生成对应的 PathFork 节点
  - 每条被违反的硬假设生成一个 PathFork
  - PathFork 描述两条路径：假设成立 vs 假设失败
"""

from __future__ import annotations

from uuid import uuid4

from src.sandbox.schemas.primary_market import (
    AssumptionStatus,
    KeyAssumptions,
    PathFork,
    PathForkTrigger,
)


class PathForkService:
    """从被违反的硬假设生成 PathFork 列表。"""

    def generate(self, assumptions: KeyAssumptions) -> list[PathFork]:
        forks: list[PathFork] = []
        for assumption in assumptions.violated_hard:
            if assumption.status == AssumptionStatus.VIOLATED:
                forks.append(self._build_fork(assumption.description))
        return forks

    @staticmethod
    def _build_fork(assumption_description: str) -> PathFork:
        return PathFork(
            fork_id=str(uuid4()),
            trigger=PathForkTrigger.HARD_ASSUMPTION_VIOLATED,
            trigger_assumption=assumption_description,
            scenario_if_holds=(
                f"If '{assumption_description}' holds: "
                "investment thesis remains intact, continue monitoring."
            ),
            scenario_if_fails=(
                f"If '{assumption_description}' fails: "
                "re-evaluate commercialization path and capital requirements. "
                "Consider extended runway or pivot."
            ),
            recommended_action=(
                "Immediately verify assumption with primary data. "
                "Re-run sandbox with updated financials before next decision gate."
            ),
        )
