"""add derived_factors table

Revision ID: 20260302_0002
Revises: 20260301_0001
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa

revision = '20260302_0002'
down_revision = '20260301_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'derived_factors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('market', sa.String(length=16), nullable=False),
        sa.Column('asof_date', sa.Date(), nullable=False),
        sa.Column('factor_name', sa.String(length=64), nullable=False),
        sa.Column('factor_value', sa.Numeric(20, 8)),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('symbol', 'market', 'asof_date', 'factor_name', name='uq_derived_factor_key'),
    )
    op.create_index('ix_derived_factors_market_symbol_asof_date', 'derived_factors', ['market', 'symbol', 'asof_date'])
    op.create_index('ix_derived_factors_factor_name_asof_date', 'derived_factors', ['factor_name', 'asof_date'])


def downgrade() -> None:
    op.drop_index('ix_derived_factors_factor_name_asof_date', table_name='derived_factors')
    op.drop_index('ix_derived_factors_market_symbol_asof_date', table_name='derived_factors')
    op.drop_table('derived_factors')
