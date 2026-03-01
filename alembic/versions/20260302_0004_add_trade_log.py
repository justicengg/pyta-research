"""add trade_log table

Revision ID: 20260302_0004
Revises: 20260302_0003
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = '20260302_0004'
down_revision = '20260302_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trade_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('card_id', sa.Integer()),          # soft ref to strategy_card.id
        sa.Column('direction', sa.String(length=8), nullable=False),  # buy | sell
        sa.Column('price', sa.Numeric(18, 6), nullable=False),
        sa.Column('shares', sa.Numeric(18, 4), nullable=False),
        sa.Column('amount', sa.Numeric(24, 6), nullable=False),  # price * shares
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('note', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_trade_log_symbol_market_trade_date', 'trade_log', ['symbol', 'market', 'trade_date'])
    op.create_index('ix_trade_log_trade_date', 'trade_log', ['trade_date'])
    op.create_index('ix_trade_log_card_id', 'trade_log', ['card_id'])


def downgrade() -> None:
    op.drop_index('ix_trade_log_card_id', table_name='trade_log')
    op.drop_index('ix_trade_log_trade_date', table_name='trade_log')
    op.drop_index('ix_trade_log_symbol_market_trade_date', table_name='trade_log')
    op.drop_table('trade_log')
