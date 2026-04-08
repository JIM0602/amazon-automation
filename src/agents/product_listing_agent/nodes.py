"""Product Listing Agent 节点。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List

logger = logging.getLogger(__name__)

try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    _db_available = True
except ImportError:
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    _db_available = False

from src.agents.product_listing_agent.schemas import ProductListingState


_REQUIRED_FIELDS = ["title", "description", "bullet_points", "brand", "sku"]


def init_run(state: ProductListingState) -> ProductListingState:
    product_data = state.get("product_data") or {}
    dry_run = state.get("dry_run", True)

    logger.info("product_listing_agent init_run | dry_run=%s", dry_run)

    if not isinstance(product_data, dict) or not product_data:
        state["error"] = "product_data is required"
        state["status"] = "failed"
        return state

    run_id = str(uuid.uuid4())
    state["agent_run_id"] = run_id

    if not dry_run and _db_available and db_session is not None and AgentRun is not None:
        try:
            with db_session() as session:
                run_model: Any = AgentRun(
                    id=uuid.UUID(run_id),
                    agent_type="product_listing",
                    status="running",
                    input_summary=json.dumps(
                        {
                            "sku": product_data.get("sku", ""),
                            "marketplace": state.get("marketplace", "ATVPDKIKX0DER"),
                        },
                        ensure_ascii=False,
                    ),
                    started_at=datetime.now(timezone.utc),
                )
                session.add(run_model)
                session.commit()
        except Exception as exc:
            logger.warning("product_listing_agent init_run DB写入失败（非阻塞）: %s", exc)

    return state


def validate_product_data(state: ProductListingState) -> ProductListingState:
    if state.get("error"):
        return state

    product_data = state.get("product_data") or {}
    errors: List[str] = []
    for field in _REQUIRED_FIELDS:
        value = product_data.get(field)
        if field == "bullet_points":
            if not isinstance(value, list) or not value:
                errors.append(field)
        elif not str(value or "").strip():
            errors.append(field)

    state["validation_errors"] = errors
    if errors:
        state["error"] = f"Missing required product fields: {', '.join(errors)}"
        state["status"] = "failed"

    return state


def prepare_payload(state: ProductListingState) -> ProductListingState:
    if state.get("error"):
        return state

    product_data = state.get("product_data") or {}
    marketplace = state.get("marketplace", "ATVPDKIKX0DER")
    sku = str(product_data.get("sku", "")).strip()

    payload = {
        "sku": sku,
        "marketplaceId": marketplace,
        "productType": product_data.get("product_type", "PRODUCT"),
        "attributes": {
            "item_name": [str(product_data.get("title", "")).strip()],
            "brand": [str(product_data.get("brand", "")).strip()],
            "description": [str(product_data.get("description", "")).strip()],
            "bullet_point": [str(bp) for bp in (product_data.get("bullet_points") or [])],
        },
        "requires_approval": True,
    }

    state["sku"] = sku
    state["prepared_payload"] = payload
    return state


def check_approval(state: ProductListingState) -> ProductListingState:
    if state.get("error"):
        return state

    dry_run = state.get("dry_run", True)
    state["requires_approval"] = True
    state["prepared_payload"]["requires_approval"] = True
    state["prepared_payload"]["approved"] = bool(dry_run)
    return state


def finalize_run(state: ProductListingState) -> ProductListingState:
    dry_run = state.get("dry_run", True)
    error = state.get("error")
    final_status = "failed" if error else "completed"
    state["status"] = final_status

    if not dry_run and _db_available and db_session is not None and AgentRun is not None and state.get("agent_run_id"):
        try:
            with db_session() as session:
                run: Any = session.get(AgentRun, uuid.UUID(state["agent_run_id"]))
                if run:
                    setattr(run, "status", final_status)
                    setattr(run, "finished_at", datetime.now(timezone.utc))
                    setattr(run, "output_summary", json.dumps(
                        {
                            "sku": state.get("sku", ""),
                            "status": final_status,
                            "requires_approval": True,
                        },
                        ensure_ascii=False,
                    )[:200])
                    session.commit()
        except Exception as exc:
            logger.warning("product_listing_agent finalize_run DB更新失败（非阻塞）: %s", exc)

    try:
        from src.utils.audit import log_action  # noqa: PLC0415

        log_action(
            action="product_listing_agent.run",
            actor="product_listing_agent",
            pre_state={"sku": state.get("sku", ""), "dry_run": dry_run},
            post_state={
                "agent_run_id": state.get("agent_run_id", ""),
                "status": final_status,
                "requires_approval": True,
                "error": error,
            },
        )
    except Exception as exc:
        logger.warning("product_listing_agent finalize_run 审计日志写入失败（非阻塞）: %s", exc)

    if not error:
        state["submission_result"] = {
            "requires_approval": True,
            "approved": bool(dry_run),
            "submitted": False,
            "status": "prepared" if dry_run else "awaiting_approval",
        }

    return state
