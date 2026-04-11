"""Product Listing Agent — LangGraph workflow."""
from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    _langgraph_graph = importlib.import_module("langgraph.graph")
    StateGraph = getattr(_langgraph_graph, "StateGraph")
    _end_node = getattr(_langgraph_graph, "END")
    _langgraph_available = True
except Exception:
    StateGraph = None  # type: ignore[assignment,misc]
    _end_node = "__end__"
    _langgraph_available = False
    logger.info("langgraph 未安装，使用顺序执行降级模式")

from src.agents.product_listing_agent.schemas import ProductListingState
from src.agents.product_listing_agent.nodes import (
    init_run,
    validate_product_data,
    prepare_payload,
    check_approval,
    finalize_run,
)

_NODE_SEQUENCE = [
    init_run,
    validate_product_data,
    prepare_payload,
    check_approval,
    finalize_run,
]


def _build_langgraph_workflow():
    if not _langgraph_available or StateGraph is None:
        return None

    try:
        workflow = StateGraph(dict)
        workflow.add_node("init_run", init_run)
        workflow.add_node("validate_product_data", validate_product_data)
        workflow.add_node("prepare_payload", prepare_payload)
        workflow.add_node("check_approval", check_approval)
        workflow.add_node("finalize_run", finalize_run)
        workflow.set_entry_point("init_run")

        def after_init(state):
            return "finalize_run" if state.get("error") else "validate_product_data"

        def after_validate(state):
            return "finalize_run" if state.get("error") else "prepare_payload"

        def after_prepare(state):
            return "finalize_run" if state.get("error") else "check_approval"

        workflow.add_conditional_edges("init_run", after_init, {
            "validate_product_data": "validate_product_data",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("validate_product_data", after_validate, {
            "prepare_payload": "prepare_payload",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("prepare_payload", after_prepare, {
            "check_approval": "check_approval",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("check_approval", "finalize_run")
        workflow.add_edge("finalize_run", _end_node)
        return workflow.compile()
    except Exception as exc:
        logger.warning("Product Listing workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: ProductListingState) -> ProductListingState:
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("product_listing_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name not in ("finalize_run",):
                current_state = finalize_run(current_state)
                break
        except Exception as exc:
            logger.error("product_listing_agent sequential | 节点 %s 异常: %s", node_name, exc)
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


def execute(product_data: Optional[dict[str, Any]] = None, marketplace: str = "ATVPDKIKX0DER", dry_run: bool = True) -> dict[str, Any]:
    """Execute product listing agent. Returns prepared payload (not auto-submitted)."""
    logger.info("product_listing_agent execute | marketplace=%s dry_run=%s", marketplace, dry_run)

    initial_state = ProductListingState(
        product_data=product_data or {},
        marketplace=marketplace,
        dry_run=dry_run,
    )

    workflow = _get_workflow()
    if workflow is not None:
        try:
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, ProductListingState):
                final_state = ProductListingState(**final_state)
        except Exception as exc:
            logger.warning("product_listing_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        final_state = _run_sequential(initial_state)

    result = {
        "sku": final_state.get("sku", ""),
        "marketplace": final_state.get("marketplace", marketplace),
        "prepared_payload": final_state.get("prepared_payload", {}),
        "validation_errors": final_state.get("validation_errors", []),
        "submission_result": final_state.get("submission_result", {}),
        "requires_approval": True,
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }
    logger.info("product_listing_agent execute | 完成 status=%s", result["status"])
    return result
