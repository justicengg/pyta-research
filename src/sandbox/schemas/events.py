"""
PYTA Sandbox Event Schema Definitions
=====================================
二级市场并行视角模式的统一事件总线 Schema。

设计原则：
1. 保留统一事件底座，服务 Layer 1 输入、Layer 2 推演、Layer 3 输出。
2. trace_id 关联同轮结构化视角（AgentPerspective）与叙事输出（AgentNarrative）。
3. 当前事件类型围绕 secondary-market MVP 收敛，不再承载 buy/sell/hold 动作语义。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .agents import AgentNarrative, AgentPerspective, PerspectiveStatus


class Channel(str, Enum):
    """事件来源通道。"""

    DATA_FEED = "CH-A"
    USER_COMMAND = "CH-B"
    AGENT_CROSS = "CH-C"


class EventType(str, Enum):
    """当前 secondary-market MVP 需要的事件类型。"""

    SANDBOX_INIT = "sandbox_init"
    ROUND_TICK = "round_tick"
    ROUND_COMPLETE = "round_complete"
    INPUT_EVENT = "input_event"
    AGENT_PERSPECTIVE = "agent_perspective"
    AGENT_NARRATIVE = "agent_narrative"
    SYSTEM_EVENT = "system_event"
    SANDBOX_RESULT = "sandbox_result"


class SandboxEvent(BaseModel):
    """
    所有沙盘事件的统一基类。

    - sandbox_id: 一次完整推演会话
    - round: 当前轮次（0 = 初始化阶段）
    - trace_id: 同轮结构化输出与叙事输出的关联链
    """

    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    round: int = Field(ge=0)
    channel: Channel
    event_type: EventType
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[UUID] = None


class SandboxInitPayload(BaseModel):
    """一次 secondary-market sandbox 启动所需的最小配置。"""

    ticker: str
    market: str
    task_scope: str
    round_timeout_ms: int = 30000
    active_agents: list[str]
    narrative_guide: Optional[str] = None


class SandboxInit(SandboxEvent):
    event_type: EventType = EventType.SANDBOX_INIT
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    round: int = 0
    payload: SandboxInitPayload


class RoundTickPayload(BaseModel):
    """新一轮推演启动。"""

    ticker: str
    market: str
    active_agents: list[str]
    round_timeout_ms: int
    input_event_count: int = 0


class RoundTick(SandboxEvent):
    event_type: EventType = EventType.ROUND_TICK
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: RoundTickPayload


class RoundCompletePayload(BaseModel):
    """一轮推演的轻量完成摘要。"""

    completion_status: str
    data_quality: str
    active_agent_ids: list[str] = []
    reused_agent_ids: list[str] = []
    degraded_agent_ids: list[str] = []
    divergence_count: int = 0
    generated_report_id: Optional[UUID] = None


class RoundComplete(SandboxEvent):
    event_type: EventType = EventType.ROUND_COMPLETE
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: RoundCompletePayload


class InputEventPayload(BaseModel):
    """Layer 1 或调用方注入的结构化输入事件。"""

    event_id: str
    event_type: str
    content: str
    source: str
    timestamp: datetime
    symbol: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InputEvent(SandboxEvent):
    event_type: EventType = EventType.INPUT_EVENT
    channel: Channel = Channel.DATA_FEED
    payload: InputEventPayload


class AgentPerspectiveEvent(SandboxEvent):
    """Track 1: 结构化市场参与者视角。"""

    event_type: EventType = EventType.AGENT_PERSPECTIVE
    channel: Channel = Channel.AGENT_CROSS
    payload: AgentPerspective


class AgentNarrativeEvent(SandboxEvent):
    """Track 2: Agent 自然语言叙事。"""

    event_type: EventType = EventType.AGENT_NARRATIVE
    channel: Channel = Channel.AGENT_CROSS
    payload: AgentNarrative


class SystemEventPayload(BaseModel):
    """系统/调度层事件。"""

    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    perspective_status: Optional[PerspectiveStatus] = None


class SystemEvent(SandboxEvent):
    event_type: EventType = EventType.SYSTEM_EVENT
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: SystemEventPayload


class SandboxResultPayload(BaseModel):
    """提交给 Layer 3 的结构化结果引用。"""

    report_id: UUID
    data_quality: str
    summary: str


class SandboxResult(SandboxEvent):
    event_type: EventType = EventType.SANDBOX_RESULT
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: SandboxResultPayload
