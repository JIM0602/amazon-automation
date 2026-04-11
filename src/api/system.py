"""系统管理 API 路由。

提供：
- GET  /api/system/status      — 返回当前停机状态
- POST /api/system/stop        — 激活紧急停机（仅限 boss 角色）
- POST /api/system/resume      — 解除停机（仅限 boss 角色）
- GET  /api/system/audit-logs  — 查询最近审计日志
"""
from __future__ import annotations

# pyright: reportAttributeAccessIssue=false

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

# ---------------------------------------------------------------------------
#  Admin / Boss Only Pages
# ---------------------------------------------------------------------------

from src.db import get_db
from sqlalchemy.orm import Session
from src.db.models import SystemConfig
from src.config import settings
from src.api import auth as auth_module

try:
    from src.agents.model_config import AGENT_MODEL_MAP, get_agent_model_config
    _model_config: dict[str, dict[str, str]] = {
        agent_type: get_agent_model_config(agent_type)
        for agent_type in AGENT_MODEL_MAP
    }
except ImportError:
    _model_config = {}

@router.get("/users")
def get_users(user: dict[str, Any] = Depends(require_role("boss"))) -> list[dict[str, str]]:
    """Return list of users with roles."""
    result: list[dict[str, str]] = []
    users = getattr(auth_module, "USERS", {})
    for username, info in users.items():
        result.append({
            "username": username,
            "role": info.get("role", "unknown")
        })
    return result

@router.get("/agent-config")
def get_agent_config(user: dict[str, Any] = Depends(require_role("boss"))) -> dict[str, dict[str, str]]:
    """Return agent type to model assignments."""
    return _model_config

class AgentConfigRequest(BaseModel):
    model: str

@router.put("/agent-config/{agent_type}")
def update_agent_config(
    agent_type: str,
    payload: AgentConfigRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_role("boss"))
) -> dict[str, str]:
    """Update model for an agent (write to system_config table)."""
    model_name = payload.model
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name is required")
        
    config_key = f"agent_model_{agent_type}"
    config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
    
    if config:
        setattr(config, "value", model_name)
    else:
        config = SystemConfig(key=config_key, value=model_name)
        db.add(config)
        
    db.commit()
    return {"status": "success", "agent_type": agent_type, "model": model_name}

@router.get("/api-status")
def get_api_status(user: dict[str, Any] = Depends(require_role("boss"))) -> dict[str, bool]:
    """Return which API keys are configured."""
    return {
        "OpenAI": bool(settings.OPENAI_API_KEY),
        "Anthropic": bool(settings.ANTHROPIC_API_KEY),
        "Amazon Ads": bool(settings.AMAZON_ADS_CLIENT_ID),
        "SP-API": bool(settings.AMAZON_SP_API_CLIENT_ID),
        "Seller Sprite": bool(settings.SELLER_SPRITE_API_KEY),
        "Google Trends": bool(getattr(settings, "GOOGLE_TRENDS_API_KEY", None))
    }

@router.get("/config")
def get_system_config(
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_role("boss"))
) -> dict[str, str]:
    """Return all system_config entries."""
    configs = db.query(SystemConfig).all()
    return {str(c.key): str(c.value) for c in configs if c.value is not None}

class SystemConfigRequest(BaseModel):
    value: str

@router.put("/config/{key}")
def update_system_config(
    key: str,
    payload: SystemConfigRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_role("boss"))
) -> dict[str, str]:
    """Update a system_config entry."""
    value = payload.value
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if config:
        setattr(config, "value", value)
    else:
        config = SystemConfig(key=key, value=value)
        db.add(config)
        
    db.commit()
    return {"status": "success", "key": key, "value": value}


# ---------------------------------------------------------------------------
#  Agent 中文名配置 API (/api/agents/config)
# ---------------------------------------------------------------------------
from src.db.models import AgentConfig

agents_config_router = APIRouter(prefix="/api/agents", tags=["agents-config"])


class AgentDisplayNameRequest(BaseModel):
    """PUT /api/agents/config/{agent_type} 的请求体。"""
    display_name_cn: str
    description: Optional[str] = None
    is_active: Optional[bool] = None
    visible_roles: Optional[List[str]] = None
    sort_order: Optional[int] = None


@agents_config_router.get("/config")
def get_agents_config(
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """返回所有 Agent 配置（含 display_name_cn），无需认证。

    Response::

        [
            {
                "agent_type": "core_management",
                "display_name_cn": "AI主管",
                "description": null,
                "is_active": true,
                "visible_roles": null,
                "sort_order": 0
            },
            ...
        ]
    """
    configs = db.query(AgentConfig).order_by(AgentConfig.sort_order).all()
    return [
        {
            "agent_type": c.agent_type,
            "display_name_cn": c.display_name_cn,
            "description": c.description,
            "is_active": c.is_active,
            "visible_roles": c.visible_roles,
            "sort_order": c.sort_order,
        }
        for c in configs
    ]


@agents_config_router.put("/config/{agent_type}")
def update_agent_display_config(
    agent_type: str,
    payload: AgentDisplayNameRequest,
    db: Session = Depends(get_db),
    _current_user: Dict[str, Any] = Depends(require_role("boss")),
) -> Dict[str, Any]:
    """更新 Agent 中文名配置。仅限 boss 角色。

    Request body::

        {"display_name_cn": "新名称", "description": "可选描述"}
    """
    config = db.query(AgentConfig).filter(AgentConfig.agent_type == agent_type).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent 类型 '{agent_type}' 不存在")

    config.display_name_cn = payload.display_name_cn  # type: ignore[assignment]
    if payload.description is not None:
        config.description = payload.description  # type: ignore[assignment]
    if payload.is_active is not None:
        config.is_active = payload.is_active  # type: ignore[assignment]
    if payload.visible_roles is not None:
        config.visible_roles = payload.visible_roles  # type: ignore[assignment]
    if payload.sort_order is not None:
        config.sort_order = payload.sort_order  # type: ignore[assignment]

    db.commit()
    return {
        "status": "success",
        "agent_type": agent_type,
        "display_name_cn": config.display_name_cn,
    }
