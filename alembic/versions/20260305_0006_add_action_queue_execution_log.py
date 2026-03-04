"""add action_queue and execution_log tables

Revision ID: 20260305_0006
Revises: 20260305_0005
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = '20260305_0006'
down_revision = '20260305_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'action_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('card_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False, server_default='normal'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('rule_tag', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('generated_date', sa.Date(), nullable=False),
        sa.Column('expires_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('exit', 'trim', 'hold', 'enter', 'watch', 'review')", name='ck_action_queue_action'),
        sa.CheckConstraint("priority IN ('urgent', 'normal', 'informational')", name='ck_action_queue_priority'),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'modified', 'expired')",
            name='ck_action_queue_status',
        ),
        sa.ForeignKeyConstraint(['card_id'], ['strategy_card.id'], ondelete='SET NULL'),
        sa.UniqueConstraint(
            'generated_date', 'symbol', 'market', 'action', 'card_id', 'rule_tag',
            name='uq_action_queue_business_key',
        ),
    )
    op.create_index('ix_action_queue_generated_date', 'action_queue', ['generated_date'])
    op.create_index('ix_action_queue_status', 'action_queue', ['status'])
    op.create_index('ix_action_queue_card_id', 'action_queue', ['card_id'])
    op.create_index(
        'ix_action_queue_generated_status_priority',
        'action_queue',
        ['generated_date', 'status', 'priority'],
    )

    op.create_table(
        'execution_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action_queue_id', sa.Integer(), nullable=True),
        sa.Column('card_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('response', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False, server_default='system_suggestion'),
        sa.Column('executed_price', sa.Numeric(18, 6), nullable=True),
        sa.Column('executed_quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("response IN ('accepted', 'rejected', 'modified')", name='ck_execution_log_response'),
        sa.CheckConstraint(
            "source IN ('system_suggestion', 'manual_override', 'external_trade')",
            name='ck_execution_log_source',
        ),
        sa.ForeignKeyConstraint(['action_queue_id'], ['action_queue.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['card_id'], ['strategy_card.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_execution_log_card_id', 'execution_log', ['card_id'])
    op.create_index('ix_execution_log_created_at', 'execution_log', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_execution_log_created_at', table_name='execution_log')
    op.drop_index('ix_execution_log_card_id', table_name='execution_log')
    op.drop_table('execution_log')

    op.drop_index('ix_action_queue_generated_status_priority', table_name='action_queue')
    op.drop_index('ix_action_queue_card_id', table_name='action_queue')
    op.drop_index('ix_action_queue_status', table_name='action_queue')
    op.drop_index('ix_action_queue_generated_date', table_name='action_queue')
    op.drop_table('action_queue')
