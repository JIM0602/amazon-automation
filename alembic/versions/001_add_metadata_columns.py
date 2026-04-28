"""Add metadata columns to documents and document_chunks.

Revision ID: 001_add_metadata_columns
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "001_add_metadata_columns"
down_revision = None
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("documents") or not inspector.has_table("document_chunks"):
        # Some early deployments created the core KB tables outside Alembic.
        # Fresh Phase-1 installs do not need KB tables, so this revision is a no-op there.
        return

    document_columns = _column_names("documents")
    if "doc_type" not in document_columns:
        op.add_column("documents", sa.Column("doc_type", sa.String(64), nullable=True, server_default="other"))
    if "version" not in document_columns:
        op.add_column("documents", sa.Column("version", sa.String(64), nullable=True))
    if "effective_date" not in document_columns:
        op.add_column("documents", sa.Column("effective_date", sa.Date, nullable=True))
    if "expires_date" not in document_columns:
        op.add_column("documents", sa.Column("expires_date", sa.Date, nullable=True))
    if "priority" not in document_columns:
        op.add_column("documents", sa.Column("priority", sa.Integer, nullable=False, server_default="5"))

    if "ix_documents_doc_type" not in _index_names("documents"):
        op.create_index("ix_documents_doc_type", "documents", ["doc_type"])

    chunk_columns = _column_names("document_chunks")
    if "doc_type" not in chunk_columns:
        op.add_column("document_chunks", sa.Column("doc_type", sa.String(64), nullable=True, server_default="other"))
    if "ix_document_chunks_doc_type" not in _index_names("document_chunks"):
        op.create_index("ix_document_chunks_doc_type", "document_chunks", ["doc_type"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("document_chunks"):
        if "ix_document_chunks_doc_type" in _index_names("document_chunks"):
            op.drop_index("ix_document_chunks_doc_type", table_name="document_chunks")
        if "doc_type" in _column_names("document_chunks"):
            op.drop_column("document_chunks", "doc_type")

    if inspector.has_table("documents"):
        if "ix_documents_doc_type" in _index_names("documents"):
            op.drop_index("ix_documents_doc_type", table_name="documents")
        for column_name in ["priority", "expires_date", "effective_date", "version", "doc_type"]:
            if column_name in _column_names("documents"):
                op.drop_column("documents", column_name)
