"""Add decisions table for T25 decision state machine.

Revision ID: 002_add_decisions_table
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "002_add_decisions_table"
down_revision = None
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    try:
        return op.get_bind().dialect.name == "postgresql"
    except Exception:  # pragma: no cover
        return False


def _uuid_type():
    return sa.dialects.postgresql.UUID(as_uuid=True) if _is_postgres() else sa.String(36)


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("decisions"):
        op.create_table(
            "decisions",
            sa.Column("id", _uuid_type(), primary_key=True),
            sa.Column("decision_type", sa.String(128), nullable=False),
            sa.Column("agent_id", sa.String(256), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(64), nullable=False, server_default="DRAFT"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("approved_by", sa.String(256), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("rollback_payload", sa.JSON(), nullable=True),
        )

    indexes = _index_names("decisions")
    if "ix_decisions_decision_type" not in indexes:
        op.create_index("ix_decisions_decision_type", "decisions", ["decision_type"])
    if "ix_decisions_agent_id" not in indexes:
        op.create_index("ix_decisions_agent_id", "decisions", ["agent_id"])
    if "ix_decisions_status" not in indexes:
        op.create_index("ix_decisions_status", "decisions", ["status"])
    if "ix_decisions_created_at" not in indexes:
        op.create_index("ix_decisions_created_at", "decisions", ["created_at"])


def downgrade() -> None:
    if _has_table("decisions"):
        indexes = _index_names("decisions")
        for index_name in ["ix_decisions_created_at", "ix_decisions_status", "ix_decisions_agent_id", "ix_decisions_decision_type"]:
            if index_name in indexes:
                op.drop_index(index_name, table_name="decisions")
        op.drop_table("decisions")
