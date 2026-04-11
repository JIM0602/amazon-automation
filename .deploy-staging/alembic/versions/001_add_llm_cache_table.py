"""add llm_cache table

Revision ID: 001_llm_cache
Revises: 
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_llm_cache'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_cache',
        sa.Column('cache_key', sa.String(64), primary_key=True),
        sa.Column('prompt_hash', sa.String(64), nullable=False, index=True),
        sa.Column('response_json', sa.JSON(), nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
    )
    # 为高频查询创建索引
    op.create_index('ix_llm_cache_expires_at', 'llm_cache', ['expires_at'])
    op.create_index('ix_llm_cache_model', 'llm_cache', ['model'])
    op.create_index('ix_llm_cache_prompt_hash', 'llm_cache', ['prompt_hash'])


def downgrade() -> None:
    op.drop_index('ix_llm_cache_prompt_hash', table_name='llm_cache')
    op.drop_index('ix_llm_cache_model', table_name='llm_cache')
    op.drop_index('ix_llm_cache_expires_at', table_name='llm_cache')
    op.drop_table('llm_cache')
