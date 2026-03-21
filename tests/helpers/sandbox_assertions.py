from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sandbox.schemas.memory import AgentSnapshot, Checkpoint, ReportRecord, SandboxEventRecord, SandboxSession


@dataclass
class SandboxBundle:
    session: SandboxSession
    events: list[SandboxEventRecord]
    snapshots: list[AgentSnapshot]
    reports: list[ReportRecord]
    checkpoints: list[Checkpoint]


def fetch_sandbox_bundle(session: Session, sandbox_id: UUID) -> SandboxBundle:
    sandbox = session.get(SandboxSession, sandbox_id)
    assert sandbox is not None, f"sandbox session not found for {sandbox_id}"
    events = list(session.scalars(select(SandboxEventRecord).where(SandboxEventRecord.sandbox_id == sandbox_id)).all())
    snapshots = list(session.scalars(select(AgentSnapshot).where(AgentSnapshot.sandbox_id == sandbox_id)).all())
    reports = list(session.scalars(select(ReportRecord).where(ReportRecord.sandbox_id == sandbox_id)).all())
    checkpoints = list(session.scalars(select(Checkpoint).where(Checkpoint.sandbox_id == sandbox_id)).all())
    return SandboxBundle(session=sandbox, events=events, snapshots=snapshots, reports=reports, checkpoints=checkpoints)


def assert_sandbox_records_consistent(
    session: Session,
    sandbox_id: UUID,
    *,
    expected_round: int = 1,
    expected_report_count: int = 1,
    expected_checkpoint_count: int = 1,
    min_event_count: int = 1,
    expected_snapshot_count: int | None = None,
) -> SandboxBundle:
    bundle = fetch_sandbox_bundle(session, sandbox_id)
    assert bundle.session.current_round == expected_round
    assert bundle.session.total_rounds == expected_round
    assert len(bundle.events) >= min_event_count
    assert len(bundle.reports) == expected_report_count
    assert len(bundle.checkpoints) == expected_checkpoint_count
    if expected_snapshot_count is not None:
        assert len(bundle.snapshots) == expected_snapshot_count

    sandbox_ids = {
        *(row.sandbox_id for row in bundle.events),
        *(row.sandbox_id for row in bundle.snapshots),
        *(row.sandbox_id for row in bundle.reports),
        *(row.sandbox_id for row in bundle.checkpoints),
    }
    assert sandbox_ids == {sandbox_id}
    return bundle

