"""调度器任务函数 — 3个预配置任务的 stub 实现。

实际的 Agent 业务逻辑在后续 Task 中实现；
这里只做框架：记录日志、写 agent_runs、写 audit_log，捕获所有异常。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from src.db.connection import db_session
from src.db.models import AgentRun, AuditLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _record_agent_run(job_id: str, status: str) -> None:
    """将任务执行结果写入 agent_runs 和 audit_logs 表。

    使用独立的 db_session，不共享主线程连接。
    遇到数据库异常时只记录警告，不让任务崩溃。
    """
    try:
        now = datetime.now(timezone.utc)
        with db_session() as session:
            run = AgentRun(
                agent_type=f"scheduler:{job_id}",
                status=status,
                input_summary=f"Scheduled job: {job_id}",
                output_summary=f"Job completed with status: {status}",
                finished_at=now,
            )
            session.add(run)

            audit = AuditLog(
                action="scheduler_job_run",
                actor="scheduler",
                pre_state=None,
                post_state={"job_id": job_id, "status": status},
            )
            session.add(audit)
            session.commit()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("写入数据库失败（job_id=%s）: %s", job_id, exc)


# ---------------------------------------------------------------------------
# 任务函数
# ---------------------------------------------------------------------------

def run_daily_report() -> Dict[str, Any]:
    """每日09:00发送数据日报到飞书（stub）。"""
    job_id = "daily_report"
    logger.info("daily_report started")
    started_at = datetime.now(timezone.utc)
    status = "ok"
    try:
        # TODO: 调用真实 Agent 逻辑（T12+）
        logger.info("daily_report finished in %.3f s", (datetime.now(timezone.utc) - started_at).total_seconds())
    except Exception as exc:  # pylint: disable=broad-except
        status = "error"
        logger.error("daily_report failed: %s", exc, exc_info=True)
    finally:
        _record_agent_run(job_id, status)
    return {"status": status, "job_id": job_id}


def run_selection_analysis(
    category: str = "pet_supplies",
    dry_run: bool = False,
    subcategory: str = None,
) -> Dict[str, Any]:
    """每周一10:00运行选品分析（调用真实 SelectionAgent）。

    Args:
        category:    分析类目，默认 "pet_supplies"
        dry_run:     True 时使用 Mock 数据（调度器默认为 False）
        subcategory: 可选子类目（来自飞书指令）

    Returns:
        {"status": "ok"/"error", "job_id": "selection_analysis", "report": {...}}
    """
    job_id = "selection_analysis"
    logger.info("selection_analysis started | category=%s dry_run=%s", category, dry_run)
    started_at = datetime.now(timezone.utc)
    status = "ok"
    report = {}
    try:
        from src.agents.selection_agent import run as selection_run
        report = selection_run(
            category=category,
            dry_run=dry_run,
            subcategory=subcategory,
        )
        if report.get("status") == "failed":
            status = "error"
            logger.error("selection_analysis agent failed: %s", report.get("error"))
        else:
            logger.info(
                "selection_analysis finished in %.3f s | candidate_count=%d",
                (datetime.now(timezone.utc) - started_at).total_seconds(),
                len(report.get("candidates", [])),
            )
    except Exception as exc:  # pylint: disable=broad-except
        status = "error"
        logger.error("selection_analysis failed: %s", exc, exc_info=True)
    finally:
        _record_agent_run(job_id, status)
    return {"status": status, "job_id": job_id, "report": report}


def run_llm_cost_report() -> Dict[str, Any]:
    """每日23:00发送LLM费用日报（stub）。"""
    job_id = "llm_cost_report"
    logger.info("llm_cost_report started")
    started_at = datetime.now(timezone.utc)
    status = "ok"
    try:
        # TODO: 调用真实 Agent 逻辑（T12+）
        logger.info("llm_cost_report finished in %.3f s", (datetime.now(timezone.utc) - started_at).total_seconds())
    except Exception as exc:  # pylint: disable=broad-except
        status = "error"
        logger.error("llm_cost_report failed: %s", exc, exc_info=True)
    finally:
        _record_agent_run(job_id, status)
    return {"status": status, "job_id": job_id}
