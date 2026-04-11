"""add phase4 tables

Revision ID: 004_add_phase4
Revises: 003_merge
Create Date: 2026-04-09

"""

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, ForeignKeyConstraint, Integer, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "004_add_phase4"
down_revision = "003_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        Column("conversation_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agent_runs",
        Column("is_chat_mode", Boolean(), nullable=True, server_default=text("false")),
    )
    op.add_column(
        "products",
        Column("brand_analytics_keywords", JSON(), nullable=True),
    )

    op.create_table(
        "conversations",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("user_id", String(256), nullable=False),
        Column("agent_type", String(128), nullable=False),
        Column("title", String(512), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        Column("updated_at", DateTime(timezone=True), nullable=True),
        Column("metadata_json", JSON(), nullable=True),
    )

    op.create_table(
        "chat_messages",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("conversation_id", UUID(as_uuid=True), nullable=False),
        Column("role", String(32), nullable=False),
        Column("content", Text(), nullable=False),
        Column("metadata_json", JSON(), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    op.create_table(
        "keyword_libraries",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("product_id", UUID(as_uuid=True), nullable=True),
        Column("keyword", String(512), nullable=False),
        Column("search_volume", Integer(), nullable=True),
        Column("relevance_tier", String(32), nullable=True),
        Column("source", String(64), nullable=False),
        Column("category", String(128), nullable=True),
        Column("monthly_rank", Integer(), nullable=True),
        Column("last_updated", DateTime(timezone=True), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        ForeignKeyConstraint(["product_id"], ["products.id"]),
    )
    op.create_index("ix_keyword_libraries_keyword", "keyword_libraries", ["keyword"])

    op.create_table(
        "ad_simulations",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("campaign_id", String(256), nullable=True),
        Column("simulation_params", JSON(), nullable=True),
        Column("results", JSON(), nullable=True),
        Column("created_by", String(256), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    op.create_table(
        "ad_optimization_logs",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("campaign_id", String(256), nullable=True),
        Column("action_type", String(128), nullable=False),
        Column("old_value", JSON(), nullable=True),
        Column("new_value", JSON(), nullable=True),
        Column("reason", Text(), nullable=True),
        Column("applied", Boolean(), nullable=False, server_default=text("false")),
        Column("approved_by", String(256), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    op.create_table(
        "kb_review_queue",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("content", Text(), nullable=False),
        Column("source", String(256), nullable=True),
        Column("agent_type", String(128), nullable=True),
        Column("summary", Text(), nullable=True),
        Column("status", String(32), nullable=False, server_default="pending"),
        Column("reviewer_id", String(256), nullable=True),
        Column("review_comment", Text(), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        Column("reviewed_at", DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "auditor_logs",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("agent_type", String(128), nullable=False),
        Column("agent_run_id", UUID(as_uuid=True), nullable=True),
        Column("severity", String(32), nullable=False),
        Column("finding", Text(), nullable=False),
        Column("auto_action", String(32), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
    )


def downgrade() -> None:
    op.drop_table("auditor_logs")
    op.drop_table("kb_review_queue")
    op.drop_table("ad_optimization_logs")
    op.drop_table("ad_simulations")
    op.drop_index("ix_keyword_libraries_keyword", table_name="keyword_libraries")
    op.drop_table("keyword_libraries")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("conversations")

    op.drop_column("products", "brand_analytics_keywords")
    op.drop_column("agent_runs", "is_chat_mode")
    op.drop_column("agent_runs", "conversation_id")
