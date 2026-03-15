"""
PYTA Sandbox Event Schema Definitions
=====================================
沙盘推演系统的完整事件 Schema 设计

设计原则：
1. 所有事件共享 SandboxEvent base，确保统一的路由、存储和追溯
2. trace_id 关联 Track 1（结构化）和 Track 2（叙事），一次 Agent 行动产出的两条事件共享同一个 trace_id
3. channel 区分事件来源（CH-A 数据层 / CH-B 用户指令 / CH-C Agent 交叉通信）
4. round 字段支持回合制同步：Orchestrator 按 round 收集和聚合
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class Channel(str, Enum):
    """事件来源通道"""
    DATA_FEED = "CH-A"       # Layer 1 数据采集层输入
    USER_COMMAND = "CH-B"    # 用户推演指令
    AGENT_CROSS = "CH-C"    # Agent 交叉通信


class EventType(str, Enum):
    """事件类型枚举"""
    # 基础设施层
    SANDBOX_INIT = "sandbox_init"
    ROUND_TICK = "round_tick"
    ROUND_COMPLETE = "round_complete"

    # 数据层 (CH-A)
    MARKET_DATA_FEED = "market_data_feed"
    NEWS_EVENT = "news_event"

    # 用户指令 (CH-B)
    USER_VAR_INJECTION = "user_var_injection"
    USER_AGENT_CONFIG = "user_agent_config"

    # Agent 行为 (CH-C / Track 1)
    AGENT_ACTION = "agent_action"
    AGENT_SIGNAL = "agent_signal"

    # Agent 叙事 (CH-C / Track 2)
    AGENT_NARRATIVE = "agent_narrative"

    # 输出层
    PATH_FORK = "path_fork"
    SANDBOX_RESULT = "sandbox_result"


class ActionVerb(str, Enum):
    """Agent 交易动作"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"              # 观望，不做交易
    INCREASE_POSITION = "increase_position"
    DECREASE_POSITION = "decrease_position"
    SHORT = "short"
    COVER_SHORT = "cover_short"


class SignalType(str, Enum):
    """Agent 信号类型（非交易动作）"""
    WARNING = "warning"          # 风险预警
    SENTIMENT_SHIFT = "sentiment_shift"  # 情绪转变信号
    POLICY_CHANGE = "policy_change"      # 政策变化信号
    SUPPLY_DISRUPTION = "supply_disruption"  # 供应链扰动
    MOMENTUM_BREAK = "momentum_break"    # 动量突破


