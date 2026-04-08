"""库存监控 Agent — LangGraph 多节点工作流编排。"""
from __future__ import annotations

import logging
import importlib
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    _langgraph_graph = importlib.import_module("langgraph.graph")
    langgraph_end = getattr(_langgraph_graph, "END")
    langgraph_state_graph = getattr(_langgraph_graph, "StateGraph")

    langgraph_available = True
except ImportError:
    langgraph_state_graph = None  # type: ignore[assignment,misc]
    langgraph_end = "__end__"
    langgraph_available = False
    logger.info("langgraph 未安装，使用顺序执行降级模式")

from .nodes import (
    analyze_stock,
    fetch_inventory,
    finalize_run,
    generate_alerts,
    init_run,
    save_results,
)
from .schemas import InventoryState

_NODE_SEQUENCE = [
    init_run,
    fetch_inventory,
    analyze_stock,
    generate_alerts,
    save_results,
    finalize_run,
]


def _build_langgraph_workflow():
    if not langgraph_available or langgraph_state_graph is None:
        return None

    try:
        workflow = langgraph_state_graph(dict)

        workflow.add_node("init_run", init_run)
        workflow.add_node("fetch_inventory", fetch_inventory)
        workflow.add_node("analyze_stock", analyze_stock)
        workflow.add_node("generate_alerts", generate_alerts)
        workflow.add_node("save_results", save_results)
        workflow.add_node("finalize_run", finalize_run)

        workflow.set_entry_point("init_run")

        def after_init(state):
            return "finalize_run" if state.get("error") else "fetch_inventory"

        def after_fetch(state):
            return "finalize_run" if state.get("error") else "analyze_stock"

        def after_analyze(state):
            return "finalize_run" if state.get("error") else "generate_alerts"

        def after_alerts(state):
            return "finalize_run" if state.get("error") else "save_results"

        workflow.add_conditional_edges("init_run", after_init, {"fetch_inventory": "fetch_inventory", "finalize_run": "finalize_run"})
        workflow.add_conditional_edges("fetch_inventory", after_fetch, {"analyze_stock": "analyze_stock", "finalize_run": "finalize_run"})
        workflow.add_conditional_edges("analyze_stock", after_analyze, {"generate_alerts": "generate_alerts", "finalize_run": "finalize_run"})
        workflow.add_conditional_edges("generate_alerts", after_alerts, {"save_results": "save_results", "finalize_run": "finalize_run"})
        workflow.add_edge("save_results", "finalize_run")
        workflow.add_edge("finalize_run", langgraph_end)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: InventoryState) -> InventoryState:
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("inventory_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name not in ("finalize_run",):
                current_state = finalize_run(current_state)
                break
        except Exception as exc:
            logger.error("inventory_agent sequential | 节点 %s 异常: %s", node_name, exc)
            current_state["error"] = f"节点 {node_name} 执行失败: {exc}"
            current_state["status"] = "failed"
            try:
                current_state = finalize_run(current_state)
            except Exception as fin_exc:
                logger.error("finalize_run 也失败了: %s", fin_exc)
            break
    return current_state


_workflow_app = None


def _get_workflow():
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = _build_langgraph_workflow()
    return _workflow_app


def execute(
    sku_list: Optional[list[str]] = None,
    threshold_days: int = 30,
    dry_run: bool = True,
) -> Dict[str, object]:
    logger.info(
        "inventory_agent execute | sku_count=%d threshold_days=%s dry_run=%s",
        len(sku_list or []),
        threshold_days,
        dry_run,
    )

    initial_state = InventoryState(
        sku_list=sku_list or [],
        threshold_days=threshold_days,
        dry_run=dry_run,
    )

    workflow = _get_workflow()
    if workflow is not None:
        try:
            logger.info("inventory_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, InventoryState):
                final_state = InventoryState(**final_state)
        except Exception as exc:
            logger.warning("inventory_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        logger.info("inventory_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    sku_result = final_state.get("sku_list", [])
    threshold_result = final_state.get("threshold_days", threshold_days)
    inventory_result = final_state.get("inventory_data", [])
    analysis_result = final_state.get("analysis", {})
    alerts_result = final_state.get("alerts", [])
    if not isinstance(alerts_result, list):
        alerts_result = []

    result: Dict[str, object] = {
        "sku_list": sku_result,
        "threshold_days": threshold_result,
        "inventory_data": inventory_result,
        "analysis": analysis_result,
        "alerts": alerts_result,
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info(
        "inventory_agent execute | 完成 status=%s alert_count=%d",
        result["status"],
        len(alerts_result),
    )
    return result
