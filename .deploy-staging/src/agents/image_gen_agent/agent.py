"""Image Generation Agent orchestration."""
from __future__ import annotations

import importlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    langgraph_graph = importlib.import_module("langgraph.graph")
    langgraph_available = True
except ImportError:
    langgraph_graph = None
    langgraph_available = False
    logger.info("langgraph not installed, using sequential fallback")

from .nodes import (
    init_run,
    generate_prompt,
    generate_image,
    save_results,
    finalize_run,
)
from .schemas import ImageGenState


_NODE_SEQUENCE = [
    init_run,
    generate_prompt,
    generate_image,
    save_results,
    finalize_run,
]


def _should_continue(state: ImageGenState) -> str:
    if state.get("error"):
        return "finalize_run"
    return "continue"


def _build_langgraph_workflow():
    if not langgraph_available or langgraph_graph is None:
        return None

    try:
        workflow = langgraph_graph.StateGraph(dict)
        workflow.add_node("init_run", init_run)
        workflow.add_node("generate_prompt", generate_prompt)
        workflow.add_node("generate_image", generate_image)
        workflow.add_node("save_results", save_results)
        workflow.add_node("finalize_run", finalize_run)

        workflow.set_entry_point("init_run")

        def after_init(state):
            return "finalize_run" if state.get("error") else "generate_prompt"

        def after_prompt(state):
            return "finalize_run" if state.get("error") else "generate_image"

        def after_image(state):
            return "finalize_run" if state.get("error") else "save_results"

        workflow.add_conditional_edges(
            "init_run",
            after_init,
            {
                "generate_prompt": "generate_prompt",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_conditional_edges(
            "generate_prompt",
            after_prompt,
            {
                "generate_image": "generate_image",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_conditional_edges(
            "generate_image",
            after_image,
            {
                "save_results": "save_results",
                "finalize_run": "finalize_run",
            },
        )
        workflow.add_edge("save_results", "finalize_run")
        workflow.add_edge("finalize_run", langgraph_graph.END)

        return workflow.compile()
    except Exception as exc:
        logger.warning("image_gen_agent LangGraph build failed, fallback to sequential: %s", exc)
        return None


def _run_sequential(state: ImageGenState) -> ImageGenState:
    current_state = state
    for node_fn in _NODE_SEQUENCE:
        node_name = node_fn.__name__
        try:
            logger.debug("image_gen_agent sequential | execute node: %s", node_name)
            current_state = node_fn(current_state)
            if current_state.get("error") and node_name not in ("finalize_run",):
                remaining = [fn for fn in _NODE_SEQUENCE if fn.__name__ == "finalize_run"]
                if remaining:
                    current_state = remaining[0](current_state)
                break
        except Exception as exc:
            logger.error("image_gen_agent sequential | node %s failed: %s", node_name, exc)
            current_state["error"] = f"node {node_name} failed: {exc}"
            current_state["status"] = "failed"
            try:
                current_state = finalize_run(current_state)
            except Exception as fin_exc:
                logger.error("image_gen_agent finalize_run also failed: %s", fin_exc)
            break

    return current_state


_workflow_app = None


def _get_workflow():
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = _build_langgraph_workflow()
    return _workflow_app


def execute(
    prompt: str,
    product_name: Optional[str] = None,
    style: str = "professional",
    size: str = "1024x1024",
    dry_run: bool = True,
) -> dict[str, object]:
    logger.info(
        "image_gen_agent execute | dry_run=%s style=%s size=%s product_name=%s",
        dry_run,
        style,
        size,
        product_name,
    )

    initial_state = ImageGenState(
        prompt=prompt,
        product_name=product_name,
        style=style,
        size=size,
        dry_run=dry_run,
    )

    workflow = _get_workflow()
    if workflow is not None:
        try:
            logger.info("image_gen_agent execute | using LangGraph workflow")
            final_state = workflow.invoke(initial_state)
            if not isinstance(final_state, ImageGenState):
                final_state = ImageGenState(**final_state)
        except Exception as exc:
            logger.warning("image_gen_agent execute | LangGraph failed, fallback to sequential: %s", exc)
            final_state = _run_sequential(initial_state)
    else:
        logger.info("image_gen_agent execute | using sequential mode")
        final_state = _run_sequential(initial_state)

    result: dict[str, object] = {
        "prompt": final_state.get("prompt", ""),
        "product_name": final_state.get("product_name"),
        "style": final_state.get("style", "professional"),
        "size": final_state.get("size", "1024x1024"),
        "enhanced_prompt": final_state.get("enhanced_prompt", ""),
        "image_url": final_state.get("image_url", ""),
        "image_data": final_state.get("image_data", ""),
        "revised_prompt": final_state.get("revised_prompt", ""),
        "agent_run_id": final_state.get("agent_run_id", ""),
        "status": final_state.get("status", "completed"),
        "error": final_state.get("error"),
    }

    logger.info(
        "image_gen_agent execute | completed status=%s image_url=%s",
        result["status"],
        result["image_url"],
    )
    return result
