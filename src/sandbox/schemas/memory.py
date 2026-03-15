"""
PYTA Memory System Database Schema
====================================
统一记忆中心的完整数据库表设计

技术栈：PostgreSQL + pgvector + SQLAlchemy + Alembic
设计原则：
1. 贯穿五层架构，每一层都能写入和读取
2. 四个关联键贯穿所有表：sandbox_id, trace_id, agent_id, round
3. 长期记忆使用 pgvector 做向量检索，支持历史模式匹配
4. 所有写入不可变（append-only），支持完整回溯审计
"""

from __future__ import annotations
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Index, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship

# pgvector 扩展
# 需要: CREATE EXTENSION IF NOT EXISTS vector;
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ============================================================
# Zone 5: Session Management（先建，其他表都依赖它）
# ============================================================

class SandboxSession(Base):
    """
    沙盘推演会话（一次完整的推演过程）

    每次用户发起推演就创建一个 session。
    所有事件、快照、路径分叉、决策日志都挂在 session 下。
    """
    __tablename__ = "sandbox_sessions"

    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, nullable=False, index=True)

    # 推演配置
    task_scope = Column(Text, nullable=False)          # 推演任务描述
    target_symbols = Column(ARRAY(String), nullable=False)  # 目标标的
    time_horizon = Column(String(32), nullable=False)  # 推演时间跨度
    narrative_guide = Column(Text)                     # 推演叙事引导
    max_rounds = Column(Integer, default=10)

    # 运行状态
    status = Column(
        SAEnum("initializing", "running", "converged", "forced_stop",
               "oscillation", "error", name="session_status"),
        default="initializing"
    )
    current_round = Column(Integer, default=0)
    total_rounds = Column(Integer)                     # 实际推演轮次（结束时填写）

    # 健康状态
    final_convergence_score = Column(Float)
    final_health_status = Column(String(16))           # healthy/degraded/critical
    final_data_completeness = Column(String(16))       # complete/partial/stale

    # 参与 Agent
    agent_instance_ids = Column(ARRAY(String))         # 本次推演的 agent_id 列表

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 关联
    events = relationship("SandboxEventRecord", back_populates="session")
    checkpoints = relationship("Checkpoint", back_populates="session")
    path_forks = relationship("PathForkRecord", back_populates="session")
    decision_records = relationship("DecisionRecord", back_populates="session")


class Checkpoint(Base):
    """
    推演断点快照（用于断点续推和回溯）

    Orchestrator 每轮结束时自动创建。
    系统崩溃后可从最近 checkpoint 恢复。
    用户也可以手动回退到某个 checkpoint 重新推演。
    """
    __tablename__ = "checkpoints"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False, index=True)
    round = Column(Integer, nullable=False)

    # 快照内容
    agent_states = Column(JSONB, nullable=False)       # 所有 Agent 的 current_state 快照
    event_queue_snapshot = Column(JSONB)                # 事件队列中未处理的事件
    convergence_score = Column(Float)
    health_status = Column(String(16))

    # 元数据
    trigger = Column(String(32))                       # auto/manual/error_recovery
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SandboxSession", back_populates="checkpoints")

    __table_args__ = (
        Index("ix_checkpoint_sandbox_round", "sandbox_id", "round"),
    )


# ============================================================
# Zone 1: Short-term Memory（事件流）
# ============================================================

class SandboxEventRecord(Base):
    """
    沙盘事件记录（所有 12 种事件类型的统一存储）

    这是短期记忆的核心表。每条事件按 SandboxEvent schema 存入。
    append-only，不可修改，支持完整回溯。

    关键索引：sandbox_id + round（按轮次查询），trace_id（双轨关联）
    """
    __tablename__ = "sandbox_events"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False)
    round = Column(Integer, nullable=False)

    # 事件元数据
    channel = Column(String(8), nullable=False)        # CH-A / CH-B / CH-C
    event_type = Column(String(32), nullable=False)    # 12 种事件类型枚举
    source = Column(String(64), nullable=False)        # agent_id / system / user
    trace_id = Column(UUID, index=True)                # 关联 Track 1 + Track 2

    # 长/短事件标记
    event_duration = Column(String(8), default="short")  # short / long
    phase = Column(String(4))                          # A / B / C（长事件阶段）

    # 事件内容（所有 payload 统一存为 JSONB）
    payload = Column(JSONB, nullable=False)

    # 容错标记
    is_degraded = Column(Boolean, default=False)
    degraded_reason = Column(String(128))

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SandboxSession", back_populates="events")

    __table_args__ = (
        Index("ix_event_sandbox_round", "sandbox_id", "round"),
        Index("ix_event_sandbox_type", "sandbox_id", "event_type"),
        Index("ix_event_source", "sandbox_id", "source"),
    )


