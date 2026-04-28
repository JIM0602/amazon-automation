"""add phase4 tables

Revision ID: 004_add_phase4
Revises: 003_merge
Create Date: 2026-04-09
"""

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKeyConstraint, Integer, JSON, String, Text, inspect, text
from sqlalchemy.dialects import postgresql


revision = "004_add_phase4"
down_revision = "003_merge"
branch_labels = None
depends_on = None


def _uuid_type():
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return String(36)


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def _ensure_core_tables() -> None:
    if not _has_table("products"):
        op.create_table(
            "products",
            Column("id", _uuid_type(), primary_key=True),
            Column("sku", String(128), nullable=False, unique=True),
            Column("name", String(512), nullable=False),
            Column("asin", String(16), nullable=True),
            Column("keywords", JSON, nullable=True),
            Column("status", String(64), nullable=False, server_default="active"),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_products_sku", "products", ["sku"])
        op.create_index("ix_products_asin", "products", ["asin"])

    if not _has_table("agent_runs"):
        op.create_table(
            "agent_runs",
            Column("id", _uuid_type(), primary_key=True),
            Column("agent_type", String(128), nullable=False),
            Column("status", String(64), nullable=False, server_default="running"),
            Column("input_summary", Text, nullable=True),
            Column("output_summary", Text, nullable=True),
            Column("cost_usd", Float, nullable=True),
            Column("started_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
            Column("finished_at", DateTime(timezone=True), nullable=True),
            Column("result_json", JSON, nullable=True),
        )
        op.create_index("ix_agent_runs_agent_type", "agent_runs", ["agent_type"])


def upgrade() -> None:
    _ensure_core_tables()

    if not _has_column("agent_runs", "conversation_id"):
        op.add_column("agent_runs", Column("conversation_id", _uuid_type(), nullable=True))
    if not _has_column("agent_runs", "is_chat_mode"):
        op.add_column("agent_runs", Column("is_chat_mode", Boolean(), nullable=True, server_default=text("false")))
    if not _has_column("products", "brand_analytics_keywords"):
        op.add_column("products", Column("brand_analytics_keywords", JSON(), nullable=True))

    if not _has_table("conversations"):
        op.create_table(
            "conversations",
            Column("id", _uuid_type(), primary_key=True),
            Column("user_id", String(256), nullable=False),
            Column("agent_type", String(128), nullable=False),
            Column("title", String(512), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
            Column("updated_at", DateTime(timezone=True), nullable=True),
            Column("metadata_json", JSON(), nullable=True),
        )

    if not _has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            Column("id", _uuid_type(), primary_key=True),
            Column("conversation_id", _uuid_type(), nullable=False),
            Column("role", String(32), nullable=False),
            Column("content", Text(), nullable=False),
            Column("metadata_json", JSON(), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
            ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        )
    if not _has_index("chat_messages", "ix_chat_messages_conversation_id"):
        op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    if not _has_table("keyword_libraries"):
        op.create_table(
            "keyword_libraries",
            Column("id", _uuid_type(), primary_key=True),
            Column("product_id", _uuid_type(), nullable=True),
            Column("keyword", String(512), nullable=False),
            Column("search_volume", Integer(), nullable=True),
            Column("relevance_tier", String(32), nullable=True),
            Column("source", String(64), nullable=False),
            Column("category", String(128), nullable=True),
            Column("monthly_rank", Integer(), nullable=True),
            Column("last_updated", DateTime(timezone=True), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
            ForeignKeyConstraint(["product_id"], ["products.id"]),
        )
    if not _has_index("keyword_libraries", "ix_keyword_libraries_keyword"):
        op.create_index("ix_keyword_libraries_keyword", "keyword_libraries", ["keyword"])

    if not _has_table("ad_simulations"):
        op.create_table(
            "ad_simulations",
            Column("id", _uuid_type(), primary_key=True),
            Column("campaign_id", String(256), nullable=True),
            Column("simulation_params", JSON(), nullable=True),
            Column("results", JSON(), nullable=True),
            Column("created_by", String(256), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        )

    if not _has_table("ad_optimization_logs"):
        op.create_table(
            "ad_optimization_logs",
            Column("id", _uuid_type(), primary_key=True),
            Column("campaign_id", String(256), nullable=True),
            Column("action_type", String(128), nullable=False),
            Column("old_value", JSON(), nullable=True),
            Column("new_value", JSON(), nullable=True),
            Column("reason", Text(), nullable=True),
            Column("applied", Boolean(), nullable=False, server_default=text("false")),
            Column("approved_by", String(256), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        )

    if not _has_table("kb_review_queue"):
        op.create_table(
            "kb_review_queue",
            Column("id", _uuid_type(), primary_key=True),
            Column("content", Text(), nullable=False),
            Column("source", String(256), nullable=True),
            Column("agent_type", String(128), nullable=True),
            Column("summary", Text(), nullable=True),
            Column("status", String(32), nullable=False, server_default="pending"),
            Column("reviewer_id", String(256), nullable=True),
            Column("review_comment", Text(), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
            Column("reviewed_at", DateTime(timezone=True), nullable=True),
        )

    if not _has_table("auditor_logs"):
        op.create_table(
            "auditor_logs",
            Column("id", _uuid_type(), primary_key=True),
            Column("agent_type", String(128), nullable=False),
            Column("agent_run_id", _uuid_type(), nullable=True),
            Column("severity", String(32), nullable=False),
            Column("finding", Text(), nullable=False),
            Column("auto_action", String(32), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
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

    if _has_column("products", "brand_analytics_keywords"):
        op.drop_column("products", "brand_analytics_keywords")
    if _has_column("agent_runs", "is_chat_mode"):
        op.drop_column("agent_runs", "is_chat_mode")
    if _has_column("agent_runs", "conversation_id"):
        op.drop_column("agent_runs", "conversation_id")
