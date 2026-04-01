"""FastAPI 应用入口 — PUDIWIND AI System。"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Response

from src.feishu.bot_handler import get_bot
from src.feishu.command_router import route_command
from src.feishu.approval import handle_card_callback

logger = logging.getLogger(__name__)

app = FastAPI(title="PUDIWIND AI System", version="0.1.0")

# --------------------------------------------------------------------------- #
#  系统管理路由（审计日志 + Kill Switch）
# --------------------------------------------------------------------------- #
from src.api.system import router as system_router  # noqa: E402
app.include_router(system_router)


# --------------------------------------------------------------------------- #
#  健康检查
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health_check() -> dict:
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

        sender_id = sender_obj.get("sender_id", {}).get("open_id", "")
        msg_type = message_obj.get("message_type", "")

        if msg_type == "text":
            try:
                content = json.loads(message_obj.get("content", "{}"))
                text = content.get("text", "").strip()
            except (json.JSONDecodeError, AttributeError):
                text = ""

            if text:
                result = route_command(text, sender_id)
                action = result.get("action", "")
                logger.info("路由结果: %s (sender=%s)", action, sender_id)
                chat_id = message_obj.get("chat_id", "")

                if action == "daily_report" and chat_id:
                    try:
                        bot.send_text_message(chat_id, "⏳ 正在生成日报，请稍候...")
                        from src.agents.core_agent.daily_report import (
                            generate_daily_report,
                            generate_feishu_card,
                        )
                        report = generate_daily_report(dry_run=True)
                        card = generate_feishu_card(report)
                        bot.send_card_message(chat_id, card)
                    except Exception as exc:
                        logger.error("日报生成失败: %s", exc)
                        bot.send_text_message(chat_id, f"❌ 日报生成失败: {exc}")

                elif action == "selection_analysis" and chat_id:
                    try:
                        bot.send_text_message(chat_id, "⏳ 正在进行选品分析，请稍候...")
                        from src.agents.selection_agent import run
                        result_text = run()
                        bot.send_text_message(chat_id, result_text)
                    except Exception as exc:
                        logger.error("选品分析失败: %s", exc)
                        bot.send_text_message(chat_id, f"❌ 选品分析失败: {exc}")

                elif action == "knowledge_query" and chat_id:
                    try:
                        query = result.get("query", "")
                        from src.feishu.bot_handler import handle_qa
                        handle_qa(sender_id, chat_id, query)
                    except Exception as exc:
                        logger.error("知识库查询失败: %s", exc)
                        bot.send_text_message(chat_id, f"❌ 查询失败: {exc}")

                elif action == "emergency_stop" and chat_id:
                    try:
                        from src.utils.killswitch import activate_killswitch
                        activate_killswitch(operator=sender_id, reason="飞书指令触发")
                        bot.send_text_message(chat_id, "🛑 紧急停机已激活，所有自动化任务已暂停。")
                    except Exception as exc:
                        logger.error("紧急停机失败: %s", exc)
                        bot.send_text_message(chat_id, f"❌ 紧急停机失败: {exc}")

                else:
                    reply = result.get("message", "")
                    if reply and chat_id:
                        try:
                            bot.send_text_message(chat_id, reply)
                        except Exception as exc:
                            logger.error("发送回复失败: %s", exc)
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
#  调度器 API
# --------------------------------------------------------------------------- #

def _get_scheduler_or_error():
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
            return job_conf.get("description", "")
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