# ============================================================
# Zone 2: Long-term Memory（历史模式 + 向量检索）
# ============================================================

class MarketPattern(Base):
    """
    历史市场模式（长期记忆）

    存储从过往推演和真实市场中提炼的行为模式。
    使用 pgvector 存储 embedding，支持相似度搜索。

    用途：
    - 沙盘 Agent 推演时检索"历史上类似情况下机构怎么做的"
    - Orchestrator 判断"当前推演模式是否匹配某个已知历史模式"
    - 决策层 Agent 引用"2008 年类似场景的结局"
    """
    __tablename__ = "market_patterns"

    id = Column(UUID, primary_key=True, default=uuid4)

    # 模式描述
    pattern_name = Column(String(128), nullable=False)     # 如"2008金融危机-机构恐慌减仓"
    pattern_type = Column(String(32), nullable=False)      # crisis/bubble/policy_shift/sector_rotation/...
    description = Column(Text, nullable=False)

    # 来源
    source_type = Column(String(16), nullable=False)       # historical（真实历史）/ simulated（推演产出）
    source_sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"))  # 如来自推演

    # 模式内容
    agent_behaviors = Column(JSONB)                        # 各角色在此模式下的典型行为
    market_conditions = Column(JSONB)                      # 触发此模式的市场条件
    outcome = Column(JSONB)                                # 此模式的最终结果

    # 向量检索
    embedding = Column(Vector(1536))                       # description 的向量表示

    # 标签和元数据
    tags = Column(ARRAY(String))                           # 如 ["金融危机", "机构行为", "恐慌"]
    relevance_count = Column(Integer, default=0)           # 被引用次数（越高越有价值）

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_pattern_type", "pattern_type"),
    )


class NarrativeArchive(Base):
    """
    叙事归档（Track 2 的长期价值提取）

    从沙盘推演的 Track 2 叙事中提取有价值的洞察，
    存入长期记忆供后续推演参考。

    不是把所有叙事都存进来——而是 Orchestrator 在推演结束时
    筛选出"关键转折点的叙事"和"产生新洞察的辩论"。
    """
    __tablename__ = "narrative_archive"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False)
    source_event_id = Column(UUID, ForeignKey("sandbox_events.id"))  # 原始事件
    agent_id = Column(String(64), nullable=False)
    round = Column(Integer, nullable=False)

    # 内容
    content = Column(Text, nullable=False)
    insight_summary = Column(Text)                         # 提炼的洞察摘要
    sentiment = Column(String(16))
    key_factors = Column(ARRAY(String))

    # 归档原因
    archive_reason = Column(String(32))                    # turning_point/novel_insight/key_debate/...

    # 向量检索
    embedding = Column(Vector(1536))

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_narrative_sandbox", "sandbox_id"),
    )


# ============================================================
# Zone 3: Path Fork Archive（路径分叉记录）
# ============================================================

class PathForkRecord(Base):
    """
    路径分叉记录（推演结论的核心产出）

    一次推演产出一个 PathFork，包含 3-5 条命名路径。
    这是提交给决策层的主要输入。
    """
    __tablename__ = "path_forks"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False, index=True)

    # 分叉元数据
    dominant_path = Column(String(128))                    # 概率最高的路径名
    divergence_round = Column(Integer)                     # 从哪一轮开始分叉
    total_rounds = Column(Integer)

    # 收敛状态
    is_converged = Column(Boolean, default=True)
    is_oscillation = Column(Boolean, default=False)
    final_convergence_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SandboxSession", back_populates="path_forks")
    scenarios = relationship("PathScenarioRecord", back_populates="path_fork")


class PathScenarioRecord(Base):
    """
    单条路径场景（PathFork 的子记录）

    每条路径包含：名称、概率、前提假设、关键验证节点、各 Agent 预期行为。
    """
    __tablename__ = "path_scenarios"

    id = Column(UUID, primary_key=True, default=uuid4)
    path_fork_id = Column(UUID, ForeignKey("path_forks.id"), nullable=False, index=True)

    # 路径定义
    name = Column(String(128), nullable=False)             # 如"牛市突破"、"震荡消化"
    probability = Column(Float, nullable=False)
    timeline = Column(String(64))                          # 预期时间线

    # 前提假设
    assumptions = Column(ARRAY(String), nullable=False)    # 成立的前提条件列表

    # 关键验证节点（核心产品价值）
    checkpoints = Column(JSONB, nullable=False)
    # 格式：[{"condition": "Q3 NRR > 110%", "impact": "路径概率升至65%", "observe_by": "2026-Q3"}]

    # 各 Agent 在此路径下的预期行为
    agent_views = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)

    path_fork = relationship("PathForkRecord", back_populates="scenarios")


