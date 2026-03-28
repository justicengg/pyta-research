"""
PYTA Secondary-Market Report Schemas
====================================
二级市场并行视角模式的轮次结果与报告输出结构。
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .agents import AgentPerspective, ParticipantType, PerspectiveStatus
from .environment import EnvironmentType, TimeHorizon


class AgentActionSnapshot(BaseModel):
    """单个 Agent 的动作模拟快照。"""

    agent_type: ParticipantType
    action_bias: str
    confidence: float
    rationale_summary: str
    key_drivers: list[str] = Field(default_factory=list)
    affected_environment_types: list[EnvironmentType] = Field(default_factory=list)
    horizon: TimeHorizon = "short_term"


class PerAgentStatus(BaseModel):
    """单个 Agent 在当前轮的完成状态。"""

    agent_type: ParticipantType
    perspective_type: ParticipantType
    saturated: bool = True
    perspective_status: PerspectiveStatus
    summary: str


class DivergenceItem(BaseModel):
    """两个或多个参与者之间的关键分歧。"""

    agents: list[ParticipantType] = Field(min_length=2)
    dimension: str
    direction: str


class RoundComplete(BaseModel):
    """一轮完成后的内部结构化结果。"""

    sandbox_id: UUID
    ticker: str
    market: str
    rounds_completed: int
    stop_reason: str
    per_agent_status: list[PerAgentStatus]
    divergence_map: list[DivergenceItem] = Field(default_factory=list)
    data_quality: str


class TensionItem(BaseModel):
    """对外展示的关键张力。"""

    between: list[ParticipantType] = Field(min_length=2)
    description: str


class MarketReadingReport(BaseModel):
    """Layer 3 的市场解读报告。"""

    sandbox_id: UUID
    ticker: str
    generated_at: str
    perspective_synthesis: dict[ParticipantType, str]
    key_tensions: list[TensionItem] = Field(default_factory=list)
    tracking_signals: list[str] = Field(default_factory=list)
    data_quality: str
    perspective_detail: Optional[dict[ParticipantType, AgentPerspective]] = None
    action_detail: Optional[dict[ParticipantType, AgentActionSnapshot]] = None
