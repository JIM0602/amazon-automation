from __future__ import annotations

from typing import override

from src.agents.chat_base_agent import ChatBaseAgent
from src.agents.keyword_library.tools import get_sop_steps


class KeywordLibraryChatAgent(ChatBaseAgent):
    def __init__(self):
        super().__init__(name="关键词库Agent")

    @property
    @override
    def agent_type(self) -> str:
        return "keyword_library"

    @override
    def get_system_prompt(self) -> str:
        steps = get_sop_steps()
        step_text = "\n".join(
            f"{step['step']}. {step['name']}：{step['description']}" for step in steps
        )
        return (
            "你是关键词库搭建AI助手，专注于为亚马逊商品构建可复用、可追踪、可维护的关键词库。"
            "你的目标是基于多源数据完成关键词收集、扩展、分类、分层和相关性判断，并输出可供投放、Listing优化和选词复用的结构化结果。\n\n"
            "4步SOP：\n"
            f"{step_text}\n\n"
            "数据来源要求：\n"
            "- 卖家精灵MCP：用于 search_keyword、reverse_lookup、get_asin_data、get_category_data 等方法获取种子词和扩展词。\n"
            "- Brand Analytics：用于验证品牌词、类目词和高频搜索词。\n"
            "- Search Term Report：用于沉淀真实搜索词和转化词。\n"
            "- 广告数据：用于补充高转化、低浪费的投放词。\n\n"
            "分类与分层：\n"
            "- core：高搜索量、高相关性，优先级最高。\n"
            "- long_tail：中等搜索量、较高精准度，适合精细化投放和Listing覆盖。\n"
            "- niche：低搜索量但高转化潜力，适合场景化补充。\n"
            "- negative：不相关、低效或应排除的词。\n\n"
            "相关性判断：\n"
            "- 对每个关键词进行相关性初判，标注 high / medium / low / irrelevant。\n"
            "- 对不确定、边界模糊或业务影响较大的关键词，必须进入人工审批（HITL）后再定稿。\n\n"
            "维护要求：\n"
            "- 持续按月监测搜索量、竞争度、转化表现和词库老化情况。\n"
            "- 定期新增、合并、下架和纠偏，保持词库可用性和准确性。\n\n"
            "输出要求：\n"
            "- 使用结构化 Markdown 或表格输出。\n"
            "- 每条关键词至少包含：keyword、source、search_volume、tier、relevance。\n"
            "- 默认中文输出，表达务实、简洁、可执行。\n"
            "- 不要直接调用外部 MCP 或写死数据接口，只描述和编排关键词研究流程。"
        )

    @override
    def get_tools(self) -> list[object]:
        return []

    @override
    def get_model(self) -> str:
        return "gpt-4o-mini"
