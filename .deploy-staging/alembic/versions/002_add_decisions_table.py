"""Add decisions table for T25 decision state machine.

Revision ID: 002_add_decisions_table
Revises: 
Create Date: 2026-04-01

创建 decisions 表，支持可追踪、可回滚的决策状态机：

  decisions 表字段：
    - id               UUID PK
    - decision_type    VARCHAR(128)   决策类型（pricing, advertising, listing 等）
    - agent_id         VARCHAR(256)   发起决策的 Agent
    - payload          JSON           决策内容
    - status           VARCHAR(64)    当前状态（DRAFT/PENDING_APPROVAL/APPROVED/...）
    - created_at       TIMESTAMP      创建时间
    - updated_at       TIMESTAMP      最后更新时间
    - approved_by      VARCHAR(256)   审批人（nullable）
    - approved_at      TIMESTAMP      审批时间（nullable）
    - executed_at      TIMESTAMP      执行时间（nullable）
    - result           JSON           执行结果（nullable）
    - error_message    TEXT           错误信息（nullable）
    - rollback_payload JSON           回滚数据（nullable）

状态流转：
    DRAFT → PENDING_APPROVAL → APPROVED → EXECUTING → SUCCEEDED
                                                    ↘ FAILED → ROLLED_BACK
                            ↘ REJECTED
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_add_decisions_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True) if _is_postgres() else sa.String(36),
            primary_key=True,
        ),
        sa.Column("decision_type", sa.String(128), nullable=False),
        sa.Column("agent_id", sa.String(256), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="DRAFT"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_by", sa.String(256), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("rollback_payload", sa.JSON(), nullable=True),
    )

    # 高频查询索引
    op.create_index("ix_decisions_decision_type", "decisions", ["decision_type"])
    op.create_index("ix_decisions_agent_id", "decisions", ["agent_id"])
    op.create_index("ix_decisions_status", "decisions", ["status"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_decisions_created_at", table_name="decisions")
    op.drop_index("ix_decisions_status", table_name="decisions")
    op.drop_index("ix_decisions_agent_id", table_name="decisions")
    op.drop_index("ix_decisions_decision_type", table_name="decisions")
    op.drop_table("decisions")


def _is_postgres() -> bool:
    """判断当前数据库是否为 PostgreSQL（用于选择 UUID 列类型）。"""
    try:
        from alembic import context
        url = context.config.get_main_option("sqlalchemy.url", "")
        return url.startswith("postgresql")
    except Exception:  # pragma: no cover
        return False
