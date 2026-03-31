"""FastAPI 应用入口 — PUDIWIND AI System。"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request, Response

from src.feishu.bot_handler import get_bot
from src.feishu.command_router import route_command

logger = logging.getLogger(__name__)

app = FastAPI(title="PUDIWIND AI System", version="0.1.0")


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
                logger.info("路由结果: %s (sender=%s)", result.get("action"), sender_id)
        else:
            logger.debug("忽略非文本消息类型: %s", msg_type)

    return Response(
        content=json.dumps({"code": 0}),
        media_type="application/json",
    )
