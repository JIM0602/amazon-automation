"""紧急停机（Kill Switch）模块。

功能：
- 读取 DB 中的 emergency_stop 配置判断系统是否处于停机状态
- 激活 / 解除紧急停机
- 装饰器：在 Agent 动作执行前检查停机状态

设计原则：
- 每次读 DB（不缓存），保证实时生效
- 模块顶部导入 db_session，保证测试 patch 生效
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional

from src.db.connection import db_session
from src.db.models import SystemConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------

class SystemStoppedError(Exception):
    """系统处于紧急停机状态时抛出。"""

    def __init__(self, reason: str = "系统已紧急停机") -> None:
        super().__init__(reason)
        self.reason = reason


# ---------------------------------------------------------------------------
# 飞书通知（可选依赖）
# ---------------------------------------------------------------------------
try:
    from src.feishu.bot_handler import get_bot as _get_feishu_bot
    _FEISHU_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FEISHU_AVAILABLE = False


def _send_feishu_notification(message: str) -> None:
    """向飞书发送通知消息（不可用时静默忽略）。"""
    if not _FEISHU_AVAILABLE:
        logger.warning("飞书不可用，跳过通知: %s", message)
        return
    try:
        bot = _get_feishu_bot()
        bot.send_text(message)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("飞书通知发送失败（非致命）: %s", exc)


# ---------------------------------------------------------------------------
# 核心功能
# ---------------------------------------------------------------------------

def is_stopped() -> bool:
    """检查系统是否处于紧急停机状态。

    每次查询 DB（不缓存），保证实时生效。

    Returns:
        True 表示系统已停机，False 表示正常运行。
    """
    try:
        with db_session() as session:
            config = session.get(SystemConfig, "emergency_stop")
            if config is None:
                return False
            val = config.value
            # value 字段类型为 JSON，可能存储字符串 "true" 或布尔 True
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() == "true"
            return bool(val)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("读取 kill switch 状态失败，默认返回 False: %s", exc)
        return False


def _get_stop_info() -> dict:
    """获取停机详情（reason, triggered_by, activated_at）。"""
    try:
        with db_session() as session:
            reason_cfg = session.get(SystemConfig, "emergency_stop_reason")
            by_cfg = session.get(SystemConfig, "emergency_stop_triggered_by")
            at_cfg = session.get(SystemConfig, "emergency_stop_activated_at")
            return {
                "reason": reason_cfg.value if reason_cfg else "",
                "triggered_by": by_cfg.value if by_cfg else "",
                "activated_at": at_cfg.value if at_cfg else "",
            }
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("读取停机详情失败: %s", exc)
        return {"reason": "", "triggered_by": "", "activated_at": ""}


def activate_stop(reason: str, triggered_by: str) -> None:
    """激活紧急停机。

    操作顺序：
    1. 写入 system_config（emergency_stop=true 及相关元数据）
    2. 暂停 APScheduler 所有任务
    3. 记录 audit_log
    4. 发送飞书通知（如可用）

    Args:
        reason:      停机原因
        triggered_by: 触发者标识
    """
    import datetime

    activated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. 写入 system_config
    try:
        with db_session() as session:
            _upsert_config(session, "emergency_stop", "true")
            _upsert_config(session, "emergency_stop_reason", reason)
            _upsert_config(session, "emergency_stop_triggered_by", triggered_by)
            _upsert_config(session, "emergency_stop_activated_at", activated_at)
            session.commit()
        logger.warning("紧急停机已激活: reason=%s triggered_by=%s", reason, triggered_by)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("写入 emergency_stop 配置失败: %s", exc)
        raise

    # 2. 暂停所有调度任务
    _pause_all_jobs()

    # 3. 记录 audit_log（导入放在函数内避免循环导入）
    from src.utils.audit import log_action
    log_action(
        action="emergency_stop_activated",
        actor=triggered_by,
        pre_state={"stopped": False},
        post_state={"stopped": True, "reason": reason, "activated_at": activated_at},
    )

    # 4. 飞书通知
    _send_feishu_notification(
        f"🚨 [紧急停机] 系统已停机\n原因: {reason}\n触发者: {triggered_by}\n时间: {activated_at}"
    )


def deactivate_stop(triggered_by: str) -> None:
    """解除紧急停机。

    操作顺序：
    1. 更新 system_config（emergency_stop=false）
    2. 恢复 APScheduler 所有任务
    3. 记录 audit_log

    Args:
        triggered_by: 解除操作者标识
    """
    import datetime

    deactivated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 获取解除前的停机信息，用于 audit log
    stop_info = _get_stop_info()

    # 1. 更新 system_config
    try:
        with db_session() as session:
            _upsert_config(session, "emergency_stop", "false")
            session.commit()
        logger.info("紧急停机已解除: triggered_by=%s", triggered_by)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("更新 emergency_stop 配置失败: %s", exc)
        raise

    # 2. 恢复所有调度任务
    _resume_all_jobs()

    # 3. 记录 audit_log
    from src.utils.audit import log_action
    log_action(
        action="emergency_stop_deactivated",
        actor=triggered_by,
        pre_state={
            "stopped": True,
            "reason": stop_info["reason"],
            "activated_at": stop_info["activated_at"],
        },
        post_state={"stopped": False, "deactivated_at": deactivated_at},
    )


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _upsert_config(session: Any, key: str, value: Any) -> None:
    """插入或更新 system_config 中的一条记录。"""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import insert as sa_insert

    config = session.get(SystemConfig, key)
    if config is None:
        config = SystemConfig(key=key, value=value)
        session.add(config)
    else:
        config.value = value


def _pause_all_jobs() -> None:
    """暂停 APScheduler 中所有任务（不可用时静默忽略）。"""
    try:
        from src.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler is None:
            logger.warning("APScheduler 不可用，跳过暂停任务")
            return
        jobs = scheduler.get_jobs()  # type: ignore[union-attr]
        for job in jobs:
            try:
                scheduler.pause_job(job.id)  # type: ignore[union-attr]
                logger.info("已暂停调度任务: %s", job.id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("暂停任务 %s 失败: %s", job.id, exc)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("暂停所有调度任务失败（非致命）: %s", exc)


def _resume_all_jobs() -> None:
    """恢复 APScheduler 中所有任务（不可用时静默忽略）。"""
    try:
        from src.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler is None:
            logger.warning("APScheduler 不可用，跳过恢复任务")
            return
        jobs = scheduler.get_jobs()  # type: ignore[union-attr]
        for job in jobs:
            try:
                scheduler.resume_job(job.id)  # type: ignore[union-attr]
                logger.info("已恢复调度任务: %s", job.id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("恢复任务 %s 失败: %s", job.id, exc)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("恢复所有调度任务失败（非致命）: %s", exc)


# ---------------------------------------------------------------------------
# 装饰器
# ---------------------------------------------------------------------------

def check_killswitch() -> Callable:
    """装饰器：在任何 Agent 动作执行前检查是否停机。

    停机时 raise SystemStoppedError，阻止函数执行。

    Example::

        @check_killswitch()
        def run_pricing_agent():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if is_stopped():
                info = _get_stop_info()
                raise SystemStoppedError(
                    f"系统处于紧急停机状态，拒绝执行 {func.__name__}。"
                    f"停机原因: {info.get('reason', '未知')}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
