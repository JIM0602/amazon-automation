from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func

from src.api.dependencies import get_current_user
from src.db.connection import SessionLocal
from src.db.models import AgentRun, ApprovalRequest, KBReviewQueue

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationItem(TypedDict):
    id: str
    type: str
    title: str
    time: str
    read: bool


_NOTIFICATIONS: list[NotificationItem] = [
    {
        "id": "notif-1",
        "type": "approval",
        "title": "有新的审批待处理",
        "time": "2026-04-10T08:30:00+00:00",
        "read": False,
    },
    {
        "id": "notif-2",
        "type": "kb_review",
        "title": "知识库审核队列有新内容",
        "time": "2026-04-10T07:50:00+00:00",
        "read": False,
    },
    {
        "id": "notif-3",
        "type": "agent_failure",
        "title": "过去 24 小时有 Agent 运行失败",
        "time": "2026-04-10T07:10:00+00:00",
        "read": True,
    },
]


def _find_notification(notification_id: str) -> NotificationItem | None:
    for notification in _NOTIFICATIONS:
        if notification["id"] == notification_id:
            return notification
    return None


@router.get("/count")
async def get_notification_count(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, int]:
    del current_user
    with SessionLocal() as db:
        approvals = db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").count()

        try:
            kb_reviews = db.query(KBReviewQueue).filter(KBReviewQueue.status == "pending").count()
        except Exception:
            kb_reviews = 0

        try:
            window_start = datetime.now(timezone.utc) - timedelta(hours=24)
            agent_failures = (
                db.query(AgentRun)
                .filter(AgentRun.status == "failed")
                .filter(func.coalesce(AgentRun.finished_at, AgentRun.started_at) >= window_start)
                .count()
            )
        except Exception:
            agent_failures = 0

    return {
        "approvals": approvals,
        "kb_reviews": kb_reviews,
        "agent_failures": agent_failures,
        "buyer_messages": 0,
    }


@router.get("/list")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    page_size = 10
    start = (page - 1) * page_size
    end = start + page_size
    items = _NOTIFICATIONS[start:end]
    return {
        "notifications": items,
        "page": page,
        "page_size": page_size,
        "total": len(_NOTIFICATIONS),
    }


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    notification = _find_notification(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification["read"] = True
    return {"success": True, "notification": notification}
