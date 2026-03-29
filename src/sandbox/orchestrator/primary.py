"""
Primary-market orchestrator — Orchestrated Deep Simulation.

与 SecondaryOrchestrator 的核心差异：
  - 多轮串行推进，Orchestrator 强控制（导演角色）
  - 三门控停止：预算上限 / 收敛 / 振荡检测
  - 硬假设失败 → 触发 PathFork
  - 6 个维度 Agent 顺序调度，而非并行 fan-out
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.sandbox.schemas.memory import Checkpoint, ReportRecord, SandboxEventRecord, SandboxSession
from src.sandbox.schemas.primary_market import (
    AssumptionLevel,
    AssumptionStatus,
    CompanyAnalysisReport,
    CompanyStage,
    DimensionAssessment,
    FinancialLens,
    FounderAnalysis,
    FounderArchetype,
    KeyAssumption,
    KeyAssumptions,
    MarketType,
    PathFork,
    PathForkTrigger,
    StageFit,
    UncertaintyDimension,
    UncertaintyMap,
    UncertaintyScore,
)
from src.sandbox.services.assumption_checker import AssumptionChecker
from src.sandbox.services.path_fork import PathForkService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 三门控停止阈值（MVP 默认值，后续可配置）
# ---------------------------------------------------------------------------
DEFAULT_MAX_ROUNDS = 3          # 预算上限：最多跑几轮
DEFAULT_CONVERGENCE_THRESHOLD = 0.85  # 收敛阈值：置信度均值达到此值视为收敛
DEFAULT_OSCILLATION_WINDOW = 2  # 振荡检测：连续 N 轮置信度变化 < 0.02 视为振荡


@dataclass
class PrimaryAgentOutput:
    """单个维度 Agent 的输出结构。"""

    dimension: UncertaintyDimension
    score: UncertaintyScore
    narrative: str
    key_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    error: str | None = None


@dataclass
class PrimaryRunResult:
    sandbox_id: UUID
    company_name: str
    report: CompanyAnalysisReport
    rounds_completed: int
    stop_reason: str


class PrimaryOrchestrator:
    """
    一级市场深推演 Orchestrator。

    执行流程（每轮）：
      1. 依次调用 6 个维度 Agent，收集输出
      2. 运行 AssumptionChecker，检查硬/软假设状态
      3. 如有硬假设违反 → PathForkService 生成分叉节点
      4. 三门控判断：收敛 / 振荡 / 预算上限
      5. 持久化 checkpoint + report
    """

    def __init__(
        self,
        assumption_checker: AssumptionChecker | None = None,
        path_fork_service: PathForkService | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
        oscillation_window: int = DEFAULT_OSCILLATION_WINDOW,
    ) -> None:
        self.assumption_checker = assumption_checker or AssumptionChecker()
        self.path_fork_service = path_fork_service or PathForkService()
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold
        self.oscillation_window = oscillation_window

    async def run(
        self,
        *,
        session: Session,
        company_name: str,
        sector: str | None = None,
        company_info: dict[str, Any],
        sandbox_id: UUID | None = None,
    ) -> PrimaryRunResult:
        sandbox = self._get_or_create_session(
            session=session,
            sandbox_id=sandbox_id,
            company_name=company_name,
            sector=sector,
        )

        confidence_history: list[float] = []
        path_forks: list[PathFork] = []
        stop_reason = "max_rounds_reached"

        for round_number in range(1, self.max_rounds + 1):
            logger.info("Primary sandbox %s — round %d/%d", sandbox.id, round_number, self.max_rounds)

            # Step 1: 调用 6 个维度 Agent
            agent_outputs = await self._run_dimension_agents(
                company_name=company_name,
                sector=sector,
                company_info=company_info,
                round_number=round_number,
            )
            self._persist_agent_outputs(session, sandbox.id, round_number, agent_outputs)

            # Step 2: 构建当前轮次的四模块结构
            uncertainty_map = self._build_uncertainty_map(agent_outputs, company_info)
            founder_analysis = self._build_founder_analysis(company_info)
            key_assumptions = self._build_key_assumptions(company_info)
            financial_lens = self._build_financial_lens(company_info)

            # Step 3: 假设验证，硬假设违反 → 生成 PathFork
            checked_assumptions = self.assumption_checker.check(key_assumptions, financial_lens)
            round_forks = self.path_fork_service.generate(checked_assumptions)
            path_forks.extend(round_forks)
            if round_forks:
                logger.info(
                    "Round %d: %d hard assumption(s) violated, %d PathFork(s) generated",
                    round_number, len(checked_assumptions.violated_hard), len(round_forks),
                )

            # Step 4: 三门控判断
            avg_confidence = self._average_confidence(agent_outputs)
            confidence_history.append(avg_confidence)

            stop_reason, should_stop = self._evaluate_stop_gates(
                confidence_history=confidence_history,
                round_number=round_number,
            )
            sandbox.current_round = round_number
            sandbox.total_rounds = round_number

            # 持久化 checkpoint
            self._persist_checkpoint(
                session=session,
                sandbox_id=sandbox.id,
                round_number=round_number,
                stop_reason=stop_reason,
                agent_outputs=agent_outputs,
                path_forks=round_forks,
                avg_confidence=avg_confidence,
            )

            if should_stop:
                logger.info("Primary sandbox %s stopping at round %d: %s", sandbox.id, round_number, stop_reason)
                break

        # 最终报告
        report = self._build_report(
            sandbox_id=sandbox.id,
            company_name=company_name,
            sector=sector,
            uncertainty_map=uncertainty_map,
            founder_analysis=founder_analysis,
            key_assumptions=checked_assumptions,
            financial_lens=financial_lens,
            path_forks=path_forks,
            avg_confidence=confidence_history[-1] if confidence_history else 0.0,
        )
        self._persist_report(session, sandbox.id, round_number, report)
        sandbox.status = "completed"

        return PrimaryRunResult(
            sandbox_id=sandbox.id,
            company_name=company_name,
            report=report,
            rounds_completed=round_number,
            stop_reason=stop_reason,
        )

    # ------------------------------------------------------------------
    # 内部：6 维度 Agent 调用（MVP：LLM stub，后续接真实 runner）
    # ------------------------------------------------------------------

    async def _run_dimension_agents(
        self,
        *,
        company_name: str,
        sector: str | None,
        company_info: dict[str, Any],
        round_number: int,
    ) -> list[PrimaryAgentOutput]:
        """
        依次调用 6 个维度 Agent。
        MVP 阶段从 company_info 解析输入，每个 Agent 输出 DimensionAssessment。
        后续替换为真实 LLM runner。
        """
        outputs: list[PrimaryAgentOutput] = []
        for dimension in UncertaintyDimension:
            output = await self._call_dimension_agent(
                dimension=dimension,
                company_name=company_name,
                sector=sector,
                company_info=company_info,
                round_number=round_number,
            )
            outputs.append(output)
        return outputs

    async def _call_dimension_agent(
        self,
        *,
        dimension: UncertaintyDimension,
        company_name: str,
        sector: str | None,
        company_info: dict[str, Any],
        round_number: int,
    ) -> PrimaryAgentOutput:
        """
        单个维度 Agent 调用。
        MVP：从 company_info 读取预填数据，后续替换为 LLM 调用。
        """
        dim_key = dimension.value
        dim_data = company_info.get("dimensions", {}).get(dim_key, {})

        score_raw = dim_data.get("score", "high")
        try:
            score = UncertaintyScore(score_raw)
        except ValueError:
            score = UncertaintyScore.HIGH

        return PrimaryAgentOutput(
            dimension=dimension,
            score=score,
            narrative=dim_data.get("narrative", f"{dim_key} assessment pending."),
            key_signals=dim_data.get("key_signals", []),
            confidence=float(dim_data.get("confidence", 0.5)),
        )

    # ------------------------------------------------------------------
    # 内部：构建四模块
    # ------------------------------------------------------------------

    def _build_uncertainty_map(
        self,
        agent_outputs: list[PrimaryAgentOutput],
        company_info: dict[str, Any],
    ) -> UncertaintyMap:
        market_type_raw = company_info.get("market_type", "new_market")
        try:
            market_type = MarketType(market_type_raw)
        except ValueError:
            market_type = MarketType.NEW_MARKET

        assessments: dict[UncertaintyDimension, DimensionAssessment] = {}
        for output in agent_outputs:
            assessments[output.dimension] = DimensionAssessment(
                score=output.score,
                narrative=output.narrative,
                key_signals=output.key_signals,
            )
        return UncertaintyMap(market_type=market_type, assessments=assessments)

    def _build_founder_analysis(self, company_info: dict[str, Any]) -> FounderAnalysis:
        f = company_info.get("founder", {})
        return FounderAnalysis(
            company_stage=CompanyStage(f.get("company_stage", "0_to_1")),
            archetype=FounderArchetype(f.get("archetype", "visionary")),
            founder_market_fit=UncertaintyScore(f.get("founder_market_fit", "medium")),
            execution_signal=f.get("execution_signal", ""),
            domain_depth=f.get("domain_depth", ""),
            team_building=UncertaintyScore(f.get("team_building", "medium")),
            self_awareness=UncertaintyScore(f.get("self_awareness", "medium")),
            stage_fit=StageFit(f.get("stage_fit", "matched")),
            stage_fit_narrative=f.get("stage_fit_narrative", ""),
            key_risks=f.get("key_risks", []),
        )

    def _build_key_assumptions(self, company_info: dict[str, Any]) -> KeyAssumptions:
        raw = company_info.get("assumptions", [])
        items: list[KeyAssumption] = []
        for a in raw:
            level = AssumptionLevel(a.get("level", "soft"))
            items.append(KeyAssumption(
                level=level,
                description=a.get("description", ""),
                status=AssumptionStatus(a.get("status", "unverified")),
                time_horizon_months=a.get("time_horizon_months"),
                triggers_path_fork=(level == AssumptionLevel.HARD),
            ))
        return KeyAssumptions(items=items)

    def _build_financial_lens(self, company_info: dict[str, Any]) -> FinancialLens:
        f = company_info.get("financials", {})
        return FinancialLens(
            arr=f.get("arr"),
            arr_growth_narrative=f.get("arr_growth_narrative"),
            nrr=f.get("nrr"),
            gross_margin=f.get("gross_margin"),
            monthly_burn=f.get("monthly_burn"),
            ltv_cac_ratio=f.get("ltv_cac_ratio"),
            current_valuation=f.get("current_valuation"),
            runway_months=f.get("runway_months"),
            valuation_narrative=f.get("valuation_narrative"),
        )

    def _build_report(
        self,
        *,
        sandbox_id: UUID,
        company_name: str,
        sector: str | None,
        uncertainty_map: UncertaintyMap,
        founder_analysis: FounderAnalysis,
        key_assumptions: KeyAssumptions,
        financial_lens: FinancialLens,
        path_forks: list[PathFork],
        avg_confidence: float,
    ) -> CompanyAnalysisReport:
        violated = key_assumptions.violated_hard
        if violated:
            verdict = f"HIGH RISK: {len(violated)} hard assumption(s) violated — PathFork triggered."
        elif avg_confidence >= self.convergence_threshold:
            verdict = "Converged with sufficient confidence across dimensions."
        else:
            verdict = "Partial analysis — further data required for full convergence."

        return CompanyAnalysisReport(
            sandbox_id=sandbox_id,
            company_name=company_name,
            sector=sector,
            generated_at=datetime.now(timezone.utc).isoformat(),
            uncertainty_map=uncertainty_map,
            founder_analysis=founder_analysis,
            key_assumptions=key_assumptions,
            financial_lens=financial_lens,
            path_forks=path_forks,
            overall_verdict=verdict,
            confidence=avg_confidence,
            round_id=str(uuid4()),
            trace_id=str(uuid4()),
        )

    # ------------------------------------------------------------------
    # 三门控停止判断
    # ------------------------------------------------------------------

    def _evaluate_stop_gates(
        self,
        *,
        confidence_history: list[float],
        round_number: int,
    ) -> tuple[str, bool]:
        """返回 (stop_reason, should_stop)。"""

        # 门控 1：预算上限
        if round_number >= self.max_rounds:
            return "max_rounds_reached", True

        # 门控 2：收敛
        if confidence_history[-1] >= self.convergence_threshold:
            return "converged", True

        # 门控 3：振荡检测（连续 N 轮置信度变化 < 0.02）
        if len(confidence_history) >= self.oscillation_window:
            recent = confidence_history[-self.oscillation_window:]
            deltas = [abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))]
            if all(d < 0.02 for d in deltas):
                return "oscillation_detected", True

        return "running", False

    @staticmethod
    def _average_confidence(outputs: list[PrimaryAgentOutput]) -> float:
        if not outputs:
            return 0.0
        return sum(o.confidence for o in outputs) / len(outputs)

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _get_or_create_session(
        self,
        *,
        session: Session,
        sandbox_id: UUID | None,
        company_name: str,
        sector: str | None,
    ) -> SandboxSession:
        if sandbox_id is not None:
            existing = session.get(SandboxSession, sandbox_id)
            if existing is not None:
                return existing
        sandbox = SandboxSession(
            ticker=company_name,
            market=sector or "primary_market",
            task_scope=f"primary market deep simulation for {company_name}",
            narrative_guide=None,
            round_timeout_ms=60000,
            status="running",
            current_round=0,
            total_rounds=0,
            agent_instance_ids=[d.value for d in UncertaintyDimension],
        )
        session.add(sandbox)
        session.flush()
        return sandbox

    def _persist_agent_outputs(
        self,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        outputs: list[PrimaryAgentOutput],
    ) -> None:
        for output in outputs:
            session.add(SandboxEventRecord(
                sandbox_id=sandbox_id,
                round=round_number,
                channel="CH-C",
                event_type="primary_dimension_assessment",
                source="agent",
                trace_id=uuid4(),
                agent_id=output.dimension.value,
                payload={
                    "dimension": output.dimension.value,
                    "score": output.score.value,
                    "narrative": output.narrative,
                    "key_signals": output.key_signals,
                    "confidence": output.confidence,
                    "error": output.error,
                },
                perspective_status=None,
                is_degraded=output.error is not None,
                degraded_reason=output.error,
            ))
        session.flush()

    def _persist_checkpoint(
        self,
        *,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        stop_reason: str,
        agent_outputs: list[PrimaryAgentOutput],
        path_forks: list[PathFork],
        avg_confidence: float,
    ) -> None:
        active = [o.dimension.value for o in agent_outputs if o.error is None]
        degraded = [o.dimension.value for o in agent_outputs if o.error is not None]
        session.add(Checkpoint(
            sandbox_id=sandbox_id,
            round=round_number,
            completion_status=stop_reason,
            active_agent_ids=active,
            reused_agent_ids=[],
            degraded_agent_ids=degraded,
            round_summary={
                "avg_confidence": avg_confidence,
                "path_fork_count": len(path_forks),
                "stop_reason": stop_reason,
                "dimensions_assessed": len(active),
            },
        ))
        session.flush()

    def _persist_report(
        self,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        report: CompanyAnalysisReport,
    ) -> None:
        session.add(ReportRecord(
            sandbox_id=sandbox_id,
            trace_id=uuid4(),
            round=round_number,
            report_type="company_analysis_report",
            data_quality="complete" if report.confidence >= self.convergence_threshold else "partial",
            perspective_synthesis={},
            key_tensions=[],
            tracking_signals=[report.overall_verdict],
            per_agent_detail={},
            assembly_notes={"report": report.model_dump(mode="json")},
        ))
        session.flush()
