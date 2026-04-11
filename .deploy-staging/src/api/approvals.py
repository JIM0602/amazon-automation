from __future__ import annotations

import uuid
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import require_role
from src.api.schemas.approval import (
    ApprovalListResponse,
    ApprovalResponse,
    ApproveRequest,
    RejectRequest,
)
from src.db import AgentRun, ApprovalRequest, get_db
from src.services.approval import ApprovalService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _approval_to_response(approval: ApprovalRequest) -> ApprovalResponse:
    approval_any = cast(Any, approval)
    payload: dict[str, Any] = dict(approval_any.payload or {})
    return ApprovalResponse(
        id=str(approval_any.id),
        agent_run_id=str(approval_any.agent_run_id),
        action_type=approval_any.action_type,
        payload=approval_any.payload,
        status=approval_any.status,
        approved_by=approval_any.approved_by,
        comment=payload.get("review_comment"),
        created_at=approval_any.created_at.isoformat() if approval_any.created_at else "",
    )


def _visible_query(db: Session, role: str, status: str, agent_type: Optional[str]) -> list[ApprovalRequest]:
    query = db.query(ApprovalRequest).join(AgentRun).filter(ApprovalRequest.status == status)
    if role == "operator":
        query = query.filter(AgentRun.agent_type.notin_(["auditor", "brand_planning"]))
    if agent_type:
        query = query.filter(AgentRun.agent_type == agent_type)
    return query.order_by(ApprovalRequest.created_at.desc()).all()


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    status: str = Query(default="pending"),
    agent_type: Optional[str] = Query(default=None),
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ApprovalListResponse:
    approvals = _visible_query(db, current_user["role"], status, agent_type)
    return ApprovalListResponse(approvals=[_approval_to_response(item) for item in approvals], total=len(approvals))


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    service = ApprovalService(db)
    approval = service.get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id!r}")
    approval_any = cast(Any, approval)
    if current_user["role"] == "operator" and getattr(getattr(approval_any, "agent_run", None), "agent_type", None) in {"auditor", "brand_planning"}:
        raise HTTPException(status_code=403, detail="Operator cannot access this approval")
    return _approval_to_response(approval)


@router.post("/{approval_id}/approve", response_model=dict[str, bool])
async def approve_approval(
    approval_id: str,
    body: ApproveRequest,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    service = ApprovalService(db)
    try:
        approved = service.approve(approval_id, current_user["username"], current_user["role"], body.comment)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": approved}


@router.post("/{approval_id}/reject", response_model=dict[str, bool])
async def reject_approval(
    approval_id: str,
    body: RejectRequest,
    current_user: dict[str, Any] = Depends(require_role("boss", "operator")),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    service = ApprovalService(db)
    try:
        rejected = service.reject(approval_id, current_user["username"], current_user["role"], body.comment)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": rejected}
