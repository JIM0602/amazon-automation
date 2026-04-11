"""飞书消息命令路由模块：根据消息内容分发到不同业务处理器。"""
from __future__ import annotations

import re


def _parse_listing_command(message: str) -> dict:
    """解析 /listing generate 命令参数。

    支持格式：
      /listing generate asin=B0XXX
      /listing generate asin=B0XXX product=产品名称 category=类目

    Args:
        message: 原始命令消息

    Returns:
        包含解析参数的字典
    """
    params = {}

    # 提取 asin（亚马逊ASIN通常是10位字母数字，但允许更灵活的格式）
    asin_match = re.search(r'asin\s*=\s*([A-Z0-9]{10,})', message, re.IGNORECASE)
    if asin_match:
        params["asin"] = asin_match.group(1).upper()

    # 提取 product
    product_match = re.search(r'product\s*=\s*([^\s]+(?:\s+[^\s=]+)*?)(?=\s+\w+=|\s*$)', message)
    if product_match:
        params["product_name"] = product_match.group(1).strip()

    # 提取 category
    cat_match = re.search(r'category\s*=\s*([^\s]+)', message)
    if cat_match:
        params["category"] = cat_match.group(1).strip()

    return params


def route_command(message: str, sender_id: str) -> dict:
    """根据消息内容路由到不同处理器。

    路由规则（优先级从高到低）：
    - 消息以 "?" 或 "？" 开头 → 知识库问答
    - 消息包含 "暂停所有" 或 "紧急停机" → 紧急停机
    - 消息为 "帮助" 或 "help"（不区分大小写）→ 帮助指令列表
    - 消息包含 "日报" 或 "报告"  → 触发日报
    - 消息包含 "选品"            → 触发选品分析
    - 消息包含 "/listing generate" → 触发Listing文案生成
    - 其他                      → 未知命令（返回帮助提示）

    Args:
        message:   用户发送的原始文本消息（已去除前后空白）。
        sender_id: 发送者的飞书 open_id，供业务层追踪使用。

    Returns:
        包含 ``action`` 键的 dict，各路由的返回格式见下文。
    """
    stripped = message.strip()

    # 1. 知识库问答（"问："或"？"或"?" 开头）
    if stripped.startswith("?") or stripped.startswith("？") or stripped.startswith("问："):
        # 去掉首个前缀后的内容作为查询词
        if stripped.startswith("问："):
            query = stripped[2:].strip()
        else:
            query = stripped[1:].strip()
        return {"action": "knowledge_query", "query": query, "sender_id": sender_id}

    # 2. 紧急停机
    if "暂停所有" in stripped or "紧急停机" in stripped:
        return {"action": "emergency_stop", "sender_id": sender_id}

    # 3. 帮助指令列表
    if stripped.lower() in ("帮助", "help"):
        help_text = (
            "📋 **PUDIWIND AI 助手指令列表**\n\n"
            "  问：<问题> 或 ?<问题>  — 向知识库提问，例如：?如何处理差评\n"
            "  今日报告 / 日报         — 生成今日运营日报\n"
            "  选品分析               — 启动选品分析\n"
            "  /listing generate asin=B0XXX  — 生成Listing文案（支持参数：asin, category）\n"
            "  暂停所有 / 紧急停机    — 紧急停止所有运营任务\n"
            "  帮助 / help            — 显示本帮助列表\n"
        )
        return {"action": "help", "message": help_text, "sender_id": sender_id}

    # 4. 日报 / 报告 — 路由到 DailyReportAgent
    _DAILY_REPORT_KEYWORDS = ["日报", "报告", "今日报告", "运营报告", "数据报告", "每日报告"]
    if any(kw in stripped for kw in _DAILY_REPORT_KEYWORDS):
        return {"action": "daily_report", "sender_id": sender_id}

    # 5. 选品分析
    if "选品" in stripped:
        return {"action": "selection_analysis", "sender_id": sender_id}

    # 6. Listing 文案生成（/listing generate asin=B0XXX）
    if "/listing" in stripped.lower() or "listing generate" in stripped.lower():
        params = _parse_listing_command(stripped)
        return {
            "action": "listing_generate",
            "sender_id": sender_id,
            "asin": params.get("asin", ""),
            "product_name": params.get("product_name", ""),
            "category": params.get("category", ""),
        }

    # 7. 未知命令 — 返回帮助提示
    help_text = (
        "👋 你好！我是 PUDIWIND AI 助手，支持以下命令：\n"
        "  ?<问题>  — 向知识库提问，例如：?如何处理差评\n"
        "  日报     — 生成今日运营日报\n"
        "  选品     — 启动选品分析\n"
        "  /listing generate asin=B0XXX  — 生成Listing文案\n"
        "  帮助     — 查看完整指令列表\n"
        "如需帮助，请输入以上关键词。"
    )
    return {"action": "unknown", "message": help_text, "sender_id": sender_id}
