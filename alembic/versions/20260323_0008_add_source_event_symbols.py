"""add source connector tables and source_event symbols

Revision ID: 20260323_0008
Revises: 20260321_0007
Create Date: 2026-03-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260323_0008"
down_revision = "20260321_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "source_connector" not in tables:
        op.create_table(
            "source_connector",
            sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("provider_id", sa.String(length=64), nullable=False),
            sa.Column("api_key", sa.Text(), nullable=False),
            sa.Column("custom_config", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="healthy"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_source_connector_created_at", "source_connector", ["created_at"])

    if "source_event" not in tables:
        op.create_table(
            "source_event",
            sa.Column("id", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("connector_id", sa.String(length=64), nullable=False),
            sa.Column("provider_id", sa.String(length=64), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("dimension", sa.String(length=64), nullable=True),
            sa.Column("impact_direction", sa.String(length=16), nullable=False, server_default="neutral"),
            sa.Column("impact_strength", sa.Numeric(6, 3), nullable=False, server_default="0.5"),
            sa.Column("symbols", sa.JSON(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("ingested_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["connector_id"], ["source_connector.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_source_event_ingested", "source_event", ["ingested_at"])
        op.create_index("ix_source_event_published", "source_event", ["published_at"])
    else:
        columns = {column["name"] for column in inspector.get_columns("source_event")}
        if "symbols" not in columns:
            with op.batch_alter_table("source_event") as batch_op:
                batch_op.add_column(sa.Column("symbols", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "source_event" in tables:
        columns = {column["name"] for column in inspector.get_columns("source_event")}
        if "symbols" in columns:
            with op.batch_alter_table("source_event") as batch_op:
                batch_op.drop_column("symbols")
        existing_indexes = {index["name"] for index in inspector.get_indexes("source_event")}
        if "ix_source_event_published" in existing_indexes:
            op.drop_index("ix_source_event_published", table_name="source_event")
        if "ix_source_event_ingested" in existing_indexes:
            op.drop_index("ix_source_event_ingested", table_name="source_event")
        op.drop_table("source_event")

    if "source_connector" in tables:
        existing_indexes = {index["name"] for index in inspector.get_indexes("source_connector")}
        if "ix_source_connector_created_at" in existing_indexes:
            op.drop_index("ix_source_connector_created_at", table_name="source_connector")
        op.drop_table("source_connector")
