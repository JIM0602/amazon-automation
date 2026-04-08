"""白皮书 Agent — LangGraph 多节点工作流编排。"""
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

from .schemas import WhitepaperState
from .nodes import (
    init_run,
    research_market,
    retrieve_kb,
    generate_whitepaper,
    finalize_run,
)

_NODE_SEQUENCE = [
    init_run,
    research_market,
    retrieve_kb,
    generate_whitepaper,
    finalize_run,
]


def _build_langgraph_workflow():
    """构建 LangGraph StateGraph 工作流。"""
    if not langgraph_available or StateGraph is None:
        return None

    try:
        workflow = StateGraph(dict)

        workflow.add_node("init_run", init_run)
        workflow.add_node("research_market", research_market)
        workflow.add_node("retrieve_kb", retrieve_kb)
        workflow.add_node("generate_whitepaper", generate_whitepaper)
        workflow.add_node("finalize_run", finalize_run)

        workflow.set_entry_point("init_run")

        def after_init(state):
            return "finalize_run" if state.get("error") else "research_market"

        def after_research(state):
            return "finalize_run" if state.get("error") else "retrieve_kb"

        def after_kb(state):
            return "finalize_run" if state.get("error") else "generate_whitepaper"

        workflow.add_conditional_edges("init_run", after_init, {
            "research_market": "research_market",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("research_market", after_research, {
            "retrieve_kb": "retrieve_kb",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("retrieve_kb", after_kb, {
            "generate_whitepaper": "generate_whitepaper",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("generate_whitepaper", "finalize_run")
        workflow.add_edge("finalize_run", end_marker)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: WhitepaperState) -> WhitepaperState:
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("whitepaper_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [f for f in _NODE_SEQUENCE if f.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error("whitepaper_agent sequential | 节点 %s 异常: %s", node_name, exc)
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
    product_name: str = "",
    asin: str = "",
    category: str = "",
    target_audience: str = "",
    dry_run: bool = True,
) -> Dict[str, Any]:
    logger.info(
        "whitepaper_agent execute | product_name=%s asin=%s dry_run=%s",
        product_name,
        asin,
        dry_run,
    )

    initial_state = WhitepaperState(
        dry_run=dry_run,
        product_name=product_name,
        asin=asin,
        category=category,
        target_audience=target_audience,
    )

    workflow = _get_workflow()

    if workflow is not None:
        try:
            logger.info("whitepaper_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, WhitepaperState):
                final_state = WhitepaperState(**final_state)
        except Exception as exc:
            logger.warning("whitepaper_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        logger.info("whitepaper_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    report = final_state.get("report", {})
    sections = final_state.get("whitepaper_sections", report.get("whitepaper_sections", {}))

    result = {
        "product_name": product_name,
        "asin": asin,
        "category": category,
        "target_audience": target_audience,
        "kb_research": final_state.get("kb_research", []),
        "market_data": final_state.get("market_data", {}),
        "competitor_summary": final_state.get("competitor_summary", {}),
        "whitepaper_sections": sections,
        "report": report or {
            "product_name": product_name,
            "asin": asin,
            "category": category,
            "target_audience": target_audience,
            "kb_research": final_state.get("kb_research", []),
            "market_data": final_state.get("market_data", {}),
            "competitor_summary": final_state.get("competitor_summary", {}),
            "whitepaper_sections": sections,
        },
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info("whitepaper_agent execute | 完成 status=%s", result["status"])
    return result
