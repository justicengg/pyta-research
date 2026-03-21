"""add sandbox tables for secondary-market mvp

Revision ID: 20260321_0007
Revises: 20260305_0006
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20260321_0007"
down_revision = "20260305_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sandbox_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("market", sa.String(length=16), nullable=False),
        sa.Column("task_scope", sa.Text(), nullable=False),
        sa.Column("narrative_guide", sa.Text(), nullable=True),
        sa.Column("round_timeout_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_round", sa.Integer(), nullable=False),
        sa.Column("total_rounds", sa.Integer(), nullable=False),
        sa.Column("agent_instance_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sandbox_sessions_user_id", "sandbox_sessions", ["user_id"])

    op.create_table(
        "sandbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("sandbox_id", sa.Uuid(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("perspective_status", sa.String(length=24), nullable=True),
        sa.Column("is_degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("degraded_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandbox_sessions.id"]),
    )
    op.create_index("ix_event_sandbox_round", "sandbox_events", ["sandbox_id", "round"])
    op.create_index("ix_event_sandbox_type", "sandbox_events", ["sandbox_id", "event_type"])
    op.create_index("ix_event_source", "sandbox_events", ["sandbox_id", "source"])
    op.create_index("ix_sandbox_events_trace_id", "sandbox_events", ["trace_id"])

    op.create_table(
        "agent_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("sandbox_id", sa.Uuid(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("perspective_type", sa.String(length=64), nullable=False),
        sa.Column("perspective_status", sa.String(length=24), nullable=False),
        sa.Column("key_observations", sa.JSON(), nullable=False),
        sa.Column("key_concerns", sa.JSON(), nullable=False),
        sa.Column("analytical_focus", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_trace_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandbox_sessions.id"]),
    )
    op.create_index("ix_agent_snapshot_lookup", "agent_snapshots", ["sandbox_id", "agent_id", "round"])

    op.create_table(
        "report_records",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("sandbox_id", sa.Uuid(), nullable=False),
        sa.Column("trace_id", sa.Uuid(), nullable=True),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("data_quality", sa.String(length=16), nullable=False),
        sa.Column("perspective_synthesis", sa.JSON(), nullable=False),
        sa.Column("key_tensions", sa.JSON(), nullable=False),
        sa.Column("tracking_signals", sa.JSON(), nullable=False),
        sa.Column("per_agent_detail", sa.JSON(), nullable=False),
        sa.Column("assembly_notes", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandbox_sessions.id"]),
    )
    op.create_index("ix_report_records_sandbox_id", "report_records", ["sandbox_id"])
    op.create_index("ix_report_records_trace_id", "report_records", ["trace_id"])

    op.create_table(
        "checkpoints",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("sandbox_id", sa.Uuid(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("completion_status", sa.String(length=16), nullable=False),
        sa.Column("active_agent_ids", sa.JSON(), nullable=False),
        sa.Column("reused_agent_ids", sa.JSON(), nullable=False),
        sa.Column("degraded_agent_ids", sa.JSON(), nullable=False),
        sa.Column("round_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sandbox_id"], ["sandbox_sessions.id"]),
    )
    op.create_index("ix_checkpoints_sandbox_id", "checkpoints", ["sandbox_id"])
    op.create_index("ix_checkpoint_sandbox_round", "checkpoints", ["sandbox_id", "round"])


def downgrade() -> None:
    op.drop_index("ix_checkpoint_sandbox_round", table_name="checkpoints")
    op.drop_index("ix_checkpoints_sandbox_id", table_name="checkpoints")
    op.drop_table("checkpoints")

    op.drop_index("ix_report_records_trace_id", table_name="report_records")
    op.drop_index("ix_report_records_sandbox_id", table_name="report_records")
    op.drop_table("report_records")

    op.drop_index("ix_agent_snapshot_lookup", table_name="agent_snapshots")
    op.drop_table("agent_snapshots")

    op.drop_index("ix_sandbox_events_trace_id", table_name="sandbox_events")
    op.drop_index("ix_event_source", table_name="sandbox_events")
    op.drop_index("ix_event_sandbox_type", table_name="sandbox_events")
    op.drop_index("ix_event_sandbox_round", table_name="sandbox_events")
    op.drop_table("sandbox_events")

    op.drop_index("ix_sandbox_sessions_user_id", table_name="sandbox_sessions")
    op.drop_table("sandbox_sessions")
