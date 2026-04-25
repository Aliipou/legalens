"""initial schema

Revision ID: 0001
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("old_document_hash", sa.String(64), nullable=False),
        sa.Column("new_document_hash", sa.String(64), nullable=False),
        sa.Column("total_clauses_old", sa.Integer, nullable=False),
        sa.Column("total_clauses_new", sa.Integer, nullable=False),
        sa.Column("added", sa.Integer, nullable=False),
        sa.Column("removed", sa.Integer, nullable=False),
        sa.Column("modified", sa.Integer, nullable=False),
        sa.Column("overall_risk", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="all-MiniLM-L6-v2"),
        sa.Column("processing_ms", sa.Float, nullable=True),
    )
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"])
    op.create_index("ix_analyses_overall_risk", "analyses", ["overall_risk"])


def downgrade() -> None:
    op.drop_table("analyses")