# ============================================================
# Zone 4: Decision Log（决策层日志）
# ============================================================

class DecisionRecord(Base):
    """
    决策层 Agent 的分析记录

    大聪明/大呆子/大善人各自对推演结果的分析和建议。
    包括它们之间的分歧点和最终聚合结果。
    """
    __tablename__ = "decision_records"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False, index=True)
    path_fork_id = Column(UUID, ForeignKey("path_forks.id"))

    # 决策 Agent 信息
    agent_id = Column(String(64), nullable=False)          # decision-dacongming / ...
    agent_role = Column(String(32))                        # chief_analyst / contrarian / risk_guardian
    llm_provider = Column(String(32))                      # 实际使用的 provider
    llm_model = Column(String(64))                         # 实际使用的 model

    # 分析结果
    recommendation = Column(String(32))                    # buy/sell/hold（二级）或 invest/pass/monitor（一级）
    confidence = Column(Float)
    reasoning = Column(Text, nullable=False)               # 完整分析推理过程

    # 输出类型
    output_schema = Column(String(32))                     # signal_card / investment_memo
    output_content = Column(JSONB)                         # 信号卡或备忘录的完整内容

    # 分歧标记
    is_minority_opinion = Column(Boolean, default=False)   # 是否与多数意见不同
    disagreement_details = Column(Text)                    # 分歧具体内容

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SandboxSession", back_populates="decision_records")


class UserDecision(Base):
    """
    用户最终决策记录

    用户看完三个决策 Agent 的建议后做出的最终拍板。
    这是整个推演链路的终点。
    """
    __tablename__ = "user_decisions"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False, index=True)
    user_id = Column(UUID, nullable=False, index=True)
    path_fork_id = Column(UUID, ForeignKey("path_forks.id"))

    # 用户决策
    decision = Column(String(32), nullable=False)          # buy/sell/hold/pass/defer
    chosen_path = Column(String(128))                      # 用户认为最可能的路径名
    position_size = Column(String(32))                     # 用户决定的仓位
    notes = Column(Text)                                   # 用户备注

    # 引用的决策 Agent
    primary_reference = Column(String(64))                 # 用户最参考哪个 Agent

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# Zone 6: Agent Snapshots（Agent 状态快照）
# ============================================================

class AgentSnapshot(Base):
    """
    Agent 状态快照（每轮结束时记录）

    记录每个 Agent 在每轮结束时的完整状态。
    用于：
    - 回溯某个 Agent 在第 N 轮时的持仓和情绪
    - 分析 Agent 状态变化趋势
    - 从 checkpoint 恢复时重建 Agent 状态
    """
    __tablename__ = "agent_snapshots"

    id = Column(UUID, primary_key=True, default=uuid4)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"), nullable=False)
    agent_id = Column(String(64), nullable=False)
    round = Column(Integer, nullable=False)

    # 状态快照（对应 AgentCard.current_state）
    state = Column(JSONB, nullable=False)
    # 沙盘 Agent: {holdings, cash_ratio, sentiment, last_action, cumulative_pnl}
    # 决策 Agent: {last_recommendation, confidence, reasoning_summary}

    # Agent Card 配置快照（记录当时的参数，用户可能中途改过）
    card_config = Column(JSONB)

    # 健康状态
    is_degraded = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_snapshot_lookup", "sandbox_id", "agent_id", "round"),
    )


class AgentCardRecord(Base):
    """
    Agent Card 版本记录

    每次用户修改 Agent Card 配置时记录一个版本。
    支持回溯"用户在第 N 轮时把风险偏好从 low 改成了 high"。
    """
    __tablename__ = "agent_cards"

    id = Column(UUID, primary_key=True, default=uuid4)
    agent_id = Column(String(64), nullable=False, index=True)
    sandbox_id = Column(UUID, ForeignKey("sandbox_sessions.id"))  # null = 全局默认配置

    # Card 层级
    card_layer = Column(String(16), nullable=False)        # sandbox（Layer 2）/ decision（Layer 3）

    # 完整 Card 内容
    card_content = Column(JSONB, nullable=False)           # 完整的 AgentCard JSON

    # 版本管理
    version = Column(Integer, default=1)
    change_reason = Column(String(128))                    # user_edit / system_default / param_injection
    changed_by = Column(String(16))                        # user / system

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_card_version", "agent_id", "sandbox_id", "version"),
    )
