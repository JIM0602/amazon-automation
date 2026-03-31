"""飞书消息命令路由模块：根据消息内容分发到不同业务处理器。"""
from __future__ import annotations


def route_command(message: str, sender_id: str) -> dict:
    """根据消息内容路由到不同处理器。

    路由规则（优先级从高到低）：
    - 消息以 "?" 或 "？" 开头 → 知识库问答
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

    # 1. 知识库问答
    if stripped.startswith("?") or stripped.startswith("？"):
        # 去掉首个问号后的内容作为查询词
        query = stripped[1:].strip()
        return {"action": "knowledge_query", "query": query, "sender_id": sender_id}

    # 2. 日报 / 报告
    if "日报" in stripped or "报告" in stripped:
        return {"action": "daily_report", "sender_id": sender_id}

    # 3. 选品分析
    if "选品" in stripped:
        return {"action": "selection_analysis", "sender_id": sender_id}

    # 4. 未知命令 — 返回帮助提示
    help_text = (
        "👋 你好！我是 PUDIWIND AI 助手，支持以下命令：\n"
        "  ?<问题>  — 向知识库提问，例如：?如何处理差评\n"
        "  日报     — 生成今日运营日报\n"
        "  选品     — 启动选品分析\n"
        "如需帮助，请输入以上关键词。"
    )
    return {"action": "unknown", "message": help_text, "sender_id": sender_id}
