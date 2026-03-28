from __future__ import annotations

from uuid import uuid4

from src.sandbox.agents.runner import RunnerResult
from src.sandbox.schemas.agents import (
    AgentNarrative,
    AgentPerspective,
    MarketBias,
    ParticipantType,
    PerspectiveStatus,
)
from src.sandbox.schemas.reports import AgentActionSnapshot
from src.sandbox.services.interaction_resolver import resolve_interactions
from src.sandbox.services.synthesis import build_market_reading_report, build_round_complete


def _make_result(
    agent_type: ParticipantType,
    *,
    market_bias: MarketBias,
    action_bias: str,
    confidence: float,
) -> RunnerResult:
    perspective = AgentPerspective(
        agent_type=agent_type,
        perspective_type=agent_type,
        market_bias=market_bias,
        key_observations=[f"{agent_type.value} observation"],
        key_concerns=[f"{agent_type.value} concern"],
        analytical_focus=[f"{agent_type.value} focus"],
        confidence=confidence,
        perspective_status=PerspectiveStatus.LIVE,
    )
    action = AgentActionSnapshot(
        agent_type=agent_type,
        action_bias=action_bias,
        confidence=confidence,
        rationale_summary=f"{agent_type.value} rationale",
        key_drivers=[f"{agent_type.value} driver"],
        affected_environment_types=[],
        horizon="short_term",
    )
    narrative = AgentNarrative(
        agent_type=agent_type,
        content=f"{agent_type.value} narrative",
        trace_id=uuid4(),
    )
    return RunnerResult(agent_type=agent_type, perspective=perspective, action=action, narrative=narrative)


def test_resolve_interactions_builds_conflicts_and_reinforcements():
    results = [
        _make_result(
            ParticipantType.TRADITIONAL_INSTITUTION,
            market_bias=MarketBias.BULLISH,
            action_bias="accumulate",
            confidence=0.7,
        ),
        _make_result(
            ParticipantType.RETAIL,
            market_bias=MarketBias.BULLISH,
            action_bias="chase",
            confidence=0.82,
        ),
        _make_result(
            ParticipantType.OFFSHORE_CAPITAL,
            market_bias=MarketBias.BEARISH,
            action_bias="reduce",
            confidence=0.77,
        ),
    ]

    resolution = resolve_interactions(results)

    relation_types = {edge.relation_type for edge in resolution.interaction_edges}
    assert "reinforce" in relation_types
    assert "conflict" in relation_types
    assert resolution.market_force_summary.regime == "fragmented"
    assert resolution.market_force_summary.net_bias == "mixed"


def test_round_complete_and_report_include_interaction_resolution():
    results = [
        _make_result(
            ParticipantType.QUANT_INSTITUTION,
            market_bias=MarketBias.BULLISH,
            action_bias="accumulate",
            confidence=0.73,
        ),
        _make_result(
            ParticipantType.SHORT_TERM_CAPITAL,
            market_bias=MarketBias.BULLISH,
            action_bias="chase",
            confidence=0.8,
        ),
        _make_result(
            ParticipantType.OFFSHORE_CAPITAL,
            market_bias=MarketBias.NEUTRAL,
            action_bias="watch",
            confidence=0.51,
        ),
    ]

    round_complete = build_round_complete(
        sandbox_id=uuid4(),
        ticker="0700.HK",
        market="HK",
        round_number=1,
        stop_reason="saturated",
        results=results,
    )
    report = build_market_reading_report(round_complete, results)

    assert round_complete.interaction_resolution is not None
    assert report.interaction_resolution is not None
    assert report.interaction_resolution.market_force_summary.regime == "expansion"
    assert report.interaction_resolution.market_force_summary.net_bias == "bullish"
    assert report.interaction_resolution.market_force_summary.dominant_agents[0] == ParticipantType.SHORT_TERM_CAPITAL
