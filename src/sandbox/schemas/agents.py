"""
PYTA Secondary-Market Agent Schemas
===================================
二级市场市场参与者的统一输出结构。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ParticipantType(str, Enum):
    """二级市场第一版的 5 个市场参与者。"""

    TRADITIONAL_INSTITUTION = "traditional_institution"
    QUANT_INSTITUTION = "quant_institution"
    RETAIL = "retail"
    OFFSHORE_CAPITAL = "offshore_capital"
    SHORT_TERM_CAPITAL = "short_term_capital"


class PerspectiveStatus(str, Enum):
    """视角状态。"""

    LIVE = "live"
    REUSED_LAST_ROUND = "reused_last_round"
    DEGRADED = "degraded"


class MarketBias(str, Enum):
    """当前视角的方向偏向。"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AgentPerspective(BaseModel):
    """
    Track 1: Agent 的结构化视角输出。

    注意：
    - 不包含 buy/sell/hold 等动作语义
    - 不新增 summary 字段，摘要由 key_observations + analytical_focus 规则生成
    """

    agent_type: ParticipantType
    perspective_type: ParticipantType
    market_bias: MarketBias = MarketBias.NEUTRAL
    key_observations: list[str] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list)
    analytical_focus: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.0)
    perspective_status: PerspectiveStatus = PerspectiveStatus.LIVE


class AgentNarrative(BaseModel):
    """Track 2: Agent 的自然语言叙事输出。"""

    agent_type: ParticipantType
    content: str
    trace_id: Optional[UUID] = None
    mentions: list[ParticipantType] = Field(default_factory=list)
