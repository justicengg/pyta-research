"""Primary-market sandbox API endpoints."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.sandbox.orchestrator.primary import PrimaryOrchestrator
from src.sandbox.schemas.memory import Checkpoint, ReportRecord, SandboxSession

router = APIRouter()


class PrimaryRunRequest(BaseModel):
    """一级市场沙盘运行请求。"""
    company_name: str = Field(min_length=1, max_length=200)
    sector: str | None = None
    company_info: dict[str, Any] = Field(default_factory=dict)
    max_rounds: int = Field(default=3, ge=1, le=5)


@router.post("/primary/run", dependencies=[Depends(verify_api_key)])
async def run_primary_sandbox(
    body: PrimaryRunRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    orchestrator = PrimaryOrchestrator(max_rounds=body.max_rounds)
    result = await orchestrator.run(
        session=session,
        company_name=body.company_name,
        sector=body.sector,
        company_info=body.company_info,
    )
    sandbox = session.get(SandboxSession, result.sandbox_id)
    return {
        "sandbox_id": str(result.sandbox_id),
        "company_name": result.company_name,
        "rounds_completed": result.rounds_completed,
        "stop_reason": result.stop_reason,
        "session_status": sandbox.status if sandbox is not None else "completed",
        "report": result.report.model_dump(mode="json"),
    }


@router.get("/primary/{sandbox_id}/result", dependencies=[Depends(verify_api_key)])
def get_primary_result(
    sandbox_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    sandbox = session.get(SandboxSession, sandbox_id)
    if sandbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox session not found")

    report = session.scalar(
        select(ReportRecord)
        .where(ReportRecord.sandbox_id == sandbox_id)
        .where(ReportRecord.report_type == "company_analysis_report")
        .order_by(ReportRecord.round.desc(), ReportRecord.generated_at.desc())
        .limit(1)
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary analysis result not found")

    checkpoint = session.scalar(
        select(Checkpoint)
        .where(Checkpoint.sandbox_id == sandbox_id)
        .order_by(Checkpoint.round.desc(), Checkpoint.created_at.desc())
        .limit(1)
    )

    return {
        "sandbox_id": str(sandbox.id),
        "company_name": sandbox.ticker,
        "session_status": sandbox.status,
        "current_round": sandbox.current_round,
        "report": report.assembly_notes.get("report") if isinstance(report.assembly_notes, dict) else None,
        "latest_checkpoint": {
            "round": checkpoint.round,
            "completion_status": checkpoint.completion_status,
            "round_summary": checkpoint.round_summary,
        } if checkpoint else None,
    }
