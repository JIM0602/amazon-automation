"""LLM费用监控模块。

功能：
  - get_daily_cost()        — 查询今天所有 agent_runs 的 cost_usd 总和
  - check_daily_limit()     — 返回费用状态字典（daily_cost, limit, percentage, exceeded, warning）
  - send_feishu_warning()   — 发送飞书预警
  - filter_pii()            — PII 过滤（邮箱/电话/信用卡号）
"""
from __future__ import annotations

import re
from typing import Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging as _logging
    logger = _logging.getLogger(__name__)  # type: ignore[assignment]

# 模块级懒加载 settings（便于测试 patch）
try:
    from src.config import settings
except Exception:  # pragma: no cover
    settings = None  # type: ignore[assignment]

# 模块级懒加载 db 相关（便于测试 patch）
try:
    from src.db.connection import db_session
    from src.db.models import AgentRun
    from sqlalchemy import func as _sa_func
except Exception:  # pragma: no cover
    db_session = None  # type: ignore[assignment]
    AgentRun = None  # type: ignore[assignment]
    _sa_func = None  # type: ignore[assignment]

# 模块级懒加载飞书（便于测试 patch）
try:
    from src.feishu.bot_handler import get_bot
except Exception:  # pragma: no cover
    get_bot = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# PII 正则模式
# ---------------------------------------------------------------------------
_EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# 电话号码: 美式 555-1234 / (555) 123-4567 / 国际 +1-555-123-4567
_PHONE_PATTERN = re.compile(
    r'(?:\+\d{1,3}[-.\s]?)?'        # 可选国际区号
    r'(?:\(\d{3}\)[-.\s]?|\d{3}[-.\s])'  # 区号（括号或不带括号）
    r'\d{3}[-.\s]?'                  # 局号
    r'\d{4}'                         # 用户号
)

# 信用卡号: 4组4位数字，用 - 或空格分隔
_CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b')


def filter_pii(text: str) -> str:
    """对文本进行 PII 脱敏。

    替换规则:
      - 邮箱       → [REDACTED_EMAIL]
      - 电话号码   → [REDACTED_PHONE]
      - 信用卡号   → [REDACTED_CARD]

    Args:
        text: 待脱敏的原始文本

    Returns:
        脱敏后的文本
    """
    # 先替换信用卡（4组数字，需在通用数字替换前）
    text = _CREDIT_CARD_PATTERN.sub('[REDACTED_CARD]', text)
    # 替换邮箱
    text = _EMAIL_PATTERN.sub('[REDACTED_EMAIL]', text)
    # 替换电话
    text = _PHONE_PATTERN.sub('[REDACTED_PHONE]', text)
    return text


def get_daily_cost() -> float:
    """查询今天所有 LLM 调用的 cost_usd 总和。

    Returns:
        今日总费用（USD），如果数据库不可用则返回 0.0
    """
    try:
        from datetime import date, datetime, timezone
        from sqlalchemy import func

        today = date.today()
        today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

        with db_session() as session:
            result = session.query(
                func.coalesce(func.sum(AgentRun.cost_usd), 0.0)
            ).filter(
                AgentRun.agent_type == "llm_call",
                AgentRun.started_at >= today_start,
            ).scalar()
            return float(result or 0.0)
    except Exception as e:
        logger.warning(f"查询每日费用失败，返回 0.0: {e}")
        return 0.0


def check_daily_limit() -> dict:
    """检查是否达到每日费用上限。

    Returns:
        {
            "daily_cost": float,    — 今日已花费（USD）
            "limit": float,         — 每日上限（USD）
            "percentage": float,    — 已用百分比 (0-100+)
            "exceeded": bool,       — 是否超过 100%
            "warning": bool,        — 是否达到 80% 预警线
        }
    """
    try:
        limit = getattr(settings, 'MAX_DAILY_LLM_COST_USD', 50.0)
    except Exception:
        limit = 50.0

    daily_cost = get_daily_cost()
    percentage = (daily_cost / limit * 100.0) if limit > 0 else 0.0

    return {
        "daily_cost": daily_cost,
        "limit": limit,
        "percentage": percentage,
        "exceeded": percentage >= 100.0,
        "warning": percentage >= 80.0,
    }


def send_feishu_warning(percentage: float) -> None:
    """发送飞书费用预警消息。

    如果飞书 Bot 不可用，只记录日志。

    Args:
        percentage: 已用百分比 (0-100+)
    """
    message = (
        f"⚠️ LLM 费用预警：今日已消耗每日上限的 {percentage:.1f}%，请注意控制 LLM 调用量。"
    )
    logger.warning(f"飞书预警: {message}")

    try:
        chat_id = getattr(settings, 'FEISHU_TEST_CHAT_ID', None)
        if not chat_id:
            logger.info("未配置 FEISHU_TEST_CHAT_ID，跳过飞书消息发送")
            return

        bot = get_bot()
        bot.send_text_message(chat_id=chat_id, text=message)
        logger.info("飞书费用预警发送成功")
    except Exception as e:
        logger.warning(f"飞书预警发送失败（只记录日志）: {e}")
