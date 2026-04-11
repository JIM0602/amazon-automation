"""Core Management Agent — LangGraph 多节点工作流编排。"""

from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_langgraph_available = False
_state_graph_cls = None
_langgraph_end = "__end__"

try:
    _langgraph_graph = importlib.import_module("langgraph.graph")
    _state_graph_cls = getattr(_langgraph_graph, "StateGraph", None)
    _langgraph_end = getattr(_langgraph_graph, "END", "__end__")
    _langgraph_available = _state_graph_cls is not None
except ImportError:
    logger.info("langgraph 未安装，使用顺序执行降级模式")

from src.agents.core_agent.nodes import (
    finalize_run,
    format_output,
    generate_report,
    init_run,
    process_approvals,
)
from src.agents.core_agent.schemas import CoreManagementState

_NODE_SEQUENCE = [
    init_run,
    generate_report,
    process_approvals,
    format_output,
    finalize_run,
]


def _build_langgraph_workflow():
    if not _langgraph_available or _state_graph_cls is None:
        return None

    try:
        workflow = _state_graph_cls(dict)
        workflow.add_node("init_run", init_run)
        workflow.add_node("generate_report", generate_report)
        workflow.add_node("process_approvals", process_approvals)
        workflow.add_node("format_output", format_output)
        workflow.add_node("finalize_run", finalize_run)

        workflow.set_entry_point("init_run")

        workflow.add_conditional_edges(
            "init_run",
            lambda state: "finalize_run" if state.get("error") else "generate_report",
            {
                "generate_report": "generate_report",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_conditional_edges(
            "generate_report",
            lambda state: "finalize_run" if state.get("error") else "process_approvals",
            {
                "process_approvals": "process_approvals",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_conditional_edges(
            "process_approvals",
            lambda state: "finalize_run" if state.get("error") else "format_output",
            {
                "format_output": "format_output",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_conditional_edges(
            "format_output",
            lambda state: "finalize_run" if state.get("error") else "finalize_run",
            {
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_edge("finalize_run", _langgraph_end)

        return workflow.compile()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: CoreManagementState) -> CoreManagementState:
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("core_management sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name != "finalize_run":
                current_state = finalize_run(current_state)
                break
        except Exception as exc:  # noqa: BLE001
            logger.error("core_management sequential | 节点 %s 异常: %s", node_name, exc)
            current_state["error"] = f"节点 {node_name} 执行失败: {exc}"
            current_state["status"] = "failed"
            try:
                current_state = finalize_run(current_state)
            except Exception as fin_exc:  # noqa: BLE001
                logger.error("finalize_run 也失败了: %s", fin_exc)
            break

    return current_state


_workflow_app = None


def _get_workflow():
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = _build_langgraph_workflow()
    return _workflow_app


def execute(report_type: str = "daily", dry_run: bool = True) -> dict[str, Any]:
    logger.info("core_management execute | report_type=%s dry_run=%s", report_type, dry_run)

    initial_state = CoreManagementState(
        report_type=report_type,
        dry_run=dry_run,
        agent_run_id=None,
        error=None,
        status="running",
        report_data={},
        formatted_output={},
        approval_items=[],
    )

    workflow = _get_workflow()
    if workflow is not None:
        try:
            logger.info("core_management execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, CoreManagementState):
                final_state = CoreManagementState(final_state)
        except Exception as exc:  # noqa: BLE001
            logger.warning("core_management execute | LangGraph 执行失败，降级到顺序模式: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        logger.info("core_management execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    result = {
        "report_type": final_state.get("report_type", report_type),
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
        "report_data": final_state.get("report_data", {}),
        "formatted_output": final_state.get("formatted_output", {}),
        "approval_items": final_state.get("approval_items", []),
        "dry_run": final_state.get("dry_run", dry_run),
    }

    logger.info("core_management execute | 完成 status=%s", result["status"])
    return result
