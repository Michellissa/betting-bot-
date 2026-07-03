"""add player availability columns to feature_store

Revision ID: 4a7b3c2d8e6f
Revises: 3f8a9b2c1d5e
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '4a7b3c2d8e6f'
down_revision: str | None = '3f8a9b2c1d5e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('feature_store', sa.Column('home_missing_players_count', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('away_missing_players_count', sa.Float(), nullable=True))
    op.add_column('feature_store', sa.Column('player_data_available', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('feature_store', 'player_data_available')
    op.drop_column('feature_store', 'away_missing_players_count')
    op.drop_column('feature_store', 'home_missing_players_count')
