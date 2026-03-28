"""Rule-based interaction resolution for secondary-market sandbox actions."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable

from src.sandbox.agents.runner import RunnerResult
from src.sandbox.schemas.agents import ParticipantType
from src.sandbox.schemas.reports import (
    AgentActionSnapshot,
    ConflictItem,
    InteractionEdge,
    InteractionResolution,
    MarketForceSummary,
    ReinforcementItem,
)

_BULLISH_ACTIONS = {"accumulate", "chase"}
_BEARISH_ACTIONS = {"reduce", "exit"}
_DEFENSIVE_ACTIONS = {"hedge"}
_PASSIVE_ACTIONS = {"hold", "watch"}
_ACTIVE_ACTIONS = _BULLISH_ACTIONS | _BEARISH_ACTIONS | _DEFENSIVE_ACTIONS


def resolve_interactions(results: Iterable[RunnerResult]) -> InteractionResolution:
    actions = [result.action for result in results if result.action is not None]
    edges: list[InteractionEdge] = []
    conflicts: list[ConflictItem] = []
    reinforcements: list[ReinforcementItem] = []

    for left, right in combinations(actions, 2):
        relation_type = _classify_relation(left.action_bias, right.action_bias)
        if relation_type is None:
            continue

        strength = round((left.confidence + right.confidence) / 2, 3)
        description = _describe_relation(left, right, relation_type)
        edges.append(
            InteractionEdge(
                source_agent=left.agent_type,
                target_agent=right.agent_type,
                relation_type=relation_type,
                strength=strength,
                description=description,
            )
        )

        if relation_type == "reinforce":
            reinforcements.append(
                ReinforcementItem(
                    between=[left.agent_type, right.agent_type],
                    strength=strength,
                    description=description,
                )
            )
        elif relation_type in {"conflict", "offset"}:
            conflicts.append(
                ConflictItem(
                    between=[left.agent_type, right.agent_type],
                    strength=strength,
                    description=description,
                )
            )

    return InteractionResolution(
        interaction_edges=edges,
        conflict_map=conflicts,
        reinforcement_map=reinforcements,
        market_force_summary=_summarize_market_forces(actions),
    )


def _classify_relation(left_bias: str, right_bias: str) -> str | None:
    if left_bias in _BULLISH_ACTIONS and right_bias in _BULLISH_ACTIONS:
        return "reinforce"
    if left_bias in _BEARISH_ACTIONS and right_bias in _BEARISH_ACTIONS:
        return "reinforce"
    if left_bias == right_bias and left_bias in _ACTIVE_ACTIONS:
        return "reinforce"
    if left_bias in _BULLISH_ACTIONS and right_bias in _BEARISH_ACTIONS:
        return "conflict"
    if left_bias in _BEARISH_ACTIONS and right_bias in _BULLISH_ACTIONS:
        return "conflict"
    if left_bias in _DEFENSIVE_ACTIONS and right_bias in _ACTIVE_ACTIONS:
        return "offset"
    if left_bias in _ACTIVE_ACTIONS and right_bias in _DEFENSIVE_ACTIONS:
        return "offset"
    if left_bias in _ACTIVE_ACTIONS and right_bias in _PASSIVE_ACTIONS:
        return "lead_follow"
    if left_bias in _PASSIVE_ACTIONS and right_bias in _ACTIVE_ACTIONS:
        return "lead_follow"
    return None


def _describe_relation(left: AgentActionSnapshot, right: AgentActionSnapshot, relation_type: str) -> str:
    if relation_type == "reinforce":
        return f"{left.agent_type.value} 与 {right.agent_type.value} 在 {left.action_bias} 上形成同向强化。"
    if relation_type == "conflict":
        return f"{left.agent_type.value} 的 {left.action_bias} 与 {right.agent_type.value} 的 {right.action_bias} 形成方向冲突。"
    if relation_type == "offset":
        return f"{left.agent_type.value} 与 {right.agent_type.value} 形成防御性对冲。"
    return f"{left.agent_type.value} 的动作正在影响 {right.agent_type.value} 的观察与跟随。"


def _summarize_market_forces(actions: list[AgentActionSnapshot]) -> MarketForceSummary:
    bullish_pressure = 0.0
    bearish_pressure = 0.0
    active_actions: list[AgentActionSnapshot] = []

    for action in actions:
        weight = _action_weight(action.action_bias) * action.confidence
        if weight > 0:
            bullish_pressure += weight
        elif weight < 0:
            bearish_pressure += abs(weight)
        if action.action_bias in _ACTIVE_ACTIONS:
            active_actions.append(action)

    if bullish_pressure > 0 and bearish_pressure > 0 and abs(bullish_pressure - bearish_pressure) < 1.0:
        regime = "fragmented"
        net_bias = "mixed"
    elif bullish_pressure >= bearish_pressure + 0.75:
        regime = "expansion"
        net_bias = "bullish"
    elif bearish_pressure >= bullish_pressure + 0.75:
        regime = "contraction"
        net_bias = "bearish"
    elif bullish_pressure > 0 and bearish_pressure > 0:
        regime = "fragmented"
        net_bias = "mixed"
    else:
        regime = "balanced"
        net_bias = "neutral"

    dominant_agents = [
        action.agent_type
        for action in sorted(active_actions or actions, key=lambda item: item.confidence, reverse=True)[:2]
    ]
    summary = _build_summary_line(regime, net_bias, dominant_agents)
    return MarketForceSummary(
        regime=regime,
        net_bias=net_bias,
        dominant_agents=dominant_agents,
        bullish_pressure=round(bullish_pressure, 3),
        bearish_pressure=round(bearish_pressure, 3),
        summary=summary,
    )


def _action_weight(action_bias: str) -> float:
    if action_bias == "chase":
        return 1.2
    if action_bias == "accumulate":
        return 1.0
    if action_bias == "reduce":
        return -1.0
    if action_bias == "exit":
        return -1.2
    if action_bias == "hedge":
        return -0.45
    return 0.0


def _build_summary_line(regime: str, net_bias: str, dominant_agents: list[ParticipantType]) -> str:
    if dominant_agents:
        driver_text = "、".join(agent.value for agent in dominant_agents)
    else:
        driver_text = "no_clear_leader"
    return f"market regime={regime}; net_bias={net_bias}; dominant_agents={driver_text}"
