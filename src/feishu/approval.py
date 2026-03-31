"""飞书审批模块：审批卡片发送 + 回调处理 + 状态机管理。

设计原则：
- 模块顶部导入所有需要被 patch 的对象（db_session, get_bot 等）
- 所有 DB 操作使用 try/except，失败不阻塞主流程
- 所有审批操作写审计日志
- 超时检查：expires_at 存储在 payload JSON 中
"""
from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

# 模块顶部导入，确保 patch 可以覆盖
from src.db.connection import db_session
from src.db.models import AgentRun, ApprovalRequest

try:
    from src.feishu.bot_handler import get_bot
except ImportError:  # pragma: no cover
    get_bot = None  # type: ignore[assignment]

try:
    from src.config import settings
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# 审批状态常量
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXECUTING = "executing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# 默认超时（小时）
DEFAULT_TIMEOUT_HOURS = 24


def _get_chat_id() -> str:
    """从 settings 读取飞书群 chat_id，若未配置则返回空字符串。"""
    if settings is None:
        return ""
    return getattr(settings, "FEISHU_CHAT_ID", "") or ""


def _build_approval_card(
    approval_id: str,
    action_type: str,
    description: str,
    impact: str,
    reason: str,
    risks: str,
) -> dict:
    """构建飞书交互审批卡片 JSON。"""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"审批请求 — {action_type}"},
            "template": "orange",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**描述：** {description}",
                },
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**影响范围：** {impact}",
                },
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**操作原因：** {reason}",
                },
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**潜在风险：** {risks}",
                },
            },
            {"tag": "hr"},
        ],
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "同意"},
                "type": "primary",
                "value": {"action": "approve", "approval_id": approval_id},
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "拒绝"},
                "type": "danger",
                "value": {"action": "reject", "approval_id": approval_id},
            },
        ],
    }


def create_approval_request(
    action_type: str,
    description: str,
    impact: str,
    reason: str,
    risks: str,
    timeout_hours: float = DEFAULT_TIMEOUT_HOURS,
    chat_id: Optional[str] = None,
) -> str:
    """创建审批请求，发送飞书交互卡片，返回 approval_id（UUID str）。

    流程：
    1. 生成 approval_id
    2. 计算 expires_at
    3. 写入 DB（创建 AgentRun + ApprovalRequest）
    4. 发送飞书审批卡片到群
    5. 写审计日志

    Args:
        action_type: 操作类型，如 "selection_list", "ad_budget"
        description: 操作描述
        impact:      影响范围
        reason:      操作原因
        risks:       潜在风险
        timeout_hours: 超时小时数（默认 24）
        chat_id:     目标飞书群 ID（None 时从 settings 读取）

    Returns:
        approval_id（UUID 字符串）
    """
    approval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=timeout_hours)).isoformat()

    # 构造 payload
    payload_data = {
        "description": description,
        "impact": impact,
        "reason": reason,
        "risks": risks,
        "expires_at": expires_at,
    }

    # 写入 DB
    try:
        with db_session() as session:
            # 先创建 AgentRun 记录（approval_requests.agent_run_id NOT NULL）
            agent_run = AgentRun(
                agent_type="core_agent.approval",
                status="running",
                input_summary=f"approval_request:{action_type}",
            )
            session.add(agent_run)
            session.flush()  # 获取 agent_run.id

            approval = ApprovalRequest(
                id=uuid.UUID(approval_id),
                agent_run_id=agent_run.id,
                action_type=action_type,
                payload=payload_data,
                status=STATUS_PENDING,
            )
            session.add(approval)
            session.commit()
            logger.info("审批请求已写入 DB: approval_id=%s type=%s", approval_id, action_type)
    except Exception as exc:
        logger.error("审批请求 DB 写入失败（继续发卡片）: %s", exc)

    # 发送飞书审批卡片
    target_chat_id = chat_id or _get_chat_id()
    if target_chat_id:
        card = _build_approval_card(
            approval_id=approval_id,
            action_type=action_type,
            description=description,
            impact=impact,
            reason=reason,
            risks=risks,
        )
        try:
            bot = get_bot()
            bot.send_card_message(target_chat_id, card)
            logger.info("审批卡片已发送: approval_id=%s chat_id=%s", approval_id, target_chat_id)
        except Exception as exc:
            logger.error("审批卡片发送失败: approval_id=%s error=%s", approval_id, exc)
    else:
        logger.warning("未配置 FEISHU_CHAT_ID，跳过发送审批卡片")

    # 写审计日志（函数内导入，避免循环依赖）
    try:
        from src.utils.audit import log_action
        log_action(
            action="approval_request_created",
            actor="system",
            pre_state=None,
            post_state={
                "approval_id": approval_id,
                "action_type": action_type,
                "status": STATUS_PENDING,
                "expires_at": expires_at,
            },
        )
    except Exception as exc:
        logger.error("审批审计日志写入失败: %s", exc)

    return approval_id


