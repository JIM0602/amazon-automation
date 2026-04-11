"""决策状态机核心逻辑。

实现所有状态转换方法，并在每次状态变更时记录审计日志。

设计原则：
- 状态转换前验证合法性（非法转换抛出 DecisionStatusTransitionError）
- 每次状态变更调用 log_action 写入 audit_logs
- 执行 (execute) 需要传入实际执行函数，状态机负责状态管理，不直接执行业务逻辑
- 不自动执行决策（必须经过人工审批后调用 execute）
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from src.db.models import Decision
from src.decisions.models import (
    DecisionCreate,
    DecisionNotFoundError,
    DecisionRead,
    DecisionStatus,
    DecisionStatusTransitionError,
    VALID_TRANSITIONS,
)
from src.decisions.repository import DecisionRepository
from src.utils.audit import log_action

logger = logging.getLogger(__name__)


class DecisionStateMachine:
    """决策状态机。

    每个实例绑定一个 SQLAlchemy Session，通过 DecisionRepository 操作数据库。

    Usage::

        from src.db.connection import db_session

        with db_session() as session:
            sm = DecisionStateMachine(session)
            decision = sm.create_decision(DecisionCreate(...))
            sm.submit_for_approval(decision.id)
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = DecisionRepository(session)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _get_or_raise(self, decision_id: uuid.UUID) -> Decision:
        """按 ID 获取决策，若不存在则抛出 DecisionNotFoundError。"""
        decision = self.repo.get_by_id(decision_id)
        if decision is None:
            raise DecisionNotFoundError(decision_id)
        return decision

    def _assert_transition(
        self,
        decision: Decision,
        to_status: DecisionStatus,
    ) -> None:
        """验证状态转换合法性，非法时抛出 DecisionStatusTransitionError。"""
        current = DecisionStatus(decision.status)
        allowed = VALID_TRANSITIONS.get(current, [])
        if to_status not in allowed:
            raise DecisionStatusTransitionError(current, to_status)

    def _audit(
        self,
        action: str,
        decision: Decision,
        actor: str,
        old_status: str,
        new_status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """写入审计日志（非阻塞）。"""
        pre_state = {
            "decision_id": str(decision.id),
            "status": old_status,
        }
        post_state: Dict[str, Any] = {
            "decision_id": str(decision.id),
            "status": new_status,
        }
        if extra:
            post_state.update(extra)
        log_action(
            action=action,
            actor=actor,
            pre_state=pre_state,
            post_state=post_state,
        )

    # ------------------------------------------------------------------
    # 公开方法：状态转换
    # ------------------------------------------------------------------

    def create_decision(self, data: DecisionCreate) -> DecisionRead:
        """创建新决策（初始状态为 DRAFT）。

        Args:
            data: 决策创建数据。

        Returns:
            新建决策的 DecisionRead 模型。
        """
        decision = self.repo.create(data)
        self.session.commit()

        log_action(
            action="decision.created",
            actor=f"agent:{data.agent_id}",
            post_state={
                "decision_id": str(decision.id),
                "decision_type": decision.decision_type,
                "status": decision.status,
            },
        )
        logger.info("决策已创建: id=%s type=%s", decision.id, decision.decision_type)
        return DecisionRead.model_validate(decision)

    def submit_for_approval(
        self,
        decision_id: uuid.UUID,
        actor: str = "system",
    ) -> DecisionRead:
        """提交决策至待审批（DRAFT → PENDING_APPROVAL）。

        Args:
            decision_id: 决策 ID。
            actor:       操作者标识（可选，默认 "system"）。

        Returns:
            更新后的 DecisionRead 模型。

        Raises:
            DecisionNotFoundError: 决策不存在。
            DecisionStatusTransitionError: 当前状态不允许转换。
        """
        decision = self._get_or_raise(decision_id)
        old_status = decision.status
        self._assert_transition(decision, DecisionStatus.PENDING_APPROVAL)

        self.repo._update_status(decision, DecisionStatus.PENDING_APPROVAL)
        self.session.commit()

        self._audit(
            "decision.submitted_for_approval",
            decision,
            actor,
            old_status,
            decision.status,
        )
        return DecisionRead.model_validate(decision)

    def approve(
        self,
        decision_id: uuid.UUID,
        approved_by: str,
    ) -> DecisionRead:
        """审批通过（PENDING_APPROVAL → APPROVED）。

        Args:
            decision_id: 决策 ID。
            approved_by: 审批人标识。

        Returns:
            更新后的 DecisionRead 模型。
        """
        decision = self._get_or_raise(decision_id)
        old_status = decision.status
        self._assert_transition(decision, DecisionStatus.APPROVED)

        now = datetime.now(timezone.utc)
        self.repo._update_status(
            decision,
            DecisionStatus.APPROVED,
            approved_by=approved_by,
            approved_at=now,
        )
        self.session.commit()

        self._audit(
            "decision.approved",
            decision,
            approved_by,
            old_status,
            decision.status,
            extra={"approved_by": approved_by},
        )
        return DecisionRead.model_validate(decision)

    def reject(
        self,
        decision_id: uuid.UUID,
        approved_by: str,
        reason: Optional[str] = None,
    ) -> DecisionRead:
        """拒绝审批（PENDING_APPROVAL → REJECTED）。

        Args:
            decision_id: 决策 ID。
            approved_by: 审批人标识。
            reason:      拒绝原因（可选）。

        Returns:
            更新后的 DecisionRead 模型。
        """
        decision = self._get_or_raise(decision_id)
        old_status = decision.status
        self._assert_transition(decision, DecisionStatus.REJECTED)

        now = datetime.now(timezone.utc)
        self.repo._update_status(
            decision,
            DecisionStatus.REJECTED,
            approved_by=approved_by,
            approved_at=now,
            error_message=reason,
        )
        self.session.commit()

        self._audit(
            "decision.rejected",
            decision,
            approved_by,
            old_status,
            decision.status,
            extra={"approved_by": approved_by, "reason": reason},
        )
        return DecisionRead.model_validate(decision)

    def execute(
        self,
        decision_id: uuid.UUID,
        executor: Callable[..., Dict[str, Any]],
        actor: str = "system",
    ) -> DecisionRead:
        """执行已审批的决策（APPROVED → EXECUTING → SUCCEEDED/FAILED）。

        执行流程：
        1. 验证决策存在且处于 APPROVED 状态
        2. 转换为 EXECUTING
        3. 调用 executor 函数执行实际业务逻辑
        4. 成功 → SUCCEEDED，失败 → FAILED

        注意：不自动执行，必须由外部显式调用此方法（人工审批后触发）。

        Args:
            decision_id: 决策 ID。
            executor:    实际执行函数，接受 decision payload (dict)，返回 result (dict)。
            actor:       执行者标识（默认 "system"）。

        Returns:
            执行后的 DecisionRead 模型（状态为 SUCCEEDED 或 FAILED）。
        """
        decision = self._get_or_raise(decision_id)
        old_status = decision.status
        self._assert_transition(decision, DecisionStatus.EXECUTING)

        # APPROVED → EXECUTING
        self.repo._update_status(decision, DecisionStatus.EXECUTING)
        self.session.commit()
        self._audit("decision.executing", decision, actor, old_status, decision.status)

        # 执行业务逻辑
        try:
            result = executor(decision.payload)
            executed_at = datetime.now(timezone.utc)
            self.repo._update_status(
                decision,
                DecisionStatus.SUCCEEDED,
                executed_at=executed_at,
                result=result,
            )
            self.session.commit()
            self._audit(
                "decision.succeeded",
                decision,
                actor,
                DecisionStatus.EXECUTING.value,
                decision.status,
                extra={"result": result},
            )
            logger.info("决策执行成功: id=%s", decision.id)

        except Exception as exc:  # pylint: disable=broad-except
            error_message = str(exc)
            executed_at = datetime.now(timezone.utc)
            self.repo._update_status(
                decision,
                DecisionStatus.FAILED,
                executed_at=executed_at,
                error_message=error_message,
            )
            self.session.commit()
            self._audit(
                "decision.failed",
                decision,
                actor,
                DecisionStatus.EXECUTING.value,
                decision.status,
                extra={"error": error_message},
            )
            logger.error("决策执行失败: id=%s error=%s", decision.id, error_message)

        return DecisionRead.model_validate(decision)

    def rollback(
        self,
        decision_id: uuid.UUID,
        actor: str = "system",
    ) -> DecisionRead:
        """回滚失败的决策（FAILED → ROLLED_BACK）。

        注意：回滚只更新状态，实际回滚业务逻辑需调用方使用 rollback_payload 自行处理。

        Args:
            decision_id: 决策 ID。
            actor:       操作者标识（默认 "system"）。

        Returns:
            更新后的 DecisionRead 模型。
        """
        decision = self._get_or_raise(decision_id)
        old_status = decision.status
        self._assert_transition(decision, DecisionStatus.ROLLED_BACK)

        self.repo._update_status(decision, DecisionStatus.ROLLED_BACK)
        self.session.commit()

        self._audit(
            "decision.rolled_back",
            decision,
            actor,
            old_status,
            decision.status,
            extra={"rollback_payload": decision.rollback_payload},
        )
        return DecisionRead.model_validate(decision)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_decision_history(
        self,
        decision_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[DecisionStatus] = None,
        limit: int = 50,
    ) -> list[DecisionRead]:
        """查询决策历史记录。

        Args:
            decision_type: 按决策类型过滤（可选）。
            agent_id:      按 Agent ID 过滤（可选）。
            status:        按状态过滤（可选）。
            limit:         返回最大条数，默认 50。

        Returns:
            符合条件的 DecisionRead 列表（按创建时间倒序）。
        """
        decisions = self.repo.get_history(
            decision_type=decision_type,
            agent_id=agent_id,
            status=status,
            limit=limit,
        )
        return [DecisionRead.model_validate(d) for d in decisions]
