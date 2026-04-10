from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class SubmitApprovalRequest(BaseModel):
    agent_type: str
    agent_run_id: str
    action_type: str
    payload: Optional[dict[str, Any]] = None
    summary: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: str
    agent_run_id: str
    action_type: str
    payload: Optional[dict[str, Any]]
    status: str
    approved_by: Optional[str]
    comment: Optional[str]
    created_at: str


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]
    total: int


class ApproveRequest(BaseModel):
    comment: Optional[str] = None


class RejectRequest(BaseModel):
    comment: str
