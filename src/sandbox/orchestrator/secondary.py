"""Secondary-market orchestrator for parallel perspective simulation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sandbox.agents.runner import RunnerResult, SecondaryAgentRunner
from src.sandbox.environment_pipeline import build_environment_state

logger = logging.getLogger(__name__)
from src.sandbox.schemas.agents import AgentNarrative, AgentPerspective, MarketBias, ParticipantType, PerspectiveStatus
from src.sandbox.schemas.environment import EnvironmentState
from src.sandbox.schemas.memory import AgentSnapshot, Checkpoint, ReportRecord, SandboxEventRecord, SandboxSession
from src.sandbox.schemas.reports import AgentActionSnapshot, MarketReadingReport, RoundComplete
from src.sandbox.services.synthesis import build_assembly_notes, build_market_reading_report, build_round_complete


@dataclass
class SecondaryRunResult:
    sandbox_id: UUID
    environment_state: EnvironmentState
    round_complete: RoundComplete
    report: MarketReadingReport


class SecondaryOrchestrator:
    def __init__(self, runner: SecondaryAgentRunner | None = None) -> None:
        self.runner = runner or SecondaryAgentRunner()

    async def run(
        self,
        *,
        session: Session,
        ticker: str,
        market: str,
        events: list[dict[str, Any]],
        environment_state: EnvironmentState | None = None,
        round_timeout_ms: int = 30000,
        narrative_guide: str | None = None,
        sandbox_id: UUID | None = None,
        round_number: int = 1,
    ) -> SecondaryRunResult:
        sandbox = self._get_or_create_session(
            session=session,
            sandbox_id=sandbox_id,
            ticker=ticker,
            market=market,
            round_timeout_ms=round_timeout_ms,
            narrative_guide=narrative_guide,
        )
        event_rows = self._persist_input_events(session, sandbox.id, round_number, events)
        environment_state = environment_state or build_environment_state(
            ticker=ticker,
            market=market,
            events=event_rows,
        )
        environment_state.sandbox_id = sandbox.id
        self._persist_environment_state(session, sandbox.id, round_number, environment_state)

        # ── Fetch real market data (yfinance, with DB cache) and inject into agent prompts ────
        market_data: dict[str, Any] | None = None
        try:
            from src.data.enrichers.yfinance_enricher import fetch_canonical_cached
            canonical = await asyncio.get_event_loop().run_in_executor(
                None, fetch_canonical_cached, ticker, market, session
            )
            market_data = canonical.to_agent_context()
            logger.info("Market data fetched for %s: price=%s", ticker, market_data.get("price", {}).get("current"))
        except Exception as exc:
            logger.warning("Failed to fetch market data for %s: %s — agents will run without it", ticker, exc)

        runner_results = await self.runner.run_all(
            ticker=ticker,
            market=market,
            round_number=round_number,
            events=event_rows,
            narrative_guide=narrative_guide,
            timeout_ms=round_timeout_ms,
            market_data=market_data,
            environment_state=environment_state.model_dump(mode="json"),
        )
        resolved_results = [self._resolve_result(session, sandbox.id, round_number, result) for result in runner_results]
        stop_reason = self._determine_stop_reason(resolved_results)
        self._persist_agent_outputs(session, sandbox.id, round_number, resolved_results)
        round_complete = build_round_complete(
            sandbox_id=sandbox.id,
            ticker=ticker,
            market=market,
            round_number=round_number,
            stop_reason=stop_reason,
            results=resolved_results,
        )
        report = build_market_reading_report(round_complete, resolved_results)
        report_record = self._persist_report_record(session, sandbox.id, round_number, round_complete, report, resolved_results)
        self._persist_checkpoint(session, sandbox.id, round_number, round_complete, report_record.id, resolved_results)
        sandbox.status = round_complete.data_quality
        sandbox.current_round = round_number
        sandbox.total_rounds = round_number
        return SecondaryRunResult(
            sandbox_id=sandbox.id,
            environment_state=environment_state,
            round_complete=round_complete,
            report=report,
        )

    def _get_or_create_session(
        self,
        *,
        session: Session,
        sandbox_id: UUID | None,
        ticker: str,
        market: str,
        round_timeout_ms: int,
        narrative_guide: str | None,
    ) -> SandboxSession:
        if sandbox_id is not None:
            existing = session.get(SandboxSession, sandbox_id)
            if existing is not None:
                return existing
        sandbox = SandboxSession(
            ticker=ticker,
            market=market,
            task_scope=f"secondary market simulation for {ticker}",
            narrative_guide=narrative_guide,
            round_timeout_ms=round_timeout_ms,
            status="running",
            current_round=0,
            total_rounds=0,
            agent_instance_ids=[agent.value for agent in ParticipantType],
        )
        session.add(sandbox)
        session.flush()
        return sandbox

    def _persist_input_events(self, session: Session, sandbox_id: UUID, round_number: int, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        persisted: list[dict[str, Any]] = []
        for event in events:
            trace_id = uuid4()
            row = SandboxEventRecord(
                sandbox_id=sandbox_id,
                round=round_number,
                channel="CH-A",
                event_type="input_event",
                source=event.get("source", "user"),
                trace_id=trace_id,
                agent_id=None,
                payload=event,
                perspective_status=None,
                is_degraded=False,
            )
            session.add(row)
            persisted.append(event)
        session.flush()
        return persisted

    def _persist_environment_state(
        self,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        environment_state: EnvironmentState,
    ) -> None:
        session.add(
            SandboxEventRecord(
                sandbox_id=sandbox_id,
                round=round_number,
                channel="CH-A",
                event_type="environment_state",
                source="system",
                trace_id=uuid4(),
                agent_id=None,
                payload=environment_state.model_dump(mode="json"),
                perspective_status=None,
                is_degraded=False,
            )
        )
        session.flush()

    def _resolve_result(self, session: Session, sandbox_id: UUID, round_number: int, result: RunnerResult) -> RunnerResult:
        if result.perspective is not None and result.narrative is not None:
            if result.action is None:
                result.action = self._build_fallback_action_snapshot(result.agent_type, result.perspective)
            return result

        previous = self._get_latest_snapshot(session, sandbox_id, result.agent_type.value, round_number)
        if previous is not None:
            perspective = AgentPerspective(
                agent_type=result.agent_type,
                perspective_type=result.agent_type,
                market_bias=MarketBias.NEUTRAL,
                key_observations=list(previous.key_observations),
                key_concerns=list(previous.key_concerns),
                analytical_focus=list(previous.analytical_focus),
                confidence=previous.confidence,
                perspective_status=PerspectiveStatus.REUSED_LAST_ROUND,
            )
            narrative = AgentNarrative(
                agent_type=result.agent_type,
                content=f"Reused previous-round perspective for {result.agent_type.value}.",
                trace_id=previous.source_trace_id,
            )
            result.perspective = perspective
            result.action = self._build_fallback_action_snapshot(result.agent_type, perspective)
            result.narrative = narrative
            result.timed_out = False
            result.error = None
            return result

        result.perspective = AgentPerspective(
            agent_type=result.agent_type,
            perspective_type=result.agent_type,
            market_bias=MarketBias.NEUTRAL,
            key_observations=[],
            key_concerns=[],
            analytical_focus=[],
            confidence=0.0,
            perspective_status=PerspectiveStatus.DEGRADED,
        )
        result.narrative = AgentNarrative(
            agent_type=result.agent_type,
            content=f"Degraded default perspective injected for {result.agent_type.value}.",
            trace_id=uuid4(),
        )
        result.action = self._build_fallback_action_snapshot(result.agent_type, result.perspective)
        return result

    def _build_fallback_action_snapshot(
        self,
        agent_type: ParticipantType,
        perspective: AgentPerspective,
    ) -> AgentActionSnapshot:
        builder = getattr(self.runner, "_build_default_action_snapshot", None)
        if callable(builder):
            return builder(agent_type, perspective, None)

        if perspective.market_bias == MarketBias.BULLISH:
            action_bias = "chase" if agent_type == ParticipantType.SHORT_TERM_CAPITAL else "accumulate"
        elif perspective.market_bias == MarketBias.BEARISH:
            action_bias = "exit" if agent_type == ParticipantType.SHORT_TERM_CAPITAL else "reduce"
        elif perspective.market_bias == MarketBias.MIXED:
            action_bias = "hedge"
        else:
            action_bias = "watch"

        if agent_type == ParticipantType.SHORT_TERM_CAPITAL:
            horizon = "intraday"
        elif agent_type == ParticipantType.TRADITIONAL_INSTITUTION:
            horizon = "long_term"
        elif agent_type == ParticipantType.OFFSHORE_CAPITAL:
            horizon = "mid_term"
        else:
            horizon = "short_term"

        return AgentActionSnapshot(
            agent_type=agent_type,
            action_bias=action_bias,
            confidence=perspective.confidence,
            rationale_summary="；".join((perspective.key_observations + perspective.analytical_focus)[:2])
            or f"{agent_type.value} action captured.",
            key_drivers=(perspective.analytical_focus or perspective.key_concerns or perspective.key_observations)[:3],
            affected_environment_types=[],
            horizon=horizon,
        )

    def _get_latest_snapshot(self, session: Session, sandbox_id: UUID, agent_id: str, round_number: int) -> AgentSnapshot | None:
        stmt = (
            select(AgentSnapshot)
            .where(
                AgentSnapshot.sandbox_id == sandbox_id,
                AgentSnapshot.agent_id == agent_id,
                AgentSnapshot.round < round_number,
            )
            .order_by(AgentSnapshot.round.desc())
            .limit(1)
        )
        return session.scalar(stmt)

    def _persist_agent_outputs(self, session: Session, sandbox_id: UUID, round_number: int, results: list[RunnerResult]) -> None:
        for result in results:
            trace_id = result.narrative.trace_id if result.narrative and result.narrative.trace_id else uuid4()
            session.add(
                SandboxEventRecord(
                    sandbox_id=sandbox_id,
                    round=round_number,
                    channel="CH-C",
                    event_type="agent_perspective",
                    source="agent",
                    trace_id=trace_id,
                    agent_id=result.agent_type.value,
                    payload=result.perspective.model_dump(mode="json"),
                    perspective_status=result.perspective.perspective_status.value,
                    is_degraded=result.perspective.perspective_status == PerspectiveStatus.DEGRADED,
                    degraded_reason=result.error,
                )
            )
            session.add(
                SandboxEventRecord(
                    sandbox_id=sandbox_id,
                    round=round_number,
                    channel="CH-C",
                    event_type="agent_narrative",
                    source="agent",
                    trace_id=trace_id,
                    agent_id=result.agent_type.value,
                    payload=result.narrative.model_dump(mode="json"),
                    perspective_status=result.perspective.perspective_status.value,
                    is_degraded=result.perspective.perspective_status == PerspectiveStatus.DEGRADED,
                    degraded_reason=result.error,
                )
            )
            session.add(
                AgentSnapshot(
                    sandbox_id=sandbox_id,
                    round=round_number,
                    agent_id=result.agent_type.value,
                    perspective_type=result.perspective.perspective_type.value,
                    perspective_status=result.perspective.perspective_status.value,
                    key_observations=result.perspective.key_observations,
                    key_concerns=result.perspective.key_concerns,
                    analytical_focus=result.perspective.analytical_focus,
                    confidence=result.perspective.confidence,
                    source_trace_id=trace_id,
                )
            )
        session.flush()

    def _persist_report_record(
        self,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        round_complete: RoundComplete,
        report: MarketReadingReport,
        results: list[RunnerResult],
    ) -> ReportRecord:
        record = ReportRecord(
            sandbox_id=sandbox_id,
            trace_id=uuid4(),
            round=round_number,
            report_type="market_reading_report",
            data_quality=report.data_quality,
            perspective_synthesis={k.value: v for k, v in report.perspective_synthesis.items()},
            key_tensions=[item.model_dump(mode="json") for item in report.key_tensions],
            tracking_signals=report.tracking_signals,
            per_agent_detail={
                agent.value: perspective.model_dump(mode="json")
                for agent, perspective in (report.perspective_detail or {}).items()
            },
            assembly_notes=build_assembly_notes(results),
        )
        session.add(record)
        session.flush()
        return record

    def _persist_checkpoint(
        self,
        session: Session,
        sandbox_id: UUID,
        round_number: int,
        round_complete: RoundComplete,
        report_id: UUID,
        results: list[RunnerResult],
    ) -> None:
        active = [r.agent_type.value for r in results if r.perspective and r.perspective.perspective_status == PerspectiveStatus.LIVE]
        reused = [r.agent_type.value for r in results if r.perspective and r.perspective.perspective_status == PerspectiveStatus.REUSED_LAST_ROUND]
        degraded = [r.agent_type.value for r in results if r.perspective and r.perspective.perspective_status == PerspectiveStatus.DEGRADED]
        session.add(
            Checkpoint(
                sandbox_id=sandbox_id,
                round=round_number,
                completion_status=round_complete.data_quality,
                active_agent_ids=active,
                reused_agent_ids=reused,
                degraded_agent_ids=degraded,
                round_summary={
                    "divergence_count": len(round_complete.divergence_map),
                    "quality": round_complete.data_quality,
                    "generated_report_id": str(report_id),
                },
            )
        )
        session.flush()

    def _determine_stop_reason(self, results: list[RunnerResult]) -> str:
        statuses = [r.perspective.perspective_status for r in results if r.perspective is not None]
        if statuses and all(status == PerspectiveStatus.LIVE for status in statuses):
            return "all_perspectives_received"
        if any(status == PerspectiveStatus.DEGRADED for status in statuses):
            return "degraded"
        return "partial"
