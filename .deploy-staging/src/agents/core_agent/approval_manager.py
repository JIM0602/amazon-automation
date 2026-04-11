"""核心管理 Agent — 高阶审批管理模块。

提供审批工作流的高阶管理功能：
- 状态机管理（PENDING → APPROVED/REJECTED → EXECUTING → COMPLETED/FAILED）
- 批量审批查询
- 执行结果回写
- 超时扫描调度

状态机：
  PENDING → APPROVED   （用户点击"同意"）
  PENDING → REJECTED   （用户点击"拒绝" 或 超时自动拒绝）
  APPROVED → EXECUTING （Agent 开始执行）
  EXECUTING → COMPLETED（执行成功）
  EXECUTING → FAILED   （执行失败）
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

# 模块顶部导入，确保 patch 可以覆盖
from src.db.connection import db_session
from src.db.models import ApprovalRequest

# 从 feishu.approval 导入底层函数
from src.feishu.approval import (
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_EXECUTING,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
    check_expired_approvals,
    create_approval_request,
    get_pending_approvals,
    handle_card_callback,
)

logger = logging.getLogger(__name__)

# 合法的状态转换图
_VALID_TRANSITIONS: dict[str, list[str]] = {
    STATUS_PENDING: [STATUS_APPROVED, STATUS_REJECTED],
    STATUS_APPROVED: [STATUS_EXECUTING],
    STATUS_REJECTED: [],          # 终态
    STATUS_EXECUTING: [STATUS_COMPLETED, STATUS_FAILED],
    STATUS_COMPLETED: [],          # 终态
    STATUS_FAILED: [],             # 终态
}


class ApprovalManager:
    """高阶审批管理器，封装审批工作流的完整生命周期。

    职责：
    - 创建审批请求（委托给 feishu.approval.create_approval_request）
    - 处理飞书卡片回调（委托给 feishu.approval.handle_card_callback）
    - 状态机转换（带合法性验证）
    - 标记执行中/完成/失败
    - 批量查询（待审批、执行中）
    - 超时扫描
    """

    AGENT_TYPE = "core_agent.approval_manager"

    def request_approval(
        self,
        action_type: str,
        description: str,
        impact: str,
        reason: str,
        risks: str,
        timeout_hours: float = 24.0,
        chat_id: Optional[str] = None,
    ) -> str:
        """创建审批请求并发送飞书卡片。

        Returns:
            approval_id（UUID 字符串）
        """
        return create_approval_request(
            action_type=action_type,
            description=description,
            impact=impact,
            reason=reason,
            risks=risks,
            timeout_hours=timeout_hours,
            chat_id=chat_id,
        )

    def process_callback(self, payload: dict) -> dict:
        """处理飞书卡片按钮回调。

        Returns:
            {"success": bool, "approval_id": str, "new_status": str, "message": str}
        """
        return handle_card_callback(payload)

    def get_pending(self) -> list:
        """获取所有 PENDING 状态的审批请求列表。"""
        return get_pending_approvals()

    def scan_expired(self) -> int:
        """扫描并自动拒绝超时审批。

        Returns:
            int: 自动拒绝的数量
        """
        return check_expired_approvals()

    def transition_status(
        self,
        approval_id: str,
        new_status: str,
        actor: str = "system",
        error_message: Optional[str] = None,
    ) -> dict:
        """执行审批状态机转换（带合法性验证）。

        Args:
            approval_id:   审批 UUID 字符串
            new_status:    目标状态
            actor:         操作者标识
            error_message: 当 new_status=FAILED 时可附带错误描述

        Returns:
            {"success": bool, "approval_id": str, "old_status": str,
             "new_status": str, "message": str}
        """
        try:
            with db_session() as session:
                approval = session.query(ApprovalRequest).filter(
                    ApprovalRequest.id == uuid.UUID(approval_id)
                ).first()

                if approval is None:
                    return {
                        "success": False,
                        "approval_id": approval_id,
                        "old_status": "",
                        "new_status": new_status,
                        "message": f"审批请求不存在: {approval_id}",
                    }

                old_status = approval.status
                allowed = _VALID_TRANSITIONS.get(old_status, [])

                if new_status not in allowed:
                    return {
                        "success": False,
                        "approval_id": approval_id,
                        "old_status": old_status,
                        "new_status": new_status,
                        "message": (
                            f"非法状态转换: {old_status} → {new_status}，"
                            f"允许的转换: {allowed}"
                        ),
                    }

                approval.status = new_status
                if new_status == STATUS_FAILED and error_message:
                    payload = approval.payload or {}
                    payload["error_message"] = error_message
                    approval.payload = payload

                session.commit()
                logger.info(
                    "审批状态转换: approval_id=%s %s→%s by=%s",
                    approval_id, old_status, new_status, actor,
                )

                # 写审计日志
                try:
                    from src.utils.audit import log_action
                    log_action(
                        action=f"approval_status_transition",
                        actor=actor,
                        pre_state={"approval_id": approval_id, "status": old_status},
                        post_state={"approval_id": approval_id, "status": new_status},
                    )
                except Exception as exc:
                    logger.error("状态转换审计日志写入失败: %s", exc)

                return {
                    "success": True,
                    "approval_id": approval_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "message": f"状态转换成功: {old_status} → {new_status}",
                }

        except Exception as exc:
            logger.error("审批状态转换失败: approval_id=%s error=%s", approval_id, exc)
            return {
                "success": False,
                "approval_id": approval_id,
                "old_status": "",
                "new_status": new_status,
                "message": f"状态转换失败: {exc}",
            }

    def mark_executing(self, approval_id: str, actor: str = "system") -> dict:
        """将已批准的审批标记为执行中（APPROVED → EXECUTING）。"""
        return self.transition_status(approval_id, STATUS_EXECUTING, actor=actor)

    def mark_completed(self, approval_id: str, actor: str = "system") -> dict:
        """将执行中的审批标记为已完成（EXECUTING → COMPLETED）。"""
        return self.transition_status(approval_id, STATUS_COMPLETED, actor=actor)

    def mark_failed(
        self, approval_id: str, error_message: str = "", actor: str = "system"
    ) -> dict:
        """将执行中的审批标记为失败（EXECUTING → FAILED）。"""
        return self.transition_status(
            approval_id, STATUS_FAILED, actor=actor, error_message=error_message
        )

    def get_approval_status(self, approval_id: str) -> Optional[dict]:
        """查询单条审批请求的当前状态。

        Returns:
            dict 或 None（不存在时）
        """
        try:
            with db_session() as session:
                approval = session.query(ApprovalRequest).filter(
                    ApprovalRequest.id == uuid.UUID(approval_id)
                ).first()

                if approval is None:
                    return None

                payload = approval.payload or {}
                return {
                    "approval_id": str(approval.id),
                    "action_type": approval.action_type,
                    "status": approval.status,
                    "approved_by": approval.approved_by,
                    "description": payload.get("description", ""),
                    "impact": payload.get("impact", ""),
                    "reason": payload.get("reason", ""),
                    "risks": payload.get("risks", ""),
                    "expires_at": payload.get("expires_at", ""),
                    "created_at": approval.created_at.isoformat() if approval.created_at else None,
                }
        except Exception as exc:
            logger.error("查询审批状态失败: approval_id=%s error=%s", approval_id, exc)
            return None


# 模块级单例（可选，允许测试直接实例化）
_manager_instance: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """返回全局 ApprovalManager 单例（懒加载）。"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ApprovalManager()
    return _manager_instance
