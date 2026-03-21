"""Helpers for sandbox developer CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sandbox.schemas.memory import AgentSnapshot, Checkpoint, ReportRecord, SandboxEventRecord, SandboxSession


def load_events_file(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        events = payload
    elif isinstance(payload, dict) and isinstance(payload.get("events"), list):
        events = payload["events"]
    else:
        raise ValueError("Input file must be a JSON array or an object with an 'events' array.")
    if not events:
        raise ValueError("Input events file is empty.")
    return events


def write_json(path: str, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def serialize_checkpoint(record: Checkpoint | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "id": str(record.id),
        "sandbox_id": str(record.sandbox_id),
        "round": record.round,
        "completion_status": record.completion_status,
        "active_agent_ids": record.active_agent_ids,
        "reused_agent_ids": record.reused_agent_ids,
        "degraded_agent_ids": record.degraded_agent_ids,
        "round_summary": record.round_summary,
        "created_at": record.created_at.isoformat(),
    }


def serialize_report(record: ReportRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "sandbox_id": str(record.sandbox_id),
        "trace_id": str(record.trace_id) if record.trace_id else None,
        "round": record.round,
        "report_type": record.report_type,
        "data_quality": record.data_quality,
        "perspective_synthesis": record.perspective_synthesis,
        "key_tensions": record.key_tensions,
        "tracking_signals": record.tracking_signals,
        "per_agent_detail": record.per_agent_detail,
        "assembly_notes": record.assembly_notes,
        "generated_at": record.generated_at.isoformat(),
    }


def fetch_sandbox(session: Session, sandbox_id: UUID) -> SandboxSession | None:
    return session.get(SandboxSession, sandbox_id)


def fetch_latest_report(session: Session, sandbox_id: UUID) -> ReportRecord | None:
    stmt = (
        select(ReportRecord)
        .where(ReportRecord.sandbox_id == sandbox_id)
        .order_by(ReportRecord.round.desc(), ReportRecord.generated_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def fetch_latest_checkpoint(session: Session, sandbox_id: UUID) -> Checkpoint | None:
    stmt = (
        select(Checkpoint)
        .where(Checkpoint.sandbox_id == sandbox_id)
        .order_by(Checkpoint.round.desc(), Checkpoint.created_at.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def fetch_input_events(session: Session, sandbox_id: UUID) -> list[dict[str, Any]]:
    stmt = (
        select(SandboxEventRecord)
        .where(
            SandboxEventRecord.sandbox_id == sandbox_id,
            SandboxEventRecord.event_type == "input_event",
        )
        .order_by(SandboxEventRecord.round.asc(), SandboxEventRecord.created_at.asc())
    )
    return [row.payload for row in session.scalars(stmt).all()]


def fetch_event_summaries(session: Session, sandbox_id: UUID) -> list[dict[str, Any]]:
    stmt = (
        select(SandboxEventRecord)
        .where(SandboxEventRecord.sandbox_id == sandbox_id)
        .order_by(SandboxEventRecord.round.asc(), SandboxEventRecord.created_at.asc())
    )
    rows = session.scalars(stmt).all()
    return [
        {
            "round": row.round,
            "event_type": row.event_type,
            "source": row.source,
            "agent_id": row.agent_id,
            "trace_id": str(row.trace_id) if row.trace_id else None,
            "perspective_status": row.perspective_status,
            "is_degraded": row.is_degraded,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def fetch_snapshot_summaries(session: Session, sandbox_id: UUID) -> list[dict[str, Any]]:
    stmt = (
        select(AgentSnapshot)
        .where(AgentSnapshot.sandbox_id == sandbox_id)
        .order_by(AgentSnapshot.round.asc(), AgentSnapshot.created_at.asc())
    )
    rows = session.scalars(stmt).all()
    return [
        {
            "round": row.round,
            "agent_id": row.agent_id,
            "perspective_type": row.perspective_type,
            "perspective_status": row.perspective_status,
            "key_observations": row.key_observations,
            "key_concerns": row.key_concerns,
            "analytical_focus": row.analytical_focus,
            "confidence": row.confidence,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]

