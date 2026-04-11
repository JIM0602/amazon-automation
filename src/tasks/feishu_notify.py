"""飞书通知定时任务 — 日报推送与任务告警检查。

提供两个异步入口函数，可被调度器（如 APScheduler / cron）调用：
- ``run_daily_report()``   — 拉取 dashboard mock 数据，推送每日运营日报
- ``check_pending_alerts()`` — 检查审批超时/Agent 失败/KB 待审核，推送告警
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  日报推送
# --------------------------------------------------------------------------- #

async def run_daily_report() -> bool:
    """从 dashboard mock API 获取指标数据，调用 send_daily_report 推送日报。

    Returns:
        bool: 推送是否成功。
    """
    try:
        from data.mock.dashboard import get_metrics_data
        from src.feishu.notifications import send_daily_report

        raw_metrics: List[Dict[str, Any]] = get_metrics_data("site_today")

        # 将 [{key, label, value, ...}, ...] 列表转为 {key: value, ...} 字典
        metrics: Dict[str, Any] = {}
        for item in raw_metrics:
            key = item.get("key")
            if key:
                metrics[key] = item.get("value")

        ok = send_daily_report(metrics)
        if ok:
            logger.info("每日运营日报推送成功")
        else:
            logger.warning("每日运营日报推送失败（send_daily_report 返回 False）")
        return ok

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("run_daily_report 执行失败: %s", exc, exc_info=True)
        return False


# --------------------------------------------------------------------------- #
#  任务告警检查
# --------------------------------------------------------------------------- #

async def check_pending_alerts() -> int:
    """检查并推送待处理的任务告警。

    检查项目：
    1. **审批超时** (approval_pending) — 查询 pending 且已超时的审批请求
    2. **Agent 失败** (agent_failed) — 查询最近 24h 内状态为 failed 的 AgentRun
    3. **KB 待审核** (kb_review) — 查询 pending_review 状态的知识库条目

    Returns:
        int: 发出的告警总数。
    """
    alert_count = 0

    # --- 1. 审批超时检查 ---
    alert_count += await _check_approval_pending()

    # --- 2. Agent 失败检查 ---
    alert_count += await _check_agent_failed()

    # --- 3. KB 待审核检查 ---
    alert_count += await _check_kb_review()

    if alert_count > 0:
        logger.info("任务告警检查完成，共发出 %d 条告警", alert_count)
    else:
        logger.debug("任务告警检查完成，无待处理告警")

    return alert_count


async def _check_approval_pending() -> int:
    """检查超时待审批请求，发送告警。"""
    count = 0
    try:
        from src.feishu.approval import get_pending_approvals
        from src.feishu.notifications import send_task_alert
        from datetime import datetime, timezone

        pending = get_pending_approvals()
        now = datetime.now(timezone.utc)

        for ap in pending:
            expires_at_str = ap.get("expires_at", "")
            if not expires_at_str:
                continue
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now > expires_at:
                    detail = (
                        f"**审批ID**: {ap.get('approval_id', '-')}\n"
                        f"**类型**: {ap.get('action_type', '-')}\n"
                        f"**描述**: {ap.get('description', '-')}\n"
                        f"**过期时间**: {expires_at_str}"
                    )
                    send_task_alert("approval_pending", detail)
                    count += 1
            except (ValueError, TypeError):
                continue

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("审批超时检查失败: %s", exc, exc_info=True)

    return count


async def _check_agent_failed() -> int:
    """检查最近 24h 内失败的 Agent 运行，发送告警。"""
    count = 0
    try:
        from datetime import datetime, timedelta, timezone

        from src.db.connection import db_session
        from src.db.models import AgentRun
        from src.feishu.notifications import send_task_alert

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        with db_session() as session:
            failed_runs = (
                session.query(AgentRun)
                .filter(
                    AgentRun.status == "failed",
                    AgentRun.created_at >= cutoff,
                )
                .order_by(AgentRun.created_at.desc())
                .limit(20)
                .all()
            )

            for run in failed_runs:
                detail = (
                    f"**Agent 类型**: {run.agent_type}\n"
                    f"**任务摘要**: {run.input_summary or '-'}\n"
                    f"**运行ID**: {run.id}\n"
                    f"**创建时间**: {run.created_at.isoformat() if run.created_at else '-'}"
                )
                send_task_alert("agent_failed", detail)
                count += 1

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Agent 失败检查失败: %s", exc, exc_info=True)

    return count


async def _check_kb_review() -> int:
    """检查待审核的知识库条目，发送告警。"""
    count = 0
    try:
        from src.db.connection import db_session
        from src.feishu.notifications import send_task_alert

        with db_session() as session:
            # 尝试查询 KnowledgeBase 表中 status='pending_review' 的记录
            try:
                from src.db.models import KnowledgeBase  # pyright: ignore[reportAttributeAccessIssue]

                pending_items = (
                    session.query(KnowledgeBase)
                    .filter(KnowledgeBase.status == "pending_review")
                    .order_by(KnowledgeBase.created_at.desc())
                    .limit(20)
                    .all()
                )

                for item in pending_items:
                    detail = (
                        f"**条目ID**: {item.id}\n"
                        f"**标题**: {getattr(item, 'title', '-')}\n"
                        f"**类型**: {getattr(item, 'category', '-')}\n"
                        f"**创建时间**: {item.created_at.isoformat() if item.created_at else '-'}"
                    )
                    send_task_alert("kb_review", detail)
                    count += 1

            except (ImportError, AttributeError):
                # KnowledgeBase 模型不存在或缺少字段，静默跳过
                logger.debug("KnowledgeBase 模型不可用，跳过 KB 待审核检查")

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("KB 待审核检查失败: %s", exc, exc_info=True)

    return count
