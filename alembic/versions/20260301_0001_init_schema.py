"""init schema

Revision ID: 20260301_0001
Revises:
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = '20260301_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'raw_price',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(18, 6)),
        sa.Column('high', sa.Numeric(18, 6)),
        sa.Column('low', sa.Numeric(18, 6)),
        sa.Column('close', sa.Numeric(18, 6)),
        sa.Column('volume', sa.Numeric(24, 6)),
        sa.Column('adj_factor', sa.Numeric(18, 8)),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('quality_status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.UniqueConstraint('symbol', 'market', 'trade_date', 'source', name='uq_raw_price_key'),
    )
    op.create_index('ix_raw_price_market_symbol_trade_date', 'raw_price', ['market', 'symbol', 'trade_date'])
    op.create_index('ix_raw_price_quality_status', 'raw_price', ['quality_status'])
    op.create_index('ix_raw_price_ingested_at', 'raw_price', ['ingested_at'])

    op.create_table(
        'raw_fundamental',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('report_period', sa.Date(), nullable=False),
        sa.Column('publish_date', sa.Date(), nullable=False),
        sa.Column('roe', sa.Numeric(18, 6)),
        sa.Column('revenue', sa.Numeric(24, 6)),
        sa.Column('net_profit', sa.Numeric(24, 6)),
        sa.Column('debt_ratio', sa.Numeric(18, 6)),
        sa.Column('operating_cashflow', sa.Numeric(24, 6)),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('quality_status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.UniqueConstraint('symbol', 'market', 'report_period', 'publish_date', 'source', name='uq_raw_fundamental_key'),
    )
    op.create_index(
        'ix_raw_fundamental_market_symbol_report_period',
        'raw_fundamental',
        ['market', 'symbol', 'report_period'],
    )
    op.create_index('ix_raw_fundamental_quality_status', 'raw_fundamental', ['quality_status'])
    op.create_index('ix_raw_fundamental_ingested_at', 'raw_fundamental', ['ingested_at'])

    op.create_table(
        'raw_macro',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('series_code', sa.String(length=64), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('obs_date', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(24, 8)),
        sa.Column('frequency', sa.String(length=16)),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('quality_status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.UniqueConstraint('series_code', 'market', 'obs_date', 'source', name='uq_raw_macro_key'),
    )
    op.create_index('ix_raw_macro_market_series_code_obs_date', 'raw_macro', ['market', 'series_code', 'obs_date'])
    op.create_index('ix_raw_macro_quality_status', 'raw_macro', ['quality_status'])
    op.create_index('ix_raw_macro_ingested_at', 'raw_macro', ['ingested_at'])


def downgrade() -> None:
    op.drop_index('ix_raw_macro_ingested_at', table_name='raw_macro')
    op.drop_index('ix_raw_macro_quality_status', table_name='raw_macro')
    op.drop_index('ix_raw_macro_market_series_code_obs_date', table_name='raw_macro')
    op.drop_table('raw_macro')

    op.drop_index('ix_raw_fundamental_ingested_at', table_name='raw_fundamental')
    op.drop_index('ix_raw_fundamental_quality_status', table_name='raw_fundamental')
    op.drop_index('ix_raw_fundamental_market_symbol_report_period', table_name='raw_fundamental')
    op.drop_table('raw_fundamental')

    op.drop_index('ix_raw_price_ingested_at', table_name='raw_price')
    op.drop_index('ix_raw_price_quality_status', table_name='raw_price')
    op.drop_index('ix_raw_price_market_symbol_trade_date', table_name='raw_price')
    op.drop_table('raw_price')
