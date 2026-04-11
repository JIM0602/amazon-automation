from __future__ import annotations

import logging
import uuid
from typing import Any, cast

from sqlalchemy.orm import Session

from src.db import AgentRun, ApprovalRequest
from src.feishu.notifications import send_approval_request

logger = logging.getLogger(__name__)

_BOSS_ONLY_AGENT_TYPES = {"auditor", "brand_planning"}


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def submit_for_review(
        self,
        agent_type: str,
        agent_run_id: str,
        action_type: str,
        payload: dict[str, Any] | None = None,
        summary: str | None = None,
    ) -> ApprovalRequest:
        run_uuid = uuid.UUID(agent_run_id)
        agent_run = cast(Any, self.db.query(AgentRun).filter(AgentRun.id == run_uuid).first())
        if agent_run is None:
            raise ValueError(f"Agent run not found: {agent_run_id!r}")

        body: dict[str, Any] = dict(payload or {})
        body["agent_type"] = agent_type
        if summary:
            body["summary"] = summary

        approval = ApprovalRequest()
        approval_any = cast(Any, approval)
        approval_any.agent_run_id = run_uuid
        approval_any.action_type = action_type
        approval_any.payload = body
        approval_any.status = "pending"
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)

        try:
            send_approval_request(
                {
                    "agent_type": agent_type,
                    "action_type": action_type,
                    "summary": summary or "New approval request",
                    "approval_id": str(approval.id),
                }
            )
        except Exception:
            logger.warning("Failed to send Feishu notification for approval %s", approval_any.id)

        return approval

    def list_pending(self, user_id: str, role: str) -> list[ApprovalRequest]:
        _ = user_id
        query = self.db.query(ApprovalRequest).join(AgentRun).filter(ApprovalRequest.status == "pending")
        if role == "operator":
            query = query.filter(AgentRun.agent_type.notin_(sorted(_BOSS_ONLY_AGENT_TYPES)))
        return query.order_by(ApprovalRequest.created_at.desc()).all()

    def approve(self, approval_id: str, user_id: str, role: str, comment: str | None = None) -> bool:
        approval = self._get_permitted_approval(approval_id, role)
        if approval is None:
            raise ValueError(f"Approval request not found: {approval_id!r}")
        approval_any = cast(Any, approval)
        if approval_any.status != "pending":
            return False

        payload: dict[str, Any] = dict(approval_any.payload or {})
        if comment:
            payload["review_comment"] = comment
        approval_any.payload = payload
        approval_any.status = "approved"
        approval_any.approved_by = user_id
        self.db.commit()

        # Execute the target action after successful approval
        self._execute_target_action(approval_any.action_type, payload, approval_id)

        return True

    def reject(self, approval_id: str, user_id: str, role: str, comment: str) -> bool:
        approval = self._get_permitted_approval(approval_id, role)
        if approval is None:
            raise ValueError(f"Approval request not found: {approval_id!r}")
        approval_any = cast(Any, approval)
        if approval_any.status != "pending":
            return False

        payload: dict[str, Any] = dict(approval_any.payload or {})
        payload["review_comment"] = comment
        approval_any.payload = payload
        approval_any.status = "rejected"
        approval_any.approved_by = user_id
        self.db.commit()
        return True

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        try:
            approval_uuid = uuid.UUID(approval_id)
        except ValueError:
            return None
        return self.db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_uuid).first()

    def _get_permitted_approval(self, approval_id: str, role: str) -> ApprovalRequest | None:
        approval = self.get_approval(approval_id)
        if approval is None:
            return None
        if role == "operator" and self._is_boss_only(approval):
            raise PermissionError("Operator cannot process this approval")
        return approval

    def _is_boss_only(self, approval: ApprovalRequest) -> bool:
        approval_any = cast(Any, approval)
        agent_run = getattr(approval_any, "agent_run", None)
        agent_type = getattr(agent_run, "agent_type", None)
        return agent_type in _BOSS_ONLY_AGENT_TYPES

    # ------------------------------------------------------------------
    #  Target action execution after approval
    # ------------------------------------------------------------------

    def _execute_target_action(
        self,
        action_type: str,
        payload: dict[str, Any],
        approval_id: str,
    ) -> None:
        """Dispatch and execute the approved action based on action_type.

        Known action types:
            kb_write    — Insert approved content into the knowledge base documents table.
            bid_change  — Log the approved bid change (actual API calls are gated separately).

        Unknown action types are logged and silently skipped — no error raised.
        """
        handler = _ACTION_HANDLERS.get(action_type)
        if handler is None:
            logger.info(
                "No target_action handler for action_type=%r (approval %s) — skipping",
                action_type, approval_id,
            )
            return
        try:
            handler(self.db, payload, approval_id)
            logger.info(
                "Executed target_action=%r for approval %s", action_type, approval_id,
            )
        except Exception:
            logger.exception(
                "Failed to execute target_action=%r for approval %s", action_type, approval_id,
            )


# ---------------------------------------------------------------------------
#  Action handler implementations (module-level, referenced by dispatch map)
# ---------------------------------------------------------------------------

def _handle_kb_write(db: Session, payload: dict[str, Any], approval_id: str) -> None:
    """Write approved content into the documents table as a new knowledge-base entry."""
    from src.db.models import Document

    content = payload.get("content", "")
    if not content:
        logger.warning("kb_write approval %s has empty content — skipping insert", approval_id)
        return

    doc = Document(
        title=payload.get("title", f"Approved KB entry ({approval_id[:8]})"),
        content=content,
        source=payload.get("source", f"approval:{approval_id}"),
        category=payload.get("category", "agent_generated"),
    )
    db.add(doc)
    db.commit()


def _handle_bid_change(db: Session, payload: dict[str, Any], approval_id: str) -> None:
    """Log the approved bid change. Actual SP-API write is gated behind a separate execution step."""
    from src.db.models import AdOptimizationLog

    log_entry = AdOptimizationLog(
        campaign_id=payload.get("campaign_id"),
        action_type="bid_change",
        old_value=payload.get("old_value"),
        new_value=payload.get("new_value"),
        reason=payload.get("summary", f"Approved via approval {approval_id}"),
        applied=False,
        approved_by=payload.get("approved_by"),
    )
    db.add(log_entry)
    db.commit()


# Dispatch map: action_type → handler function
_ACTION_HANDLERS: dict[str, Any] = {
    "kb_write": _handle_kb_write,
    "bid_change": _handle_bid_change,
}
