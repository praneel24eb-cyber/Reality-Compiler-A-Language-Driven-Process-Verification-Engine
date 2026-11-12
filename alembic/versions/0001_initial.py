"""Initial immutable analysis and scenario snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
    )
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )
    op.create_index("ix_scenarios_analysis_id", "scenarios", ["analysis_id"])


def downgrade():
    op.drop_table("scenarios")
    op.drop_table("analyses")
