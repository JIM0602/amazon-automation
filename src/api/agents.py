"""Agent management REST API — T4/T5.

Endpoints:
    POST   /api/agents/{agent_type}/run   — trigger an agent run (async, returns 202)
    GET    /api/agents/runs/{run_id}      — get status of a specific run
    GET    /api/agents/runs               — list runs with optional filters
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import require_role
from src.api.schemas.agents import (
    AgentRunList,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatus,
    AgentType,
    AGENT_PARAM_SCHEMAS,
)
from src.db import AgentRun, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_AGENT_TYPES = {e.value for e in AgentType} | {"auditor"}
_BOSS_ONLY_AGENT_TYPES = {"auditor", "brand_planning"}

_OUTPUT_SUMMARY_MAX_LEN = 2000  # characters


def _truncate(text: str, max_len: int = _OUTPUT_SUMMARY_MAX_LEN) -> str:
    """Truncate a long string for storage as output_summary."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "… [truncated]"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_roles_for_agent_type(agent_type: str) -> tuple[str, ...]:
    """返回指定 agent_type 允许的角色集合。"""
    if agent_type in _BOSS_ONLY_AGENT_TYPES:
        return ("boss",)
    return ("boss", "operator")


def _run_to_status(run: AgentRun) -> AgentRunStatus:
    """Convert an ORM AgentRun object to the AgentRunStatus schema."""
    result_value: Optional[dict[str, Any]] = None
    result_json = getattr(run, "result_json", None)
    output_summary = getattr(run, "output_summary", None)
    started_at = getattr(run, "started_at", None)
    finished_at = getattr(run, "finished_at", None)
    agent_type = getattr(run, "agent_type", "")
    status = getattr(run, "status", "")
    input_summary = getattr(run, "input_summary", None)
    cost_usd = getattr(run, "cost_usd", None)

    if result_json is not None:
        result_value = result_json
    elif output_summary:
        try:
            result_value = json.loads(output_summary)
        except (json.JSONDecodeError, TypeError):
            result_value = None

    return AgentRunStatus(
        run_id=str(run.id),
        agent_type=agent_type,
        status=status,
        input_summary=input_summary,
        output_summary=output_summary,
        cost_usd=cost_usd,
        started_at=started_at.isoformat() if started_at else _now_iso(),
        finished_at=finished_at.isoformat() if finished_at else None,
        result=result_value,
    )


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def _run_agent_background(
    run_id: str,
    agent_type: str,
    params: dict[str, Any],
    dry_run: bool,
) -> None:
    """Execute the requested agent in the background and update the DB record."""
    from src.db.connection import get_session_local  # lazy import — avoid circular

    db: Session = get_session_local()()
    try:
        result_data: dict[str, Any] = {}

        if agent_type == "selection":
            from src.agents.selection_agent import run as selection_run  # noqa: PLC0415

            result_data = selection_run(
                category=params.get("category", "pet_supplies"),
                dry_run=dry_run,
                subcategory=params.get("subcategory"),
            )

        elif agent_type == "listing":
            from src.agents.listing_agent import run as listing_run  # noqa: PLC0415

            result_data = listing_run(
                asin=params.get("asin", ""),
                product_name=params.get("product_name", ""),
                category=params.get("category", ""),
                dry_run=dry_run,
            )

        elif agent_type == "competitor":
            from src.agents.competitor_agent import execute as competitor_execute  # noqa: PLC0415

            result_data = competitor_execute(
                target_asin=params.get("target_asin", ""),
                competitor_asins=params.get("competitor_asins") or [],
                dry_run=dry_run,
            )

        elif agent_type == "persona":
            from src.agents.persona_agent import execute as persona_execute  # noqa: PLC0415

            result_data = persona_execute(
                category=params.get("category", ""),
                asin=params.get("asin", ""),
                dry_run=dry_run,
            )

        elif agent_type == "ad_monitor":
            from src.agents.ad_monitor_agent import execute as ad_execute  # noqa: PLC0415

            result_data = ad_execute(
                campaigns=params.get("campaigns") or [],
                thresholds=params.get("thresholds") or {},
                dry_run=dry_run,
            )

        elif agent_type == "brand_planning":
            from importlib import import_module  # noqa: PLC0415

            bp_execute = import_module("src.agents.brand_planning_agent.agent").execute
            result_data = bp_execute(
                brand_name=params.get("brand_name", ""),
                category=params.get("category", ""),
                target_market=params.get("target_market", "US"),
                budget_range=params.get("budget_range", ""),
                dry_run=dry_run,
            )

        elif agent_type == "whitepaper":
            from importlib import import_module  # noqa: PLC0415

            wp_execute = import_module("src.agents.whitepaper_agent.agent").execute
            result_data = wp_execute(
                product_name=params.get("product_name", ""),
                asin=params.get("asin", ""),
                category=params.get("category", ""),
                target_audience=params.get("target_audience", ""),
                dry_run=dry_run,
            )

        elif agent_type == "image_generation":
            from src.agents.image_gen_agent import execute as img_execute  # noqa: PLC0415

            result_data = img_execute(
                prompt=params.get("prompt", ""),
                product_name=params.get("product_name"),
                style=params.get("style", "professional"),
                size=params.get("size", "1024x1024"),
                dry_run=dry_run,
            )

        elif agent_type == "product_listing":
            from src.agents.product_listing_agent import execute as pl_execute  # noqa: PLC0415

            result_data = pl_execute(
                product_data=params.get("product_data") or {},
                marketplace=params.get("marketplace", "ATVPDKIKX0DER"),
                dry_run=dry_run,
            )

        elif agent_type == "inventory":
            from src.agents.inventory_agent import execute as inv_execute  # noqa: PLC0415

            result_data = inv_execute(
                sku_list=params.get("sku_list") or [],
                threshold_days=int(params.get("threshold_days", 30)),
                dry_run=dry_run,
            )

        elif agent_type == "core_management":
            from src.agents.core_agent import execute as core_execute  # noqa: PLC0415

            result_data = core_execute(
                report_type=params.get("report_type", "daily"),
                dry_run=dry_run,
            )

        elif agent_type == "auditor":
            logger.warning("Auditor agent requested but not implemented yet; returning placeholder result")
            result_data = {
                "agent_type": "auditor",
                "status": "not_implemented",
                "dry_run": dry_run,
            }

        else:
            raise ValueError(f"Unknown agent_type: {agent_type!r}")

        # --- success ---
        summary = _truncate(json.dumps(result_data, ensure_ascii=False, default=str))
        run_record: Optional[AgentRun] = db.query(AgentRun).filter(
            AgentRun.id == uuid.UUID(run_id)
        ).first()
        if run_record:
            setattr(run_record, "status", "success")
            setattr(run_record, "output_summary", summary)
            setattr(run_record, "finished_at", datetime.now(timezone.utc))
            if hasattr(run_record, "result_json"):
                setattr(run_record, "result_json", result_data)
            db.commit()
            logger.info("Agent %s (run_id=%s) completed successfully", agent_type, run_id)

    except Exception as exc:  # noqa: BLE001 — intentional broad catch in background task
        logger.exception("Agent %s (run_id=%s) failed: %s", agent_type, run_id, exc)
        try:
            run_record = db.query(AgentRun).filter(
                AgentRun.id == uuid.UUID(run_id)
            ).first()
            if run_record:
                setattr(run_record, "status", "failed")
                setattr(run_record, "output_summary", _truncate(str(exc)))
                setattr(run_record, "finished_at", datetime.now(timezone.utc))
                db.commit()
        except Exception as inner_exc:  # noqa: BLE001
            logger.error(
                "Failed to update DB after agent failure (run_id=%s): %s",
                run_id,
                inner_exc,
            )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoint 0: GET /api/agents/types
