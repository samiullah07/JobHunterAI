"""Add scoring columns to user_profiles and match_scores.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("embedding", Vector(384), nullable=True))
    op.add_column(
        "match_scores",
        sa.Column(
            "passed_prefilter", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "match_scores",
        sa.Column("prefilter_reasons", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column("match_scores", sa.Column("similarity", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("match_scores", "similarity")
    op.drop_column("match_scores", "prefilter_reasons")
    op.drop_column("match_scores", "passed_prefilter")
    op.drop_column("user_profiles", "embedding")
