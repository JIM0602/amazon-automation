"""审计日志工具模块。

提供对 audit_logs 表的写入和查询功能，以及装饰器支持。

设计原则：
- 写入非阻塞：失败时只记录日志，不抛出异常
- 从模块顶层导入 db_session，以便测试 patch 生效
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional

from src.db.connection import db_session
from src.db.models import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    action: str,
    actor: str,
    pre_state: Optional[dict] = None,
    post_state: Optional[dict] = None,
) -> None:
    """向 audit_logs 表写入一条记录。

    非阻塞：任何异常只记录日志，不向上抛出。

    Args:
        action:     操作描述，如 "product_updated"、"emergency_stop_activated"
        actor:      操作者，如 "system"、"user:open_id_xxx"
        pre_state:  操作前状态快照（可选）
        post_state: 操作后状态快照（可选）
    """
    try:
        with db_session() as session:
            log = AuditLog(
                action=action,
                actor=actor,
                pre_state=pre_state,
                post_state=post_state,
            )
            session.add(log)
            session.commit()
            logger.debug("审计日志已写入: action=%s actor=%s", action, actor)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("审计日志写入失败（非致命）: action=%s actor=%s error=%s", action, actor, exc)


def get_recent_logs(limit: int = 50) -> list[dict]:
    """查询最近 N 条审计日志，按时间倒序排列。

    Args:
        limit: 返回的最大条数，默认 50。

    Returns:
        list[dict]: 每条日志的字典表示，包含 id, action, actor,
                    pre_state, post_state, created_at 字段。
    """
    try:
        with db_session() as session:
            logs = (
                session.query(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "actor": log.actor,
                    "pre_state": log.pre_state,
                    "post_state": log.post_state,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("查询审计日志失败: %s", exc)
        return []


def log_rate_limit_event(
    api_group: str,
    account_id: str,
    priority: str,
    allowed: bool,
    tokens_left: float,
    retry_after: float = 0.0,
    actor: str = "system",
) -> None:
    """记录限流事件到审计日志。

    非阻塞：任何异常只记录日志，不向上抛出。

    Args:
        api_group:   API 分组，如 "llm"、"seller_sprite"
        account_id:  账号 ID
        priority:    优先级名称，如 "critical"、"normal"、"batch"
        allowed:     是否允许通过
        tokens_left: 剩余令牌数
        retry_after: 建议重试等待时间（秒），仅在限流时有意义
        actor:       操作者标识
    """
    action = "rate_limit_allowed" if allowed else "rate_limit_throttled"
    post_state = {
        "api_group": api_group,
        "account_id": account_id,
        "priority": priority,
        "allowed": allowed,
        "tokens_left": round(tokens_left, 3),
        "retry_after": round(retry_after, 3),
    }
    log_action(action=action, actor=actor, post_state=post_state)


def audit_decorator(action: str, actor: str = "system") -> Callable:
    """装饰器：在函数执行前后自动记录审计日志。

    在函数调用**前**记录 pre_state（入参摘要），
    在函数调用**后**记录 post_state（返回值摘要）。
    若函数抛出异常，post_state 记录异常信息。

    Args:
        action: 审计动作名称
        actor:  操作者标识，默认 "system"

    Example::

        @audit_decorator("product_price_updated", actor="agent:pricing")
        def update_price(sku: str, price: float) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 构造入参摘要作为 pre_state
            pre_state: dict = {}
            if args:
                pre_state["args"] = [repr(a) for a in args]
            if kwargs:
                pre_state["kwargs"] = {k: repr(v) for k, v in kwargs.items()}

            try:
                result = func(*args, **kwargs)
                post_state: dict = {"result": repr(result)}
                log_action(action, actor, pre_state=pre_state, post_state=post_state)
                return result
            except Exception as exc:
                post_state = {"error": str(exc), "error_type": type(exc).__name__}
                log_action(action, actor, pre_state=pre_state, post_state=post_state)
                raise

        return wrapper
    return decorator