# ---------------------------------------------------------------------------


@router.get(
    "/types",
    summary="List all registered agent types and their parameter schemas",
)
async def list_agent_types(
    _current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
) -> dict[str, Any]:
    """Return all registered agent types with their parameter schemas.

    This endpoint is used by the frontend to dynamically render agent cards
    and parameter forms.
    """
    types = []
    for agent_type_value in AgentType:
        schema = AGENT_PARAM_SCHEMAS.get(agent_type_value.value, {})
        types.append(
            {
                "type": agent_type_value.value,
                "name": schema.get("name", agent_type_value.value),
                "description": schema.get("description", ""),
                "params": schema.get("params", {}),
            }
        )
    return {"types": types}


# ---------------------------------------------------------------------------
# Endpoint 1: POST /api/agents/{agent_type}/run
# ---------------------------------------------------------------------------

@router.post(
    "/{agent_type}/run",
    status_code=202,
    response_model=AgentRunResponse,
    summary="Trigger an agent run",
)
async def trigger_agent_run(
    agent_type: str,
    body: AgentRunRequest,
    background_tasks: BackgroundTasks,
    _current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    """Trigger an async agent run.

    Returns HTTP 202 immediately; the actual execution happens in a background
    task.  Poll ``GET /api/agents/runs/{run_id}`` to track progress.
    """
    if agent_type not in _VALID_AGENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid agent_type {agent_type!r}. "
                f"Must be one of: {sorted(_VALID_AGENT_TYPES)}"
            ),
        )

    allowed_roles = _required_roles_for_agent_type(agent_type)
    if _current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"权限不足，需要角色: {', '.join(allowed_roles)}",
        )

    # --- concurrency check: reject if the same agent is already running ---
    already_running = (
        db.query(AgentRun)
        .filter(AgentRun.agent_type == agent_type, AgentRun.status == "running")
        .first()
    )
    if already_running:
        raise HTTPException(
            status_code=409,
            detail=f"Agent {agent_type} is already running (run_id={already_running.id})",
        )

    # --- create DB record ---
    params = body.params or {}
    input_summary = _truncate(json.dumps(params, ensure_ascii=False, default=str))

    run_record = AgentRun(
        agent_type=agent_type,
        status="running",
        input_summary=input_summary,
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)

    run_id_str = str(run_record.id)

    # --- schedule background work ---
    background_tasks.add_task(
        _run_agent_background,
        run_id=run_id_str,
        agent_type=agent_type,
        params=params,
        dry_run=body.dry_run,
    )

    logger.info("Agent run accepted: type=%s run_id=%s dry_run=%s", agent_type, run_id_str, body.dry_run)

    return AgentRunResponse(
        run_id=run_id_str,
        agent_type=agent_type,
        status="running",
        message=f"Agent {agent_type} started (dry_run={body.dry_run}). Poll /api/agents/runs/{run_id_str} for status.",
    )


