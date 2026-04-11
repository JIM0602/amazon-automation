"""决策数据库操作层 (Repository)。

提供对 decisions 表的 CRUD 操作，遵循现有项目的 db_session 风格。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models import Decision
from src.decisions.models import DecisionCreate, DecisionStatus

logger = logging.getLogger(__name__)


class DecisionRepository:
    """decisions 表的数据库操作封装。

    所有方法接受一个已打开的 SQLAlchemy Session，由调用方负责事务管理。
    """

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------

    def create(self, data: DecisionCreate) -> Decision:
        """插入一条新决策记录（状态为 DRAFT）。

        Args:
            data: 创建决策所需的数据。

        Returns:
            新建的 Decision ORM 对象。
        """
        now = datetime.now(timezone.utc)
        decision = Decision(
            id=uuid.uuid4(),
            decision_type=data.decision_type,
            agent_id=data.agent_id,
            payload=data.payload,
            status=DecisionStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
            rollback_payload=data.rollback_payload,
        )
        self.session.add(decision)
        self.session.flush()  # 获取 DB 生成的值，不提交事务
        return decision

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_by_id(self, decision_id: uuid.UUID) -> Optional[Decision]:
        """按 ID 查询单条决策记录。"""
        return (
            self.session.query(Decision)
            .filter(Decision.id == decision_id)
            .first()
        )

    def get_history(
        self,
        decision_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[DecisionStatus] = None,
        limit: int = 50,
    ) -> List[Decision]:
        """查询决策历史，支持多维度过滤。

        Args:
            decision_type: 按决策类型过滤（可选）。
            agent_id:      按 Agent ID 过滤（可选）。
            status:        按状态过滤（可选）。
            limit:         返回最大条数，默认 50。

        Returns:
            符合条件的决策列表，按创建时间倒序排列。
        """
        query = self.session.query(Decision)

        if decision_type is not None:
            query = query.filter(Decision.decision_type == decision_type)
        if agent_id is not None:
            query = query.filter(Decision.agent_id == agent_id)
        if status is not None:
            query = query.filter(Decision.status == status.value)

        return query.order_by(Decision.created_at.desc()).limit(limit).all()

    # ------------------------------------------------------------------
    # 状态更新（内部辅助）
    # ------------------------------------------------------------------

    def _update_status(
        self,
        decision: Decision,
        new_status: DecisionStatus,
        **extra_fields,
    ) -> Decision:
        """更新决策状态及附加字段，并刷新 updated_at。"""
        decision.status = new_status.value
        decision.updated_at = datetime.now(timezone.utc)
        for field, value in extra_fields.items():
            setattr(decision, field, value)
        self.session.flush()
        return decision
