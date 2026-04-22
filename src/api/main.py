"""FastAPI 应用入口 — PUDIWIND AI System。"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Response

from src.feishu.bot_handler import get_bot
from src.feishu.approval import handle_card_callback

logger = logging.getLogger(__name__)

app = FastAPI(title="PUDIWIND AI System", version="0.1.0")

# --------------------------------------------------------------------------- #
#  JWT 认证中间件（必须在路由注册之前添加）
# --------------------------------------------------------------------------- #
from src.api.middleware import JWTAuthMiddleware  # noqa: E402
app.add_middleware(JWTAuthMiddleware)

# --------------------------------------------------------------------------- #
#  认证路由（登录 / 刷新 Token / 当前用户）
# --------------------------------------------------------------------------- #
from src.api.auth import router as auth_router  # noqa: E402
app.include_router(auth_router)

# --------------------------------------------------------------------------- #
#  系统管理路由（审计日志 + Kill Switch）
# --------------------------------------------------------------------------- #
from src.api.system import router as system_router  # noqa: E402
app.include_router(system_router)

from src.api.system import agents_config_router  # noqa: E402
app.include_router(agents_config_router)

# --------------------------------------------------------------------------- #
#  健康检查路由
# --------------------------------------------------------------------------- #
from src.api.health import router as health_router  # noqa: E402
app.include_router(health_router)


# --------------------------------------------------------------------------- #
#  健康检查
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health_check() -> dict[str, str]:
    """服务健康检查端点。"""
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
#  飞书 Webhook
# --------------------------------------------------------------------------- #

@app.post("/feishu/webhook")
async def feishu_webhook(request: Request) -> Response:
    """接收飞书 Webhook 回调，验证签名，路由消息命令。

    处理流程：
    1. 读取请求体
    2. 调用 bot_handler.parse_webhook_event 解析（含签名验证）
    3. 处理 url_verification 类型（飞书服务器验证）
    4. 处理 im.message.receive_v1 类型（接收消息）
    5. 调用 command_router.route_command 路由
    6. 返回 {"code": 0} 或 challenge
    """
    body = await request.body()
    headers = dict(request.headers)

    try:
        bot = get_bot()
        event = bot.parse_webhook_event(body, headers)
    except ValueError as exc:
        logger.warning("Webhook 解析失败: %s", exc)
        return Response(
            content=json.dumps({"code": 1, "msg": str(exc)}),
            media_type="application/json",
            status_code=400,
        )

    # --- url_verification（飞书配置回调地址时的握手验证）---
    if event.get("type") == "url_verification":
        challenge = event.get("challenge", "")
        return Response(
            content=json.dumps({"challenge": challenge}),
            media_type="application/json",
        )

    # --- 消息事件 ---
    header = event.get("header", {})
    event_type = header.get("event_type", "")

    if event_type == "im.message.receive_v1":
        event_data = event.get("event", {})
        message_obj = event_data.get("message", {})
        sender_obj = event_data.get("sender", {})

        msg_type = message_obj.get("message_type", "")

        if msg_type == "text":
            result = bot.handle_event(event)
            reply = result.get("reply", "")
            chat_id = result.get("chat_id", "")
            if reply and chat_id:
                try:
                    bot.send_message(chat_id, reply)
                except Exception as exc:
                    logger.error("发送跳转提示失败: %s", exc)
        else:
            logger.debug("忽略非文本消息类型: %s", msg_type)

    return Response(
        content=json.dumps({"code": 0}),
        media_type="application/json",
    )


# --------------------------------------------------------------------------- #
#  飞书卡片回调（审批按钮）
# --------------------------------------------------------------------------- #

@app.post("/feishu/card-callback")
async def feishu_card_callback(request: Request) -> Response:
    """接收飞书卡片交互按钮回调，处理审批同意/拒绝。

    飞书卡片回调格式：
    {
        "type": "card.action.trigger",
        "action": {
            "value": {"action": "approve"/"reject", "approval_id": "uuid"},
            "tag": "button"
        },
        "operator": {"open_id": "ou_xxx"}
    }
    """
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("卡片回调 JSON 解析失败: %s", exc)
        return Response(
            content=json.dumps({"code": 1, "msg": "invalid json"}),
            media_type="application/json",
            status_code=400,
        )

    result = handle_card_callback(payload)
    code = 0 if result.get("success") else 1
    return Response(
        content=json.dumps({"code": code, "data": result}),
        media_type="application/json",
    )


# --------------------------------------------------------------------------- #
#  Agent 管理路由（触发 + 状态查询）
# --------------------------------------------------------------------------- #
from src.api.agents import router as agents_router  # noqa: E402
app.include_router(agents_router)

# --------------------------------------------------------------------------- #
#  Chat SSE 路由（实时对话流）
# --------------------------------------------------------------------------- #
from src.api.chat import router as chat_router  # noqa: E402
app.include_router(chat_router)

# --------------------------------------------------------------------------- #
#  审批流路由（HITL Approval Workflow）
# --------------------------------------------------------------------------- #
from src.api.approvals import router as approvals_router  # noqa: E402
app.include_router(approvals_router)

from src.api.kb_review import router as kb_review_router  # noqa: E402
app.include_router(kb_review_router)

# --------------------------------------------------------------------------- #
#  通知路由（Notifications Mock Data API）
# --------------------------------------------------------------------------- #
from importlib import import_module

notifications_router = import_module("src.api.notifications").router
app.include_router(notifications_router)

# --------------------------------------------------------------------------- #
#  仪表盘路由（Dashboard Mock Data API）
# --------------------------------------------------------------------------- #
from src.api.dashboard import router as dashboard_router  # noqa: E402
app.include_router(dashboard_router)

# --------------------------------------------------------------------------- #
#  订单管理路由（Orders Mock Data API）
# --------------------------------------------------------------------------- #
from src.api.orders import router as orders_router  # noqa: E402
app.include_router(orders_router)

# --------------------------------------------------------------------------- #
#  退货管理路由（Returns Mock Data API）
# --------------------------------------------------------------------------- #
from src.api.returns import router as returns_router  # noqa: E402
app.include_router(returns_router)

# --------------------------------------------------------------------------- #
#  用户管理路由（CRUD + 改密码）
# --------------------------------------------------------------------------- #
from src.api.users import router as users_router  # noqa: E402
app.include_router(users_router)

# --------------------------------------------------------------------------- #
#  API 费用监控路由（boss-only）
# --------------------------------------------------------------------------- #
from src.api.monitoring import router as monitoring_router  # noqa: E402
app.include_router(monitoring_router)

# --------------------------------------------------------------------------- #
#  知识库路由（文档导入 + RAG 查询）
# --------------------------------------------------------------------------- #
from src.api.knowledge_base import router as kb_router  # noqa: E402
app.include_router(kb_router)

# --------------------------------------------------------------------------- #
#  广告管理路由（Ads Mock Data API — Dashboard + Tabs + Drill-down）
# --------------------------------------------------------------------------- #
from src.api.ads import router as ads_router  # noqa: E402
app.include_router(ads_router)

# --------------------------------------------------------------------------- #
#  Amazon Ads OAuth 回调（获取 refresh_token 的临时工具）
# --------------------------------------------------------------------------- #
from src.api.ads_oauth import router as ads_oauth_router  # noqa: E402
app.include_router(ads_oauth_router)


# --------------------------------------------------------------------------- #
#  调度器 API
# --------------------------------------------------------------------------- #

def _get_scheduler_or_error() -> Any:
    """获取调度器实例，未安装时抛出 503。"""
    from src.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="APScheduler 未安装或不可用，调度功能不可用",
        )
    return scheduler


def _get_job_description(job_id: str) -> str:
    """从配置中获取任务描述。"""
    from src.scheduler.config import SCHEDULED_JOBS
    for job_conf in SCHEDULED_JOBS:
        if job_conf.get("id") == job_id:
            return str(job_conf.get("description", ""))
    return ""


@app.get("/api/scheduler/jobs")
async def list_scheduler_jobs() -> List[Dict[str, Any]]:
    """返回所有定时任务列表（id, next_run_time, trigger, description）。"""
    scheduler = _get_scheduler_or_error()
    jobs = scheduler.get_jobs()  # type: ignore[union-attr]
    result = []
    for job in jobs:
        next_run = job.next_run_time
        result.append({
            "id": job.id,
            "next_run_time": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
            "description": _get_job_description(job.id),
        })
    return result


@app.post("/api/scheduler/jobs/{job_id}/pause")
async def pause_scheduler_job(job_id: str) -> Dict[str, Any]:
    """暂停指定任务。"""
    scheduler = _get_scheduler_or_error()
    try:
        scheduler.pause_job(job_id)  # type: ignore[union-attr]
        logger.info("任务已暂停: %s", job_id)
        return {"status": "paused", "job_id": job_id}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"任务不存在或暂停失败: {exc}") from exc


@app.post("/api/scheduler/jobs/{job_id}/resume")
async def resume_scheduler_job(job_id: str) -> Dict[str, Any]:
    """恢复指定任务。"""
    scheduler = _get_scheduler_or_error()
    try:
        scheduler.resume_job(job_id)  # type: ignore[union-attr]
        logger.info("任务已恢复: %s", job_id)
        return {"status": "resumed", "job_id": job_id}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"任务不存在或恢复失败: {exc}") from exc


@app.post("/api/scheduler/trigger/{job_id}")
async def trigger_scheduler_job(job_id: str) -> Dict[str, Any]:
    """手动立即触发一次指定任务。"""
    scheduler = _get_scheduler_or_error()
    try:
        job = scheduler.get_job(job_id)  # type: ignore[union-attr]
        if job is None:
            raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
        job.modify(next_run_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        logger.info("手动触发任务: %s", job_id)
        return {"status": "triggered", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"触发任务失败: {exc}") from exc


# --------------------------------------------------------------------------- #
#  应用启动事件 — 初始化 LangGraph Checkpointer
# --------------------------------------------------------------------------- #
@app.on_event("startup")
async def startup_event():
    """Initialize background services on app startup."""
    import logging

    _logger = logging.getLogger(__name__)

    try:
        from src.scheduler import start_scheduler

        if start_scheduler():
            _logger.info("Scheduler initialized successfully")
        else:
            _logger.warning("Scheduler not available, startup continues without scheduled jobs")
    except Exception as exc:
        _logger.warning("Scheduler startup failed (non-fatal): %s", exc)

    try:
        from src.agents.checkpointer import setup_checkpointer

        setup_checkpointer()
        _logger.info("LangGraph checkpointer initialized successfully")
    except Exception as exc:
        _logger.warning("Checkpointer setup failed (non-fatal): %s", exc)
