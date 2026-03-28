"""Rule-based Layer 3 assembly for secondary-market MVP."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from typing import Iterable
from uuid import UUID

from src.sandbox.agents.runner import RunnerResult
from src.sandbox.schemas.agents import AgentPerspective, MarketBias, ParticipantType
from src.sandbox.schemas.reports import (
    AgentActionSnapshot,
    DivergenceItem,
    MarketReadingReport,
    PerAgentStatus,
    RoundComplete,
    TensionItem,
)


def build_summary_from_perspective(perspective: AgentPerspective) -> str:
    observations = perspective.key_observations[:1]
    focus = perspective.analytical_focus[:1]
    parts = observations + focus
    return "；".join(parts) if parts else f"{perspective.agent_type.value} 当前暂无明确观察。"


def build_round_complete(
    *,
    sandbox_id: UUID,
    ticker: str,
    market: str,
    round_number: int,
    stop_reason: str,
    results: Iterable[RunnerResult],
) -> RoundComplete:
    per_agent_status: list[PerAgentStatus] = []
    perspectives: list[AgentPerspective] = []
    for result in results:
        if result.perspective is None:
            continue
        perspectives.append(result.perspective)
        per_agent_status.append(
            PerAgentStatus(
                agent_type=result.agent_type,
                perspective_type=result.perspective.perspective_type,
                saturated=result.perspective.perspective_status == "live",
                perspective_status=result.perspective.perspective_status,
                summary=build_summary_from_perspective(result.perspective),
            )
        )

    divergence_map = _build_divergence_map(perspectives)
    data_quality = _derive_data_quality(results)
    return RoundComplete(
        sandbox_id=sandbox_id,
        ticker=ticker,
        market=market,
        rounds_completed=round_number,
        stop_reason=stop_reason,
        per_agent_status=per_agent_status,
        divergence_map=divergence_map,
        data_quality=data_quality,
    )


def build_market_reading_report(round_complete: RoundComplete, results: Iterable[RunnerResult]) -> MarketReadingReport:
    detail: dict[ParticipantType, AgentPerspective] = {}
    actions: dict[ParticipantType, AgentActionSnapshot] = {}
    synthesis: dict[ParticipantType, str] = {}
    tensions: list[TensionItem] = []
    tracking_signals: list[str] = []

    for result in results:
        if result.perspective is None:
            continue
        detail[result.agent_type] = result.perspective
        if result.action is not None:
            actions[result.agent_type] = result.action
        synthesis[result.agent_type] = build_summary_from_perspective(result.perspective)
        tracking_signals.extend(result.perspective.key_concerns[:1])

    for item in round_complete.divergence_map:
        tensions.append(TensionItem(between=item.agents, description=item.direction))

    return MarketReadingReport(
        sandbox_id=round_complete.sandbox_id,
        ticker=round_complete.ticker,
        generated_at=datetime.now(timezone.utc).isoformat(),
        perspective_synthesis=synthesis,
        key_tensions=tensions,
        tracking_signals=_unique_keep_order(tracking_signals)[:3],
        data_quality=round_complete.data_quality,
        perspective_detail=detail,
        action_detail=actions,
    )


def build_assembly_notes(results: Iterable[RunnerResult]) -> dict:
    notes: dict[str, dict] = {}
    for result in results:
        status = result.perspective.perspective_status.value if result.perspective else "missing"
        notes[result.agent_type.value] = {
            "perspective_status": status,
            "used_stub": result.used_stub,
            "timed_out": result.timed_out,
            "error": result.error,
            "action_snapshot": result.action.model_dump(mode="json") if result.action is not None else None,
        }
    return notes


def _build_divergence_map(perspectives: list[AgentPerspective]) -> list[DivergenceItem]:
    items: list[DivergenceItem] = []
    for left, right in combinations(perspectives, 2):
        if left.market_bias == right.market_bias:
            continue
        items.append(
            DivergenceItem(
                agents=[left.agent_type, right.agent_type],
                dimension="market_bias",
                direction=f"{left.agent_type.value}={left.market_bias.value}, {right.agent_type.value}={right.market_bias.value}",
            )
        )
    return items


def _derive_data_quality(results: Iterable[RunnerResult]) -> str:
    statuses = [result.perspective.perspective_status.value for result in results if result.perspective is not None]
    if statuses and all(status == "live" for status in statuses):
        return "complete"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "partial"


def _unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
