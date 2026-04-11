"""add agent_configs table

Revision ID: 006_add_agent_configs
Revises: 005_add_users_table
Create Date: 2026-04-10

"""

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false

from alembic import op
from sqlalchemy import Boolean, Column, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = "006_add_agent_configs"
down_revision = "005_add_users_table"
branch_labels = None
depends_on = None


# 13 agents from AGENT_REGISTRY (src/services/chat.py) with Chinese display names
INITIAL_AGENT_CONFIGS = [
    {"agent_type": "core_management",  "display_name_cn": "AI主管",       "sort_order": 0},
    {"agent_type": "selection",        "display_name_cn": "选品Agent",    "sort_order": 1},
    {"agent_type": "keyword_library",  "display_name_cn": "关键词Agent",  "sort_order": 2},
    {"agent_type": "listing",          "display_name_cn": "Listing文案",  "sort_order": 3},
    {"agent_type": "product_listing",  "display_name_cn": "产品Listing",  "sort_order": 4},
    {"agent_type": "ad_monitor",       "display_name_cn": "广告监控",     "sort_order": 5},
    {"agent_type": "brand_planning",   "display_name_cn": "品牌规划",     "sort_order": 6},
    {"agent_type": "inventory",        "display_name_cn": "供应链",       "sort_order": 7},
    {"agent_type": "competitor",       "display_name_cn": "市场分析",     "sort_order": 8},
    {"agent_type": "persona",          "display_name_cn": "用户画像",     "sort_order": 9},
    {"agent_type": "whitepaper",       "display_name_cn": "白皮书",       "sort_order": 10},
    {"agent_type": "image_generation", "display_name_cn": "图片生成",     "sort_order": 11},
    {"agent_type": "auditor",          "display_name_cn": "审计Agent",    "sort_order": 12},
]


def upgrade() -> None:
    op.create_table(
        "agent_configs",
        Column("agent_type", String(64), primary_key=True),
        Column("display_name_cn", String(128), nullable=False),
        Column("description", Text, nullable=True),
        Column("is_active", Boolean(), nullable=False, server_default=text("true")),
        Column("visible_roles", JSON, nullable=True),
        Column("sort_order", Integer, nullable=False, server_default=text("0")),
    )

    conn = op.get_bind()
    for cfg in INITIAL_AGENT_CONFIGS:
        conn.execute(
            text(
                """
                INSERT INTO agent_configs (agent_type, display_name_cn, is_active, sort_order)
                VALUES (:agent_type, :display_name_cn, true, :sort_order)
                """
            ),
            cfg,
        )


def downgrade() -> None:
    op.drop_table("agent_configs")
