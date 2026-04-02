"""Add metadata columns to documents and document_chunks.

Revision ID: 001_add_metadata_columns
Revises: 
Create Date: 2026-04-01

添加 T24 RAG 元数据增强所需的列：
  documents:
    - doc_type     VARCHAR(64)  DEFAULT 'other'   (文档类型)
    - version      VARCHAR(64)  NULLABLE           (版本号)
    - effective_date DATE       NULLABLE           (生效日期)
    - expires_date   DATE       NULLABLE           (过期日期)
    - priority       INTEGER    DEFAULT 5          (优先级 1-10)
  document_chunks:
    - doc_type     VARCHAR(64)  DEFAULT 'other'   (冗余，加速过滤)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_add_metadata_columns"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # documents 表新增列
    # -----------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column("doc_type", sa.String(64), nullable=True, server_default="other"),
    )
    op.add_column(
        "documents",
        sa.Column("version", sa.String(64), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("effective_date", sa.Date, nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("expires_date", sa.Date, nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("priority", sa.Integer, nullable=False, server_default="5"),
    )

    # 为 doc_type 建索引，加速元数据过滤查询
    op.create_index(
        "ix_documents_doc_type",
        "documents",
        ["doc_type"],
    )

    # -----------------------------------------------------------------------
    # document_chunks 表新增列（冗余字段，避免每次 JOIN）
    # -----------------------------------------------------------------------
    op.add_column(
        "document_chunks",
        sa.Column("doc_type", sa.String(64), nullable=True, server_default="other"),
    )
    op.create_index(
        "ix_document_chunks_doc_type",
        "document_chunks",
        ["doc_type"],
    )


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 回滚：删除新增列（顺序与 upgrade 相反）
    # -----------------------------------------------------------------------
    op.drop_index("ix_document_chunks_doc_type", table_name="document_chunks")
    op.drop_column("document_chunks", "doc_type")

    op.drop_index("ix_documents_doc_type", table_name="documents")
    op.drop_column("documents", "priority")
    op.drop_column("documents", "expires_date")
    op.drop_column("documents", "effective_date")
    op.drop_column("documents", "version")
    op.drop_column("documents", "doc_type")
