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


def send_daily_report(metrics: Dict[str, Any], chat_id: Optional[str] = None) -> bool:
    """发送每日运营日报飞书卡片消息。

    Args:
        metrics: 包含核心指标的字典，支持以下键（均可选，缺失显示 '-'）：
            - total_sales:        销售额 (USD)
            - total_orders:       订单量
            - units_sold:         销量
            - ad_spend:           广告花费 (USD)
            - ad_orders:          广告订单
            - acos:               ACoS (0~1 ratio)
            - tacos:              TACoS (0~1 ratio)
            - returns_count:      退货数
            - conversion_rate:    转化率 (0~1 ratio)
            - avg_order_value:    客单价 (USD)
        chat_id: 目标飞书群 ID，None 时使用默认群。

    Returns:
        bool: 发送是否成功。
    """
    from datetime import date as _date

    today_str = _date.today().strftime("%Y-%m-%d")
    title = f"📊 每日运营日报 · {today_str}"

    def _fmt_usd(v: Any) -> str:
        if v is None:
            return "-"
        return f"${v:,.2f}" if isinstance(v, (int, float)) else _stringify(v)

    def _fmt_pct(v: Any) -> str:
        if v is None:
            return "-"
        if isinstance(v, (int, float)):
            return f"{v * 100:.1f}%"
        return _stringify(v)

    def _fmt_int(v: Any) -> str:
        if v is None:
            return "-"
        if isinstance(v, (int, float)):
            return f"{int(v):,}"
        return _stringify(v)

    rows = [
        ("💰 销售额", _fmt_usd(metrics.get("total_sales"))),
        ("📦 订单量", _fmt_int(metrics.get("total_orders"))),
        ("📈 销量", _fmt_int(metrics.get("units_sold"))),
        ("💸 广告花费", _fmt_usd(metrics.get("ad_spend"))),
        ("🎯 广告订单", _fmt_int(metrics.get("ad_orders"))),
        ("📊 ACoS", _fmt_pct(metrics.get("acos"))),
        ("📉 TACoS", _fmt_pct(metrics.get("tacos"))),
        ("↩️ 退货数", _fmt_int(metrics.get("returns_count"))),
        ("🔄 转化率", _fmt_pct(metrics.get("conversion_rate"))),
        ("💵 客单价", _fmt_usd(metrics.get("avg_order_value"))),
    ]

    body_lines = [f"**{label}**：{value}" for label, value in rows if value != "-"]
    body = "\n".join(body_lines) if body_lines else "今日暂无数据"

    card: Dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": body}},
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"数据统计日期: {today_str} · Amazon 运营自动化系统"},
                ],
            },
        ],
    }
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


def send_task_alert(alert_type: str, details: str, chat_id: Optional[str] = None) -> bool:
    """发送任务告警飞书卡片消息。

    Args:
        alert_type: 告警类型，支持：
            - ``approval_pending`` — 审批超时待处理
            - ``agent_failed``    — Agent 执行失败
            - ``kb_review``       — 知识库内容待审核
        details: 告警详细描述（纯文本或 lark_md 格式均可）。
        chat_id: 目标飞书群 ID，None 时使用默认群。

    Returns:
        bool: 发送是否成功。
    """
    alert_config: Dict[str, Dict[str, str]] = {
        "approval_pending": {
            "title": "⏰ 审批超时提醒",
            "template": "orange",
            "icon": "⏰",
        },
        "agent_failed": {
            "title": "❗ Agent 执行失败",
            "template": "red",
            "icon": "❗",
        },
        "kb_review": {
            "title": "📝 知识库待审核",
            "template": "purple",
            "icon": "📝",
        },
    }

    config = alert_config.get(alert_type, {
        "title": f"⚠️ 任务告警 · {alert_type}",
        "template": "orange",
        "icon": "⚠️",
    })

    body = details or "无详细信息"

    card: Dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": config["template"],
            "title": {"tag": "plain_text", "content": config["title"]},
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{config['icon']} **告警类型**：{alert_type}",
                },
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": body},
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": "Amazon 运营自动化系统 · 任务告警"},
                ],
            },
        ],
    }
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