# ---------------------------------------------------------------------------
# Endpoint 2: GET /api/agents/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get(
    "/runs/{run_id}",
    response_model=AgentRunStatus,
    summary="Get status of a specific agent run",
)
async def get_agent_run(
    run_id: str,
    _current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> AgentRunStatus:
    """Return the current status of a single agent run by its UUID."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid run_id format: {run_id!r}") from exc

    run_record: Optional[AgentRun] = (
        db.query(AgentRun).filter(AgentRun.id == run_uuid).first()
    )
    if run_record is None:
        raise HTTPException(status_code=404, detail=f"Agent run not found: {run_id!r}")

    return _run_to_status(run_record)


# ---------------------------------------------------------------------------
# Endpoint 3: GET /api/agents/runs
# ---------------------------------------------------------------------------

@router.get(
    "/runs",
    response_model=AgentRunList,
    summary="List agent runs with optional filters",
)
async def list_agent_runs(
    agent_type: Optional[str] = Query(default=None, description="Filter by agent type"),
    status: Optional[str] = Query(default=None, description="Filter by status (running/success/failed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    _current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> AgentRunList:
    """Return a paginated, optionally filtered list of agent runs ordered by start time (desc)."""
    query = db.query(AgentRun)

    if _current_user.get("role") == "operator":
        query = query.filter(AgentRun.agent_type != "auditor")

    if agent_type is not None:
        query = query.filter(AgentRun.agent_type == agent_type)

    if status is not None:
        query = query.filter(AgentRun.status == status)

    total: int = query.count()
    runs = (
        query.order_by(AgentRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AgentRunList(
        runs=[_run_to_status(r) for r in runs],
        total=total,
    )
