"""Listing文案Agent — LangGraph 多节点工作流编排。

工作流图：
  init_run → retrieve_kb → generate_copy → check_compliance → finalize_run

特性：
  - LangGraph 可用时构建真实 StateGraph
  - LangGraph 不可用时（测试环境）降级为顺序执行节点
  - dry_run=True 时所有节点均不调用真实外部 API
  - 错误处理：任意节点设置 state["error"] 后，后续节点跳过，直接到 finalize_run
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangGraph 可选依赖
# ---------------------------------------------------------------------------
try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None  # type: ignore[assignment,misc]
    END = "__end__"
    _LANGGRAPH_AVAILABLE = False
    logger.info("langgraph 未安装，使用顺序执行降级模式")

from src.agents.listing_agent.schemas import ListingState
from src.agents.listing_agent.nodes import (
    init_run,
    retrieve_kb,
    generate_copy,
    check_compliance,
    finalize_run,
)

# ---------------------------------------------------------------------------
# 节点执行顺序（顺序降级模式使用）
# ---------------------------------------------------------------------------
_NODE_SEQUENCE = [
    init_run,
    retrieve_kb,
    generate_copy,
    check_compliance,
    finalize_run,
]


def _build_langgraph_workflow():
    """构建 LangGraph StateGraph 工作流。"""
    if not _LANGGRAPH_AVAILABLE or StateGraph is None:
        return None

    try:
        workflow = StateGraph(dict)

        # 添加节点
        workflow.add_node("init_run", init_run)
        workflow.add_node("retrieve_kb", retrieve_kb)
        workflow.add_node("generate_copy", generate_copy)
        workflow.add_node("check_compliance", check_compliance)
        workflow.add_node("finalize_run", finalize_run)

        # 设置入口
        workflow.set_entry_point("init_run")

        # 添加条件边（错误时跳转到 finalize_run）
        def after_init(state):
            return "finalize_run" if state.get("error") else "retrieve_kb"

        def after_retrieve(state):
            return "finalize_run" if state.get("error") else "generate_copy"

        def after_generate(state):
            return "finalize_run" if state.get("error") else "check_compliance"

        workflow.add_conditional_edges("init_run", after_init, {
            "retrieve_kb": "retrieve_kb",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("retrieve_kb", after_retrieve, {
            "generate_copy": "generate_copy",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("generate_copy", after_generate, {
            "check_compliance": "check_compliance",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("check_compliance", "finalize_run")
        workflow.add_edge("finalize_run", END)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: ListingState) -> ListingState:
    """顺序执行所有节点（LangGraph 不可用时的降级实现）。"""
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("listing_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            # 如果有错误，跳过中间节点直接到 finalize_run
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [f for f in _NODE_SEQUENCE if f.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error(
                "listing_agent sequential | 节点 %s 异常: %s", node_name, exc
            )
            current_state["error"] = f"节点 {node_name} 执行失败: {exc}"
            current_state["status"] = "failed"
            try:
                current_state = finalize_run(current_state)
            except Exception as fin_exc:
                logger.error("finalize_run 也失败了: %s", fin_exc)
            break

    return current_state


# ---------------------------------------------------------------------------
# 工作流单例
# ---------------------------------------------------------------------------
_workflow_app = None


def _get_workflow():
    """懒加载工作流实例。"""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = _build_langgraph_workflow()
    return _workflow_app


# ---------------------------------------------------------------------------
# 核心执行函数
# ---------------------------------------------------------------------------

def execute(
    asin: str = "",
    product_name: str = "",
    category: str = "",
    features: List[str] = None,
    persona_data: Dict[str, Any] = None,
    competitor_data: Dict[str, Any] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """执行Listing文案生成 Agent 工作流。

    Args:
        asin:            产品 ASIN（如 B0XXX）
        product_name:    产品名称
        category:        产品类目
        features:        产品特性列表
        persona_data:    用户画像数据（来自 persona_agent）
        competitor_data: 竞品差异数据（来自 competitor_agent）
        dry_run:         True = 不调用真实外部 API（Mock 数据）

    Returns:
        dict 包含完整文案结果，结构：
        {
            "asin": str,
            "title": str,
            "bullet_points": list[str],
            "search_terms": str,
            "aplus_copy": str | None,
            "compliance_passed": bool,
            "compliance_issues": list[str],
            "kb_tips_used": list[str],
            "agent_run_id": str,
            "status": "completed" | "failed",
            "error": str | None,
        }
    """
    logger.info(
        "listing_agent execute | asin=%s product_name=%s dry_run=%s",
        asin,
        product_name[:30] if product_name else "",
        dry_run,
    )

    # 初始化状态
    initial_state = ListingState(
        asin=asin,
        product_name=product_name,
        category=category,
        features=features or [],
        persona_data=persona_data or {},
        competitor_data=competitor_data or {},
        dry_run=dry_run,
    )

    # 尝试使用 LangGraph，降级为顺序执行
    workflow = _get_workflow()

    if workflow is not None:
        try:
            logger.info("listing_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, ListingState):
                final_state = ListingState(**final_state)
        except Exception as exc:
            logger.warning(
                "listing_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc
            )
            final_state = _run_sequential(initial_state)
    else:
        logger.info("listing_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    # 提取结果
    listing_copy = final_state.get("listing_copy", {})

    result = {
        "asin": asin,
        "title": listing_copy.get("title", ""),
        "bullet_points": listing_copy.get("bullet_points", []),
        "search_terms": listing_copy.get("search_terms", ""),
        "aplus_copy": listing_copy.get("aplus_copy"),
        "compliance_passed": listing_copy.get("compliance_passed", False),
        "compliance_issues": listing_copy.get("compliance_issues", []),
        "kb_tips_used": listing_copy.get("kb_tips_used", []),
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info(
        "listing_agent execute | 完成 status=%s compliance_passed=%s",
        result["status"],
        result["compliance_passed"],
    )
    return result