def handle_card_callback(payload: dict) -> dict:
    """处理飞书卡片按钮回调，更新审批状态。

    飞书回调格式：
    {
        "type": "card.action.trigger",
        "action": {
            "value": {"action": "approve"/"reject", "approval_id": "uuid"},
            "tag": "button"
        },
        "operator": {"open_id": "ou_xxx"}
    }

    Returns:
        dict: {"success": bool, "approval_id": str, "new_status": str, "message": str}
    """
    try:
        action_value = payload.get("action", {}).get("value", {})
        action = action_value.get("action", "")
        approval_id = action_value.get("approval_id", "")
        operator_id = payload.get("operator", {}).get("open_id", "system")

        if not action or not approval_id:
            return {
                "success": False,
                "message": "缺少 action 或 approval_id",
                "approval_id": approval_id,
                "new_status": "",
            }

        if action not in ("approve", "reject"):
            return {
                "success": False,
                "message": f"未知 action: {action}",
                "approval_id": approval_id,
                "new_status": "",
            }

        new_status = STATUS_APPROVED if action == "approve" else STATUS_REJECTED

        # 更新 DB
        updated = False
        try:
            with db_session() as session:
                approval = session.query(ApprovalRequest).filter(
                    ApprovalRequest.id == uuid.UUID(approval_id)
                ).first()

                if approval is None:
                    return {
                        "success": False,
                        "message": f"审批请求不存在: {approval_id}",
                        "approval_id": approval_id,
                        "new_status": "",
                    }

                if approval.status != STATUS_PENDING:
                    return {
                        "success": False,
                        "message": f"审批请求已处理（当前状态: {approval.status}）",
                        "approval_id": approval_id,
                        "new_status": approval.status,
                    }

                old_status = approval.status
                approval.status = new_status
                approval.approved_by = operator_id
                session.commit()
                updated = True
                logger.info(
                    "审批状态已更新: approval_id=%s %s→%s by=%s",
                    approval_id, old_status, new_status, operator_id,
                )
        except Exception as exc:
            logger.error("审批 DB 更新失败: approval_id=%s error=%s", approval_id, exc)
            return {
                "success": False,
                "message": f"DB 更新失败: {exc}",
                "approval_id": approval_id,
                "new_status": "",
            }

        # 写审计日志
        if updated:
            try:
                from src.utils.audit import log_action
                log_action(
                    action=f"approval_{action}d",
                    actor=f"user:{operator_id}",
                    pre_state={"approval_id": approval_id, "status": STATUS_PENDING},
                    post_state={"approval_id": approval_id, "status": new_status, "approved_by": operator_id},
                )
            except Exception as exc:
                logger.error("审批回调审计日志写入失败: %s", exc)

        return {
            "success": True,
            "approval_id": approval_id,
            "new_status": new_status,
            "message": f"审批{'通过' if action == 'approve' else '拒绝'}成功",
        }

    except Exception as exc:
        logger.error("处理卡片回调异常: %s", exc)
        return {
            "success": False,
            "message": f"处理回调异常: {exc}",
            "approval_id": "",
            "new_status": "",
        }


def get_pending_approvals() -> list:
    """获取所有 PENDING 状态的审批请求列表。

    Returns:
        list[dict]: 每条审批的字典表示
    """
    try:
        with db_session() as session:
            approvals = (
                session.query(ApprovalRequest)
                .filter(ApprovalRequest.status == STATUS_PENDING)
                .order_by(ApprovalRequest.created_at.desc())
                .all()
            )
            result = []
            for ap in approvals:
                payload = ap.payload or {}
                result.append({
                    "approval_id": str(ap.id),
                    "action_type": ap.action_type,
                    "status": ap.status,
                    "description": payload.get("description", ""),
                    "impact": payload.get("impact", ""),
                    "reason": payload.get("reason", ""),
                    "risks": payload.get("risks", ""),
                    "expires_at": payload.get("expires_at", ""),
                    "created_at": ap.created_at.isoformat() if ap.created_at else None,
                })
            return result
    except Exception as exc:
        logger.error("获取待审批列表失败: %s", exc)
        return []


def check_expired_approvals() -> int:
    """检查超时审批，自动设置为 REJECTED。

    比较当前时间与 payload.expires_at，超时则自动拒绝。

    Returns:
        int: 自动拒绝的审批数量
    """
    now = datetime.now(timezone.utc)
    rejected_count = 0

    try:
        with db_session() as session:
            pending_approvals = (
                session.query(ApprovalRequest)
                .filter(ApprovalRequest.status == STATUS_PENDING)
                .all()
            )

            for approval in pending_approvals:
                payload = approval.payload or {}
                expires_at_str = payload.get("expires_at", "")
                if not expires_at_str:
                    continue

                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    # 确保 timezone-aware 比较
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if now > expires_at:
                        approval_id = str(approval.id)
                        approval.status = STATUS_REJECTED
                        approval.approved_by = "system:timeout"
                        rejected_count += 1
                        logger.info("审批超时自动拒绝: approval_id=%s", approval_id)

                        # 写审计日志
                        try:
                            from src.utils.audit import log_action
                            log_action(
                                action="approval_timeout_rejected",
                                actor="system",
                                pre_state={"approval_id": approval_id, "status": STATUS_PENDING},
                                post_state={
                                    "approval_id": approval_id,
                                    "status": STATUS_REJECTED,
                                    "reason": "timeout",
                                    "expires_at": expires_at_str,
                                },
                            )
                        except Exception as exc:
                            logger.error("超时拒绝审计日志写入失败: %s", exc)

                except (ValueError, TypeError) as exc:
                    logger.warning("解析 expires_at 失败: %s error=%s", expires_at_str, exc)
                    continue

            if rejected_count > 0:
                session.commit()

    except Exception as exc:
        logger.error("检查超时审批失败: %s", exc)

    return rejected_count
