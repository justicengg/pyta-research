"""add strategy_card 2.0 fields

Revision ID: 20260305_0005
Revises: 20260302_0004
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260305_0005'
down_revision = '20260302_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == 'postgresql' else sa.JSON()

    op.add_column('strategy_card', sa.Column('industry', sa.String(length=64), nullable=True))
    op.add_column('strategy_card', sa.Column('expected_cycle', sa.String(length=32), nullable=True))
    op.add_column('strategy_card', sa.Column('valuation_anchor', json_type, nullable=True))
    op.add_column('strategy_card', sa.Column('position_rules', json_type, nullable=True))
    op.add_column('strategy_card', sa.Column('entry_rules', json_type, nullable=True))
    op.add_column('strategy_card', sa.Column('exit_rules', json_type, nullable=True))
    op.add_column('strategy_card', sa.Column('risk_rules', json_type, nullable=True))
    op.add_column('strategy_card', sa.Column('review_cadence', sa.String(length=16), nullable=True))
    op.add_column('strategy_card', sa.Column('rules_version', sa.Integer(), nullable=True, server_default='1'))


def downgrade() -> None:
    op.drop_column('strategy_card', 'rules_version')
    op.drop_column('strategy_card', 'review_cadence')
    op.drop_column('strategy_card', 'risk_rules')
    op.drop_column('strategy_card', 'exit_rules')
    op.drop_column('strategy_card', 'entry_rules')
    op.drop_column('strategy_card', 'position_rules')
    op.drop_column('strategy_card', 'valuation_anchor')
    op.drop_column('strategy_card', 'expected_cycle')
    op.drop_column('strategy_card', 'industry')
