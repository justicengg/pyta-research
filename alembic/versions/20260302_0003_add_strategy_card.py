"""add strategy_card table

Revision ID: 20260302_0003
Revises: 20260302_0002
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = '20260302_0003'
down_revision = '20260302_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strategy_card',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        # Human-filled fields (NULL until reviewed)
        sa.Column('thesis', sa.Text()),
        sa.Column('position_pct', sa.Numeric(6, 4)),
        # Auto-filled by CardGenerator
        sa.Column('valuation_note', sa.Text()),
        sa.Column('entry_price', sa.Numeric(18, 6)),
        sa.Column('entry_date', sa.Date()),
        sa.Column('stop_loss_price', sa.Numeric(18, 6)),
        # Lifecycle
        sa.Column('status', sa.String(length=16), nullable=False, server_default='draft'),
        sa.Column('close_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_strategy_card_symbol_market', 'strategy_card', ['symbol', 'market'])
    op.create_index('ix_strategy_card_status', 'strategy_card', ['status'])
    op.create_index('ix_strategy_card_created_at', 'strategy_card', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_strategy_card_created_at', table_name='strategy_card')
    op.drop_index('ix_strategy_card_status', table_name='strategy_card')
    op.drop_index('ix_strategy_card_symbol_market', table_name='strategy_card')
    op.drop_table('strategy_card')
