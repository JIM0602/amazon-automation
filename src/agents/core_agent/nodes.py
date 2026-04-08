"""Core Management Agent 节点实现。"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.agents.core_agent.daily_report import generate_daily_report, generate_feishu_card
from src.agents.core_agent.approval_manager import get_approval_manager
from src.agents.core_agent.schemas import CoreManagementState

try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    db_available = True
except ImportError:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    db_available = False

try:
    from src.utils.audit import log_action
    audit_available = True
except ImportError:  # pragma: no cover
    log_action = None  # type: ignore[assignment]
    audit_available = False

try:
    from src.agents.core_agent.daily_report import DailyReportAgent
    daily_report_agent_available = True
except ImportError:  # pragma: no cover
    DailyReportAgent = None  # type: ignore[assignment]
    daily_report_agent_available = False

logger = logging.getLogger(__name__)


def _guard(state: CoreManagementState) -> bool:
    return bool(state.get("error"))


def _mark_failed(state: CoreManagementState, message: str) -> CoreManagementState:
    state["error"] = message
    state["status"] = "failed"
    return state


def init_run(state: CoreManagementState) -> CoreManagementState:
    if _guard(state):
        return state

    report_type = str(state.get("report_type", "daily") or "daily").lower()
    dry_run = bool(state.get("dry_run", True))

    if report_type not in {"daily", "weekly", "custom"}:
        return _mark_failed(state, f"不支持的 report_type: {report_type}")

    state["report_type"] = report_type
    state["dry_run"] = dry_run
    state["status"] = "running"

    input_summary = json.dumps(
        {"report_type": report_type, "dry_run": dry_run},
        ensure_ascii=False,
    )

    if not db_available or db_session is None or AgentRun is None:
        state["agent_run_id"] = state.get("agent_run_id") or str(uuid.uuid4())
        return _mark_failed(state, "数据库不可用，无法创建 agent_runs 记录")

    try:
        with db_session() as session:
            run = AgentRun(
                agent_type="core_management",
                status="running",
                input_summary=input_summary,
                started_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.flush()
            state["agent_run_id"] = str(run.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("core_management init_run failed: %s", exc)
        return _mark_failed(state, f"创建 agent_runs 记录失败: {exc}")

    return state


def generate_report(state: CoreManagementState) -> CoreManagementState:
    if _guard(state):
        return state

    dry_run = bool(state.get("dry_run", True))
    report_type = str(state.get("report_type", "daily") or "daily")

    try:
        if daily_report_agent_available and DailyReportAgent is not None:
            _ = DailyReportAgent(dry_run=dry_run)

        report_data = generate_daily_report(dry_run=dry_run)
        report_data["report_type"] = report_type
        state["report_data"] = report_data
    except Exception as exc:  # noqa: BLE001
        logger.exception("core_management generate_report failed: %s", exc)
        return _mark_failed(state, f"生成日报失败: {exc}")

    return state


def process_approvals(state: CoreManagementState) -> CoreManagementState:
    if _guard(state):
        return state

    try:
        manager = get_approval_manager()
        pending_items = manager.get_pending()
        state["approval_items"] = pending_items if isinstance(pending_items, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.exception("core_management process_approvals failed: %s", exc)
        return _mark_failed(state, f"获取待审批项失败: {exc}")

    return state


def format_output(state: CoreManagementState) -> CoreManagementState:
    if _guard(state):
        return state

    report_data = state.get("report_data") or {}
    if not report_data:
        return _mark_failed(state, "report_data 为空，无法格式化输出")

    try:
        card = generate_feishu_card(report_data)
        state["formatted_output"] = card
    except Exception as exc:  # noqa: BLE001
        logger.exception("core_management format_output failed: %s", exc)
        return _mark_failed(state, f"生成飞书卡片失败: {exc}")

    return state


def finalize_run(state: CoreManagementState) -> CoreManagementState:
    status = "failed" if state.get("error") else "completed"
    state["status"] = status

    run_id = state.get("agent_run_id")
    if not run_id:
        return state

    output_summary = json.dumps(
        {
            "status": status,
            "report_type": state.get("report_type"),
            "error": state.get("error"),
        },
        ensure_ascii=False,
        default=str,
    )

    if db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run = session.query(AgentRun).filter(AgentRun.id == uuid.UUID(str(run_id))).first()
                if run is not None:
                    setattr(run, "status", status)
                    setattr(run, "output_summary", output_summary)
                    setattr(run, "finished_at", datetime.now(timezone.utc))
                    if hasattr(run, "result_json"):
                        setattr(run, "result_json", {
                            "report_type": state.get("report_type"),
                            "report_data": state.get("report_data", {}),
                            "formatted_output": state.get("formatted_output", {}),
                            "approval_items": state.get("approval_items", []),
                            "error": state.get("error"),
                            "status": status,
                        })
                    session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("core_management finalize_run DB update failed: %s", exc)

    if audit_available and log_action is not None:
        try:
            log_action(
                action="core_management.run",
                actor="core_management",
                pre_state={
                    "report_type": state.get("report_type"),
                    "dry_run": state.get("dry_run"),
                },
                post_state={
                    "agent_run_id": run_id,
                    "status": status,
                    "error": state.get("error"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("core_management audit log failed: %s", exc)

    return state
