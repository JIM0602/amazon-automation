"""飞书消息命令路由模块：根据消息内容分发到不同业务处理器。"""
from __future__ import annotations


def route_command(message: str, sender_id: str) -> dict:
    """根据消息内容路由到不同处理器。

    路由规则（优先级从高到低）：
    - 消息以 "?" 或 "？" 开头 → 知识库问答
    - 消息包含 "暂停所有" 或 "紧急停机" → 紧急停机
    - 消息为 "帮助" 或 "help"（不区分大小写）→ 帮助指令列表
    - 消息包含 "日报" 或 "报告"  → 触发日报
    - 消息包含 "选品"            → 触发选品分析
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
            "  暂停所有 / 紧急停机    — 紧急停止所有运营任务\n"
            "  帮助 / help            — 显示本帮助列表\n"
        )
        return {"action": "help", "message": help_text, "sender_id": sender_id}

    # 4. 日报 / 报告
    if "日报" in stripped or "报告" in stripped or "今日报告" in stripped:
        return {"action": "daily_report", "sender_id": sender_id}

    # 5. 选品分析
    if "选品" in stripped:
        return {"action": "selection_analysis", "sender_id": sender_id}

    # 6. 未知命令 — 返回帮助提示
    help_text = (
        "👋 你好！我是 PUDIWIND AI 助手，支持以下命令：\n"
        "  ?<问题>  — 向知识库提问，例如：?如何处理差评\n"
        "  日报     — 生成今日运营日报\n"
        "  选品     — 启动选品分析\n"
        "  帮助     — 查看完整指令列表\n"
        "如需帮助，请输入以上关键词。"
    )
    return {"action": "unknown", "message": help_text, "sender_id": sender_id}
