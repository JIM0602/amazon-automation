"""选品分析 Agent — LangGraph 多节点工作流编排。

工作流图：
  init_run → collect_data → retrieve_kb → analyze_llm → generate_report → save_results → finalize_run

特性：
  - LangGraph 可用时构建真实 StateGraph
  - LangGraph 不可用时（测试环境）降级为顺序执行节点
  - dry_run=True 时所有节点均不调用真实外部 API
  - 支持子类目过滤（subcategory 参数）
  - 错误处理：任意节点设置 state["error"] 后，后续节点跳过，直接到 finalize_run
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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

from src.agents.selection_agent.schema import SelectionState
from src.agents.selection_agent.nodes import (
    init_run,
    collect_data,
    retrieve_kb,
    analyze_llm,
    generate_report,
    save_results,
    finalize_run,
)

# ---------------------------------------------------------------------------
# 节点执行顺序（顺序降级模式使用）
# ---------------------------------------------------------------------------
_NODE_SEQUENCE = [
    init_run,
    collect_data,
    retrieve_kb,
    analyze_llm,
    generate_report,
    save_results,
    finalize_run,
]


def _should_continue(state: SelectionState) -> str:
    """条件边：如果有错误，跳过到 finalize_run；否则继续下一步。"""
    if state.get("error"):
        return "finalize_run"
    return "continue"


def _build_langgraph_workflow():
    """构建 LangGraph StateGraph 工作流。"""
    if not _LANGGRAPH_AVAILABLE or StateGraph is None:
        return None

    try:
        # LangGraph StateGraph 使用 dict 类型
        workflow = StateGraph(dict)

        # 添加节点
        workflow.add_node("init_run", init_run)
        workflow.add_node("collect_data", collect_data)
        workflow.add_node("retrieve_kb", retrieve_kb)
        workflow.add_node("analyze_llm", analyze_llm)
        workflow.add_node("generate_report", generate_report)
        workflow.add_node("save_results", save_results)
        workflow.add_node("finalize_run", finalize_run)

        # 设置入口
        workflow.set_entry_point("init_run")

        # 添加条件边（错误时跳转到 finalize_run）
        def after_init(state):
            return "finalize_run" if state.get("error") else "collect_data"

        def after_collect(state):
            return "finalize_run" if state.get("error") else "retrieve_kb"

        def after_retrieve(state):
            return "finalize_run" if state.get("error") else "analyze_llm"

        def after_analyze(state):
            return "finalize_run" if state.get("error") else "generate_report"

        def after_report(state):
            return "finalize_run" if state.get("error") else "save_results"

        workflow.add_conditional_edges("init_run", after_init, {
            "collect_data": "collect_data",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("collect_data", after_collect, {
            "retrieve_kb": "retrieve_kb",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("retrieve_kb", after_retrieve, {
            "analyze_llm": "analyze_llm",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("analyze_llm", after_analyze, {
            "generate_report": "generate_report",
            "finalize_run": "finalize_run",
        })
        workflow.add_conditional_edges("generate_report", after_report, {
            "save_results": "save_results",
            "finalize_run": "finalize_run",
        })
        workflow.add_edge("save_results", "finalize_run")
        workflow.add_edge("finalize_run", END)

        return workflow.compile()
    except Exception as exc:
        logger.warning("LangGraph workflow 构建失败，降级为顺序执行: %s", exc)
        return None


def _run_sequential(state: SelectionState) -> SelectionState:
    """顺序执行所有节点（LangGraph 不可用时的降级实现）。"""
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("selection_agent sequential | 执行节点: %s", node_name)
            current_state = node_fn(current_state)
            # 如果有错误，跳过中间节点直接到 finalize_run
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [f for f in _NODE_SEQUENCE if f.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error(
                "selection_agent sequential | 节点 %s 异常: %s", node_name, exc
            )
            current_state["error"] = f"节点 {node_name} 执行失败: {exc}"
            current_state["status"] = "failed"
            # 尝试执行 finalize_run
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
    category: str = "pet_supplies",
    dry_run: bool = True,
    subcategory: Optional[str] = None,
) -> Dict[str, Any]:
    """执行选品分析 Agent 工作流。

    Args:
        category:    要分析的产品类目（如 "pet_supplies", "pet supplies"）
        dry_run:     True = 不调用真实外部 API（Mock 数据）
        subcategory: 可选子类目（来自飞书指令，如 "牵引绳"）

    Returns:
        dict 包含完整分析报告，结构：
        {
            "category": str,
            "analysis_date": str,
            "candidates": [...],   # ≥3个
            "kb_principles_used": [...],
            "agent_run_id": str,
            "status": "completed" | "failed",
            "error": str | None,
        }
    """
    logger.info(
        "selection_agent execute | category=%s dry_run=%s subcategory=%s",
        category,
        dry_run,
        subcategory,
    )

    # 标准化类目名称
    cat_normalized = category.lower().replace(" ", "_")

    # 初始化状态
    initial_state = SelectionState(
        category=cat_normalized,
        dry_run=dry_run,
        subcategory=subcategory,
    )

    # 尝试使用 LangGraph，降级为顺序执行
    workflow = _get_workflow()

    if workflow is not None:
        try:
            logger.info("selection_agent execute | 使用 LangGraph 工作流执行")
            final_state = workflow.invoke(initial_state)
            # LangGraph 返回 dict，包装为 SelectionState
            if not isinstance(final_state, SelectionState):
                final_state = SelectionState(**final_state)
        except Exception as exc:
            logger.warning(
                "selection_agent execute | LangGraph 执行失败，降级到顺序模式: %s", exc
            )
            final_state = _run_sequential(initial_state)
    else:
        logger.info("selection_agent execute | 使用顺序执行模式")
        final_state = _run_sequential(initial_state)

    # 提取结果
    report = final_state.get("report", {})
    candidates = final_state.get("candidates", report.get("candidates", []))

    result = {
        "category": cat_normalized,
        "analysis_date": report.get("analysis_date", ""),
        "candidates": candidates,
        "kb_principles_used": report.get("kb_principles_used", []),
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info(
        "selection_agent execute | 完成 status=%s candidate_count=%d",
        result["status"],
        len(result["candidates"]),
    )
    return result
