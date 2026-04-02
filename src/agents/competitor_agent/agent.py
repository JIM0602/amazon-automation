"""竞品调研Agent — LangGraph 多节点工作流编排。

工作流图：
  init_run → fetch_asin_data → analyze_competitors → generate_profile → finalize_run

特性：
  - LangGraph 可用时构建真实 StateGraph
  - LangGraph 不可用时（测试环境）降级为顺序执行节点
  - dry_run=True 时所有节点均不调用真实外部 API（使用Mock数据）
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

from src.agents.competitor_agent.schemas import CompetitorState
from src.agents.competitor_agent.nodes import (
    init_run,
    fetch_asin_data,
    analyze_competitors,
    generate_profile,
    finalize_run,
)

# ---------------------------------------------------------------------------
# 节点执行顺序（顺序降级模式使用）
# ---------------------------------------------------------------------------
_NODE_SEQUENCE = [
    init_run,
    fetch_asin_data,
    analyze_competitors,
    generate_profile,
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
        workflow.add_node("fetch_asin_data", fetch_asin_data)
        workflow.add_node("analyze_competitors", analyze_competitors)
        workflow.add_node("generate_profile", generate_profile)
        workflow.add_node("finalize_run", finalize_run)

        # 设置入口
        workflow.set_entry_point("init_run")

        # 添加条件边（错误时跳转到 finalize_run）
        def after_init(state):
            return "finalize_run" if state.get("error") else "fetch_asin_data"

        def after_fetch(state):
            return "finalize_run" if state.get("error") else "analyze_competitors"

        def after_analyze(state):
            return "finalize_run" if state.get("error") else "generate_profile"

        workflow.add_conditional_edges("init_run", after_init, {
            "fetch_asin_data": "fetch_asin_data",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("fetch_asin_data", after_fetch, {
            "analyze_competitors": "analyze_competitors",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("analyze_competitors", after_analyze, {
            "generate_profile": "generate_profile",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("generate_profile", "finalize_run")
        workflow.add_edge("finalize_run", END)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: CompetitorState) -> CompetitorState:
    """顺序执行所有节点（LangGraph 不可用时的降级实现）。"""
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("competitor_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            # 如果有错误，跳过中间节点直接到 finalize_run
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [f for f in _NODE_SEQUENCE if f.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error(
                "competitor_agent sequential | 节点 %s 异常: %s", node_name, exc
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
    target_asin: str = "",
    competitor_asins: List[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """执行竞品调研 Agent 工作流。

    Args:
        target_asin:      目标产品 ASIN（如 B0XXX）
        competitor_asins: 待分析的竞品 ASIN 列表（为空时使用 Mock/API 获取默认竞品）
        dry_run:          True = 不调用真实外部 API（使用 Mock 数据）

    Returns:
        dict 包含完整竞品分析结果，结构：
        {
            "target_asin": str,
            "competitor_profiles": list,
            "market_summary": str,
            "price_range": dict,
            "avg_rating": float,
            "top_keywords": list,
            "differentiation_suggestions": list,
            "agent_run_id": str,
            "status": "completed" | "failed",
            "error": str | None,
        }
    """
    logger.info(
        "competitor_agent execute | target_asin=%s dry_run=%s",
        target_asin,
        dry_run,
    )

    # 初始化状态
    initial_state = CompetitorState(
        target_asin=target_asin,
        competitor_asins=competitor_asins or [],
        dry_run=dry_run,
    )

    # 尝试使用 LangGraph，降级为顺序执行
    workflow = _get_workflow()

    if workflow is not None:
        try:
            logger.info("competitor_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, CompetitorState):
                final_state = CompetitorState(**final_state)
        except Exception as exc:
            logger.warning(
                "competitor_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc
            )
            final_state = _run_sequential(initial_state)
    else:
        logger.info("competitor_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    # 提取结果
    competitor_profile = final_state.get("competitor_profile", {})

    result = {
        "target_asin": target_asin,
        "competitor_profiles": competitor_profile.get("competitor_profiles", []),
        "market_summary": competitor_profile.get("market_summary", ""),
        "price_range": competitor_profile.get("price_range", {"min": 0.0, "max": 0.0, "avg": 0.0}),
        "avg_rating": competitor_profile.get("avg_rating", 0.0),
        "top_keywords": competitor_profile.get("top_keywords", []),
        "differentiation_suggestions": competitor_profile.get("differentiation_suggestions", []),
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info(
        "competitor_agent execute | 完成 status=%s profiles=%d",
        result["status"],
        len(result["competitor_profiles"]),
    )
    return result
