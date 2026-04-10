"""Feishu notification service — Phase 4 refactor.

Provides clean, typed notification methods. All interactive chat
handling has been moved to the web frontend.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.config import settings
from src.feishu.bot_handler import FeishuBot

logger = logging.getLogger(__name__)

# Singleton bot instance
_bot: Optional[FeishuBot] = None


def _get_bot() -> FeishuBot:
    """Get or create the FeishuBot singleton."""
    global _bot
    if _bot is None:
        _bot = FeishuBot(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET,
            encrypt_key=getattr(settings, "FEISHU_ENCRYPT_KEY", None),
        )
    return _bot


def _resolve_chat_id(chat_id: Optional[str]) -> Optional[str]:
    return chat_id or getattr(settings, "FEISHU_TEST_CHAT_ID", None)


def _stringify(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _format_mapping(data: Dict[str, Any], exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    lines = []
    for key, value in data.items():
        if key in exclude or value in (None, "", [], {}):
            continue
        lines.append(f"- **{key}**: {_stringify(value)}")
    return "\n".join(lines) if lines else "- 无详细信息"


def _build_card(title: str, body: str, template: str = "blue") -> Dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": {"template": template, "title": {"tag": "plain_text", "content": title}},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": body}},
        ],
    }


def _send_card(card: Dict[str, Any], chat_id: Optional[str]) -> bool:
    target_chat_id = _resolve_chat_id(chat_id)
    if not target_chat_id:
        logger.error("Feishu card send failed: missing chat_id")
        return False
    try:
        _get_bot().send_card(target_chat_id, card)
        return True
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Feishu card send failed: %s", exc, exc_info=True)
        return False


def send_daily_report(report: Dict[str, Any], chat_id: Optional[str] = None) -> bool:
    """Send daily summary report notification."""
    title = "📊 每日报告"
    summary = _stringify(report.get("summary") or report.get("message") or report.get("text") or "")
    body = summary if summary not in ("", "-") else "今日日报已生成。"
    details = _format_mapping(report, exclude={"summary", "message", "text"})
    card = _build_card(title, f"{body}\n\n{details}", template="blue")
    return _send_card(card, chat_id)


def send_approval_request(request: Dict[str, Any], chat_id: Optional[str] = None) -> bool:
    """Notify boss of pending approval request."""
    title = "📝 待审批请求"
    details = _format_mapping(request)
    card = _build_card(title, details, template="orange")
    return _send_card(card, chat_id)


def send_task_completion(agent_type: str, task_summary: str, chat_id: Optional[str] = None) -> bool:
    """Notify when agent task completes."""
    title = f"✅ 任务完成 · {agent_type}"
    card = _build_card(title, task_summary or "任务已完成。", template="green")
    return _send_card(card, chat_id)


def send_alert(message: str, severity: str = "info", chat_id: Optional[str] = None) -> bool:
    """Send urgent alert (inventory low, budget exceeded, etc.)."""
    severity_map = {
        "info": ("blue", "ℹ️ 告警"),
        "warning": ("orange", "⚠️ 告警"),
        "error": ("red", "❗告警"),
        "critical": ("red", "🚨 严重告警"),
    }
    template, prefix = severity_map.get(severity.lower(), severity_map["info"])
    card = _build_card(prefix, message or "系统告警", template=template)
    return _send_card(card, chat_id)
