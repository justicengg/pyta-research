"""
PYTA Memory System Database Schema
=================================
二级市场第一版（Parallel Perspective Simulation）优先的持久化模型。

当前只实现 secondary-market MVP 必需的 5 张表：
- sandbox_sessions
- sandbox_events
- agent_snapshots
- report_records
- checkpoints
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import relationship

from src.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SandboxSession(Base):
    """一次二级市场推演会话。"""

    __tablename__ = "sandbox_sessions"

    id = Column(Uuid, primary_key=True, default=uuid4)
    user_id = Column(Uuid, nullable=True, index=True)

    ticker = Column(String(32), nullable=False)
    market = Column(String(16), nullable=False)
    task_scope = Column(Text, nullable=False)
    narrative_guide = Column(Text, nullable=True)
    round_timeout_ms = Column(Integer, default=30000, nullable=False)

    status = Column(
        SAEnum(
            "initializing",
            "running",
            "complete",
            "partial",
            "degraded",
            "error",
            name="session_status",
        ),
        default="initializing",
        nullable=False,
    )
    current_round = Column(Integer, default=0, nullable=False)
    total_rounds = Column(Integer, default=0, nullable=False)
    agent_instance_ids = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    events = relationship("SandboxEventRecord", back_populates="session")
    checkpoints = relationship("Checkpoint", back_populates="session")
    reports = relationship("ReportRecord", back_populates="session")


class SandboxEventRecord(Base):
    """统一追加写事件流。"""

    __tablename__ = "sandbox_events"

    id = Column(Uuid, primary_key=True, default=uuid4)
    sandbox_id = Column(
        Uuid,
        ForeignKey("sandbox_sessions.id"),
        nullable=False,
    )
    round = Column(Integer, nullable=False)

    channel = Column(String(8), nullable=False)
    event_type = Column(String(32), nullable=False)
    source = Column(String(64), nullable=False)
    trace_id = Column(Uuid, index=True, nullable=True)
    agent_id = Column(String(64), nullable=True)

    payload = Column(JSON, nullable=False)
    perspective_status = Column(String(24), nullable=True)
    is_degraded = Column(Boolean, default=False, nullable=False)
    degraded_reason = Column(String(128), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("SandboxSession", back_populates="events")

    __table_args__ = (
        Index("ix_event_sandbox_round", "sandbox_id", "round"),
        Index("ix_event_sandbox_type", "sandbox_id", "event_type"),
        Index("ix_event_source", "sandbox_id", "source"),
    )


class AgentSnapshot(Base):
    """每轮每个 Agent 的执行态快照，用于 timeout fallback。"""

    __tablename__ = "agent_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid4)
    sandbox_id = Column(
        Uuid,
        ForeignKey("sandbox_sessions.id"),
        nullable=False,
    )
    round = Column(Integer, nullable=False)
    agent_id = Column(String(64), nullable=False)

    perspective_type = Column(String(64), nullable=False)
    perspective_status = Column(String(24), nullable=False)
    key_observations = Column(JSON, nullable=False)
    key_concerns = Column(JSON, nullable=False)
    analytical_focus = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    source_trace_id = Column(Uuid, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_agent_snapshot_lookup", "sandbox_id", "agent_id", "round"),
    )


class ReportRecord(Base):
    """Layer 3 的报告就绪输出。"""

    __tablename__ = "report_records"

    id = Column(Uuid, primary_key=True, default=uuid4)
    sandbox_id = Column(
        Uuid,
        ForeignKey("sandbox_sessions.id"),
        nullable=False,
        index=True,
    )
    trace_id = Column(Uuid, nullable=True, index=True)
    round = Column(Integer, nullable=False)

    report_type = Column(String(32), nullable=False, default="market_reading_report")
    data_quality = Column(String(16), nullable=False)
    perspective_synthesis = Column(JSON, nullable=False)
    key_tensions = Column(JSON, nullable=False)
    tracking_signals = Column(JSON, nullable=False)
    per_agent_detail = Column(JSON, nullable=False)
    assembly_notes = Column(JSON, nullable=False)

    generated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("SandboxSession", back_populates="reports")


class Checkpoint(Base):
    """最小轮次级 checkpoint，不承载完整恢复引擎状态。"""

    __tablename__ = "checkpoints"

    id = Column(Uuid, primary_key=True, default=uuid4)
    sandbox_id = Column(
        Uuid,
        ForeignKey("sandbox_sessions.id"),
        nullable=False,
        index=True,
    )
    round = Column(Integer, nullable=False)
    completion_status = Column(String(16), nullable=False)
    active_agent_ids = Column(JSON, nullable=False, default=list)
    reused_agent_ids = Column(JSON, nullable=False, default=list)
    degraded_agent_ids = Column(JSON, nullable=False, default=list)
    round_summary = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("SandboxSession", back_populates="checkpoints")

    __table_args__ = (
        Index("ix_checkpoint_sandbox_round", "sandbox_id", "round"),
    )