class Sentiment(str, Enum):
    """情绪倾向"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    CONFLICTED = "conflicted"    # 多空分歧


# ============================================================
# Base Event
# ============================================================

class SandboxEvent(BaseModel):
    """
    所有沙盘事件的基类。

    设计要点：
    - id: 每条事件的唯一标识
    - sandbox_id: 关联到哪一次沙盘推演会话
    - round: 当前推演轮次（0 = 初始化阶段）
    - channel: 事件来源通道
    - event_type: 事件类型
    - source: 事件发起者（agent_id / "system" / "user"）
    - timestamp: 事件创建时间
    - trace_id: 关联同一次 Agent 行动产出的 Track 1 和 Track 2 事件
    """
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    round: int = Field(ge=0)
    channel: Channel
    event_type: EventType
    source: str                # agent_id | "system" | "user"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[UUID] = None  # 关联 Track 1 + Track 2


# ============================================================
# 基础设施层事件
# ============================================================

class SandboxInitPayload(BaseModel):
    """沙盘初始化配置"""
    task_scope: str             # 推演任务描述（自然语言）
    target_symbols: list[str]   # 目标标的列表
    time_horizon: str           # 推演时间跨度（如 "3_months", "1_year"）
    max_rounds: int = 20       # 最大推演轮次
    narrative_guide: str        # 推演叙事引导方向
    agent_instances: list[str]  # 参与本次推演的 agent_id 列表


class SandboxInit(SandboxEvent):
    event_type: EventType = EventType.SANDBOX_INIT
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    round: int = 0
    payload: SandboxInitPayload


class RoundTickPayload(BaseModel):
    """新一轮推演启动"""
    injected_event: Optional[str] = None   # 本轮注入的外部事件描述
    market_state_summary: str              # 当前市场状态摘要
    active_agents: list[str]               # 本轮参与的 agent_id 列表


class RoundTick(SandboxEvent):
    event_type: EventType = EventType.ROUND_TICK
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: RoundTickPayload


class RoundCompletePayload(BaseModel):
    """一轮推演结束汇总"""
    actions_count: int                     # 本轮收到的 AgentAction 总数
    net_sentiment: Sentiment               # 本轮净情绪
    key_actions_summary: str               # 关键行动摘要
    convergence_score: float = Field(ge=0, le=1)  # 收敛度评分
    should_continue: bool                  # Orchestrator 判断：继续 or 输出


class RoundComplete(SandboxEvent):
    event_type: EventType = EventType.ROUND_COMPLETE
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: RoundCompletePayload


# ============================================================
# 数据层事件 (CH-A)
# ============================================================

class MarketDataFeedPayload(BaseModel):
    """来自 Layer 1 的标准化市场数据"""
    data_type: str              # "price" | "fundamental" | "macro" | "sentiment"
    symbol: Optional[str] = None
    metrics: dict               # 灵活的指标键值对
    period: str                 # "daily" | "weekly" | "quarterly"
    data_source: str            # "baostock" | "yfinance" | "fred" | ...


class MarketDataFeed(SandboxEvent):
    event_type: EventType = EventType.MARKET_DATA_FEED
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: MarketDataFeedPayload


class NewsEventPayload(BaseModel):
    """新闻/政策/突发事件"""
    headline: str
    content_summary: str
    category: str               # "geopolitical" | "policy" | "earnings" | "breaking"
    severity: str               # "low" | "medium" | "high" | "critical"
    affected_symbols: list[str] = []
    source_url: Optional[str] = None


class NewsEvent(SandboxEvent):
    event_type: EventType = EventType.NEWS_EVENT
    channel: Channel = Channel.DATA_FEED
    payload: NewsEventPayload


# ============================================================
# 用户指令事件 (CH-B)
# ============================================================

class UserVarInjectionPayload(BaseModel):
    """用户注入假设变量"""
    variable_name: str          # 如 "interest_rate_change"
    description: str            # 自然语言描述："假设央行突然降息 50bp"
    value: Optional[str] = None # 结构化值（如果适用）
    affected_agents: list[str] = []  # 空 = 影响所有 Agent


class UserVarInjection(SandboxEvent):
    event_type: EventType = EventType.USER_VAR_INJECTION
    channel: Channel = Channel.USER_COMMAND
    source: str = "user"
    payload: UserVarInjectionPayload


class UserAgentConfigPayload(BaseModel):
    """用户调整 Agent 参数"""
    target_agent_id: str
    config_changes: dict        # 如 {"risk_appetite": "high", "horizon": "short"}
    action: str                 # "update_params" | "add_instance" | "remove_instance"


class UserAgentConfig(SandboxEvent):
    event_type: EventType = EventType.USER_AGENT_CONFIG
    channel: Channel = Channel.USER_COMMAND
    source: str = "user"
    payload: UserAgentConfigPayload


# ============================================================
# Agent 行为事件 (CH-C / Track 1 — 结构化行为总线)
# ============================================================

class AgentActionPayload(BaseModel):
    """
    Agent 的正式交易决策（Track 1）

    这是给 Orchestrator 和决策层消费的结构化数据。
    reasoning_ref 指向对应的 AgentNarrative 事件（Track 2），
    两者共享同一个 trace_id。
    """
    action: ActionVerb
    target: str                 # symbol
    size: str                   # "+3%", "-5%", "N/A"（观望时）
    confidence: float = Field(ge=0, le=1)
    stop_loss: Optional[str] = None     # 止损位
    target_price: Optional[str] = None  # 目标价
    holding_period: Optional[str] = None  # 预期持仓周期
    reasoning_ref: Optional[UUID] = None  # 关联 Track 2 叙事的 id


class AgentAction(SandboxEvent):
    event_type: EventType = EventType.AGENT_ACTION
    channel: Channel = Channel.AGENT_CROSS
    payload: AgentActionPayload


class AgentSignalPayload(BaseModel):
    """
    Agent 发出的非交易信号（Track 1）

    政策 Agent 发出监管预警、产业 Agent 发出供应链扰动信号等。
    不涉及交易动作，但影响其他 Agent 的决策。
    """
    signal_type: SignalType
    target: Optional[str] = None  # 受影响的 symbol 或领域
    strength: float = Field(ge=0, le=1)  # 信号强度
    description: str
    expected_impact: str        # 预期影响描述
    duration: str               # "short_term" | "medium_term" | "long_term"


class AgentSignal(SandboxEvent):
    event_type: EventType = EventType.AGENT_SIGNAL
    channel: Channel = Channel.AGENT_CROSS
    payload: AgentSignalPayload


# ============================================================
# Agent 叙事事件 (CH-C / Track 2 — 叙事讨论频道)
# ============================================================

class AgentNarrativePayload(BaseModel):
    """
    Agent 的推理叙事和辩论（Track 2）

    自然语言内容，用于：
    1. 其他 Agent 读取推理过程做决策参考
    2. 前端展示 Agent 行为日志下钻
    3. 记忆系统存储，支持回溯审计

    reply_to: 回复另一个叙事事件（形成辩论线程）
    mentions: 提及的其他 Agent（触发被提及 Agent 的关注）
    """
    content: str                # 自由文本：推理过程、辩论、观点
    reply_to: Optional[UUID] = None     # 回复哪条叙事（辩论线程）
    mentions: list[str] = []            # 提及的 agent_id 列表
    sentiment: Sentiment
    key_factors: list[str] = []         # 提取的关键决策因子


class AgentNarrative(SandboxEvent):
    event_type: EventType = EventType.AGENT_NARRATIVE
    channel: Channel = Channel.AGENT_CROSS
    payload: AgentNarrativePayload


# ============================================================
# 输出层事件
# ============================================================

class PathScenario(BaseModel):
    """单条路径分叉"""
    name: str                   # 路径名称（如 "牛市突破", "震荡消化"）
    probability: float = Field(ge=0, le=1)
    assumptions: list[str]      # 成立的前提假设
    checkpoints: list[str]      # 关键验证节点
    key_agents_view: dict       # 各 Agent 在此路径下的预期行为
    timeline: str               # 预期时间线


class PathForkPayload(BaseModel):
    """路径分叉输出"""
    paths: list[PathScenario] = Field(min_length=2, max_length=7)
    dominant_path: str          # 当前概率最高的路径名
    divergence_round: int       # 从哪一轮开始出现分叉
    total_rounds_simulated: int


class PathFork(SandboxEvent):
    event_type: EventType = EventType.PATH_FORK
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: PathForkPayload


class SandboxResultPayload(BaseModel):
    """
    推演最终结果，提交给 Layer 3 决策 Agent

    包含路径分叉 + 推演过程摘要 + 关键 Agent 行为日志引用
    """
    path_fork_ref: UUID                   # 关联 PathFork 事件的 id
    simulation_summary: str               # 推演过程总结
    total_rounds: int
    key_narrative_refs: list[UUID] = []   # 关键叙事事件的 id 列表
    agent_behavior_summary: dict          # 各 Agent 行为汇总
    risk_flags: list[str] = []            # 风险提示


class SandboxResult(SandboxEvent):
    event_type: EventType = EventType.SANDBOX_RESULT
    channel: Channel = Channel.DATA_FEED
    source: str = "system"
    payload: SandboxResultPayload


# ============================================================
# Agent Card（Agent 注册和发现）
# ============================================================

class AgentCard(BaseModel):
    """
    Agent 名片，注册到共享的 AgentRegistry

    所有 Agent 启动时把自己的 Card 注册进来，
    其他 Agent 可以查询 registry 了解"沙盘里有谁、擅长什么"。

    与 A2A 协议的 Agent Card 类似但更轻量——
    不需要 discovery protocol，直接查内存注册表。
    """
    agent_id: str               # 唯一标识
    agent_type: str             # "institutional" | "retail" | "short_seller" | ...
    instance_name: str          # "价值型基金" | "量化对冲基金" | ...
    behavior_template: str      # system prompt 摘要
    configurable_params: dict   # 当前参数配置
    current_state: dict         # 当前运行时状态（持仓、情绪...）
    subscribed_channels: list[Channel]
    is_active: bool = True
