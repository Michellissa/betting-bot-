"""add odds columns to feature_store

Revision ID: 3f8a9b2c1d5e
Revises: 7cf2642cf797
Create Date: 2026-07-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '3f8a9b2c1d5e'
down_revision: str | None = '7cf2642cf797'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('feature_store', sa.Column('odds_home_prob', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_draw_prob', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_away_prob', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_overround', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_home_odds_raw', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_draw_odds_raw', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_away_odds_raw', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('odds_source', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('feature_store', 'odds_source')
    op.drop_column('feature_store', 'odds_away_odds_raw')
    op.drop_column('feature_store', 'odds_draw_odds_raw')
    op.drop_column('feature_store', 'odds_home_odds_raw')
    op.drop_column('feature_store', 'odds_overround')
    op.drop_column('feature_store', 'odds_away_prob')
    op.drop_column('feature_store', 'odds_draw_prob')
    op.drop_column('feature_store', 'odds_home_prob')
