"""品牌规划 Agent — LangGraph 多节点工作流编排。"""
from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    _langgraph_module = import_module("langgraph.graph")
    StateGraph = getattr(_langgraph_module, "StateGraph", None)
    end_marker = getattr(_langgraph_module, "END", "__end__")
    langgraph_available = StateGraph is not None
except Exception:
    StateGraph = None  # type: ignore[assignment,misc]
    end_marker = "__end__"
    langgraph_available = False
    logger.info("langgraph 未安装，使用顺序执行降级模式")

from .schemas import BrandPlanningState
from .nodes import (
    init_run,
    collect_market_data,
    retrieve_kb,
    generate_strategy,
    finalize_run,
)

_NODE_SEQUENCE = [
    init_run,
    collect_market_data,
    retrieve_kb,
    generate_strategy,
    finalize_run,
]


def _build_langgraph_workflow():
    """构建 LangGraph StateGraph 工作流。"""
    if not langgraph_available or StateGraph is None:
        return None

    try:
        workflow = StateGraph(dict)

        workflow.add_node("init_run", init_run)
        workflow.add_node("collect_market_data", collect_market_data)
        workflow.add_node("retrieve_kb", retrieve_kb)
        workflow.add_node("generate_strategy", generate_strategy)
        workflow.add_node("finalize_run", finalize_run)

        workflow.set_entry_point("init_run")

        def after_init(state):
            return "finalize_run" if state.get("error") else "collect_market_data"

        def after_collect(state):
            return "finalize_run" if state.get("error") else "retrieve_kb"

        def after_retrieve(state):
            return "finalize_run" if state.get("error") else "generate_strategy"

        workflow.add_conditional_edges("init_run", after_init, {
            "collect_market_data": "collect_market_data",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("collect_market_data", after_collect, {
            "retrieve_kb": "retrieve_kb",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("retrieve_kb", after_retrieve, {
            "generate_strategy": "generate_strategy",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("generate_strategy", "finalize_run")
        workflow.add_edge("finalize_run", end_marker)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: BrandPlanningState) -> BrandPlanningState:
    """顺序执行所有节点（LangGraph 不可用时的降级实现）。"""
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("brand_planning_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [f for f in _NODE_SEQUENCE if f.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error("brand_planning_agent sequential | 节点 %s 异常: %s", node_name, exc)
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
    """懒加载工作流实例。"""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = _build_langgraph_workflow()
    return _workflow_app


def execute(
    brand_name: str = "",
    category: str = "",
    target_market: str = "US",
    budget_range: str = "",
    dry_run: bool = True,
) -> Dict[str, Any]:
    """执行品牌规划 Agent 工作流。"""
    logger.info(
        "brand_planning_agent execute | brand_name=%s category=%s dry_run=%s",
        brand_name,
        category,
        dry_run,
    )

    initial_state = BrandPlanningState(
        dry_run=dry_run,
        brand_name=brand_name,
        category=category,
        target_market=target_market,
        budget_range=budget_range,
    )

    workflow = _get_workflow()

    if workflow is not None:
        try:
            logger.info("brand_planning_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, BrandPlanningState):
                final_state = BrandPlanningState(**final_state)
        except Exception as exc:
            logger.warning("brand_planning_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        logger.info("brand_planning_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    report = final_state.get("report", {})
    brand_strategy = final_state.get("brand_strategy", report.get("brand_strategy", {}))

    result = {
        "brand_name": brand_name,
        "category": category,
        "target_market": target_market,
        "budget_range": budget_range,
        "kb_insights": final_state.get("kb_insights", []),
        "market_analysis": final_state.get("market_analysis", {}),
        "brand_strategy": brand_strategy,
        "report": report or {
            "brand_name": brand_name,
            "category": category,
            "target_market": target_market,
            "budget_range": budget_range,
            "kb_insights": final_state.get("kb_insights", []),
            "market_analysis": final_state.get("market_analysis", {}),
            "brand_strategy": brand_strategy,
        },
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info("brand_planning_agent execute | 完成 status=%s", result["status"])
    return result
