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
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.schemas.agents import (
    AgentRunList,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatus,
    AgentType,
)
from src.db import AgentRun, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_AGENT_TYPES = {e.value for e in AgentType}

_OUTPUT_SUMMARY_MAX_LEN = 2000  # characters


def _truncate(text: str, max_len: int = _OUTPUT_SUMMARY_MAX_LEN) -> str:
    """Truncate a long string for storage as output_summary."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "… [truncated]"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_to_status(run: AgentRun) -> AgentRunStatus:
    """Convert an ORM AgentRun object to the AgentRunStatus schema."""
    return AgentRunStatus(
        run_id=str(run.id),
        agent_type=run.agent_type,
        status=run.status,
        input_summary=run.input_summary,
        output_summary=run.output_summary,
        cost_usd=run.cost_usd,
        started_at=run.started_at.isoformat() if run.started_at else _now_iso(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def _run_agent_background(
    run_id: str,
    agent_type: str,
    params: dict,
    dry_run: bool,
) -> None:
    """Execute the requested agent in the background and update the DB record."""
    from src.db.connection import get_session_local  # lazy import — avoid circular

    db: Session = get_session_local()()
    try:
        result_data: dict = {}

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
                competitor_asins=params.get("competitor_asins"),
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
                campaigns=params.get("campaigns"),
                thresholds=params.get("thresholds"),
                dry_run=dry_run,
            )

        else:
            raise ValueError(f"Unknown agent_type: {agent_type!r}")

        # --- success ---
        summary = _truncate(json.dumps(result_data, ensure_ascii=False, default=str))
        run_record: Optional[AgentRun] = db.query(AgentRun).filter(
            AgentRun.id == uuid.UUID(run_id)
        ).first()
        if run_record:
            run_record.status = "success"
            run_record.output_summary = summary
            run_record.finished_at = datetime.now(timezone.utc)
            db.commit()

    except Exception as exc:  # noqa: BLE001 — intentional broad catch in background task
        logger.exception("Agent %s (run_id=%s) failed: %s", agent_type, run_id, exc)
        try:
            run_record = db.query(AgentRun).filter(
                AgentRun.id == uuid.UUID(run_id)
            ).first()
            if run_record:
                run_record.status = "failed"
                run_record.output_summary = _truncate(str(exc))
                run_record.finished_at = datetime.now(timezone.utc)
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
    db: Session = Depends(get_db),
) -> AgentRunList:
    """Return a paginated, optionally filtered list of agent runs ordered by start time (desc)."""
    query = db.query(AgentRun)

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
