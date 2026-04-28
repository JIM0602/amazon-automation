"""add llm_cache table

Revision ID: 001_llm_cache
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "001_llm_cache"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("llm_cache"):
        op.create_table(
            "llm_cache",
            sa.Column("cache_key", sa.String(64), primary_key=True),
            sa.Column("prompt_hash", sa.String(64), nullable=False),
            sa.Column("response_json", sa.JSON(), nullable=False),
            sa.Column("model", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        )

    indexes = _index_names("llm_cache")
    if "ix_llm_cache_expires_at" not in indexes:
        op.create_index("ix_llm_cache_expires_at", "llm_cache", ["expires_at"])
    if "ix_llm_cache_model" not in indexes:
        op.create_index("ix_llm_cache_model", "llm_cache", ["model"])
    if "ix_llm_cache_prompt_hash" not in indexes:
        op.create_index("ix_llm_cache_prompt_hash", "llm_cache", ["prompt_hash"])


def downgrade() -> None:
    if _has_table("llm_cache"):
        indexes = _index_names("llm_cache")
        if "ix_llm_cache_prompt_hash" in indexes:
            op.drop_index("ix_llm_cache_prompt_hash", table_name="llm_cache")
        if "ix_llm_cache_model" in indexes:
            op.drop_index("ix_llm_cache_model", table_name="llm_cache")
        if "ix_llm_cache_expires_at" in indexes:
            op.drop_index("ix_llm_cache_expires_at", table_name="llm_cache")
        op.drop_table("llm_cache")
