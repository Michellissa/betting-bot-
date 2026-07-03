"""add data_confidence_score to prediction table

Revision ID: 5e9f8c7d6b4a
Revises: 4a7b3c2d8e6f
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '5e9f8c7d6b4a'
down_revision: str | None = '4a7b3c2d8e6f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('prediction', sa.Column('data_confidence_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('prediction', 'data_confidence_score')
