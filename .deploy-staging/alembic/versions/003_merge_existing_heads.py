"""merge existing heads

Revision ID: 003_merge
Revises: 001_llm_cache, 001_add_metadata_columns, 002_add_decisions_table
Create Date: 2026-04-09

"""

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false

from alembic import op  # noqa: F401


# revision identifiers, used by Alembic.
revision = "003_merge"
down_revision = ("001_llm_cache", "001_add_metadata_columns", "002_add_decisions_table")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
