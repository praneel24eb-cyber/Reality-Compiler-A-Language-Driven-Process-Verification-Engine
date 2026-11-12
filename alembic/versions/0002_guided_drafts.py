"""Durable guided Q&A drafts with optimistic concurrency protection."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.create_table(
        "drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("drafts")
