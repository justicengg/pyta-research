"""Secondary-market sandbox API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.sandbox.orchestrator.secondary import SecondaryOrchestrator
from src.sandbox.schemas.environment import EnvironmentState
from src.sandbox.schemas.memory import Checkpoint, ReportRecord, SandboxSession

router = APIRouter()


class SandboxInputEvent(BaseModel):
    event_id: str
    event_type: str
    content: str
    source: str
    timestamp: datetime
    symbol: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxRunRequest(BaseModel):
    ticker: str
    market: str
    events: list[SandboxInputEvent] = Field(min_length=1)
    environment_state: EnvironmentState | None = None
    round_timeout_ms: int = Field(default=60000, ge=1000, le=120000)
    narrative_guide: str | None = None


def _serialize_report_record(record: ReportRecord) -> dict[str, Any]:
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


def _serialize_checkpoint(record: Checkpoint | None) -> dict[str, Any] | None:
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


@router.post("/sandbox/run", dependencies=[Depends(verify_api_key)])
async def run_sandbox(
    body: SandboxRunRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    orchestrator = SecondaryOrchestrator()
    result = await orchestrator.run(
        session=session,
        ticker=body.ticker,
        market=body.market,
        events=[event.model_dump(mode="json") for event in body.events],
        environment_state=body.environment_state,
        round_timeout_ms=body.round_timeout_ms,
        narrative_guide=body.narrative_guide,
    )
    sandbox = session.get(SandboxSession, result.sandbox_id)
    return {
        "sandbox_id": str(result.sandbox_id),
        "session_status": sandbox.status if sandbox is not None else result.round_complete.data_quality,
        "environment_state": result.environment_state.model_dump(mode="json"),
        "round_complete": result.round_complete.model_dump(mode="json"),
        "report": result.report.model_dump(mode="json"),
    }


@router.get("/sandbox/{sandbox_id}/result", dependencies=[Depends(verify_api_key)])
def get_sandbox_result(
    sandbox_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    sandbox = session.get(SandboxSession, sandbox_id)
    if sandbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox session not found")

    report = session.scalar(
        select(ReportRecord)
        .where(ReportRecord.sandbox_id == sandbox_id)
        .order_by(ReportRecord.round.desc(), ReportRecord.generated_at.desc())
        .limit(1)
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox result not found")

    checkpoint = session.scalar(
        select(Checkpoint)
        .where(Checkpoint.sandbox_id == sandbox_id)
        .order_by(Checkpoint.round.desc(), Checkpoint.created_at.desc())
        .limit(1)
    )

    return {
        "sandbox_id": str(sandbox.id),
        "ticker": sandbox.ticker,
        "market": sandbox.market,
        "session_status": sandbox.status,
        "current_round": sandbox.current_round,
        "report": _serialize_report_record(report),
        "latest_checkpoint": _serialize_checkpoint(checkpoint),
    }
