"""系统管理 API 路由。

提供：
- GET  /api/system/status      — 返回当前停机状态
- POST /api/system/stop        — 激活紧急停机（仅限 boss 角色）
- POST /api/system/resume      — 解除停机（仅限 boss 角色）
- GET  /api/system/audit-logs  — 查询最近审计日志
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import require_role
from src.utils.audit import get_recent_logs
from src.utils.killswitch import activate_stop, deactivate_stop, is_stopped, _get_stop_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------

class StopRequest(BaseModel):
    """POST /api/system/stop 的请求体。"""
    reason: str
    triggered_by: str = "api"


class ResumeRequest(BaseModel):
    """POST /api/system/resume 的请求体（可选）。"""
    triggered_by: str = "api"


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """返回当前系统停机状态。

    Response::

        {
            "stopped": true,
            "reason": "手动触发停机",
            "triggered_by": "admin",
            "activated_at": "2026-03-31T10:00:00+00:00"
        }
    """
    stopped = is_stopped()
    if stopped:
        info = _get_stop_info()
        return {
            "stopped": True,
            "reason": info.get("reason", ""),
            "triggered_by": info.get("triggered_by", ""),
            "activated_at": info.get("activated_at", ""),
        }
    return {
        "stopped": False,
        "reason": "",
        "triggered_by": "",
        "activated_at": "",
    }


@router.post("/stop")
async def stop_system(
    body: StopRequest,
    _current_user: Dict[str, Any] = Depends(require_role("boss")),
) -> Dict[str, Any]:
    """激活紧急停机。仅限 boss 角色。

    Request body::

        {"reason": "检测到异常交易", "triggered_by": "admin"}

    Response::

        {"status": "stopped", "reason": "...", "triggered_by": "..."}
    """
    if is_stopped():
        raise HTTPException(status_code=409, detail="系统已处于停机状态")

    try:
        activate_stop(reason=body.reason, triggered_by=body.triggered_by)
    except Exception as exc:
        logger.error("激活紧急停机失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"激活停机失败: {exc}") from exc

    return {
        "status": "stopped",
        "reason": body.reason,
        "triggered_by": body.triggered_by,
    }


@router.post("/resume")
async def resume_system(
    body: Optional[ResumeRequest] = None,
    _current_user: Dict[str, Any] = Depends(require_role("boss")),
) -> Dict[str, Any]:
    """解除紧急停机。仅限 boss 角色。

    Request body（可选）::

        {"triggered_by": "admin"}

    Response::

        {"status": "running", "triggered_by": "..."}
    """
    if not is_stopped():
        raise HTTPException(status_code=409, detail="系统当前并非停机状态")

    triggered_by = body.triggered_by if body else "api"

    try:
        deactivate_stop(triggered_by=triggered_by)
    except Exception as exc:
        logger.error("解除紧急停机失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"解除停机失败: {exc}") from exc

    return {
        "status": "running",
        "triggered_by": triggered_by,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500, description="返回条数，最大500"),
) -> List[Dict[str, Any]]:
    """返回最近 N 条审计日志（按时间倒序）。

    Query params:
        limit: 返回条数，默认50，最大500
    """
    logs = get_recent_logs(limit=limit)
    return logs
