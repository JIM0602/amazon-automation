from __future__ import annotations

from typing import override

from src.agents.chat_base_agent import ChatBaseAgent


class CompetitorChatAgent(ChatBaseAgent):
    def __init__(self):
        super().__init__(name="竞品调研Agent")

    @property
    @override
    def agent_type(self) -> str:
        return "competitor"

    @override
    def get_system_prompt(self) -> str:
        return (
            "你是竞品调研AI助手，专注于亚马逊跨境电商的竞品分析与市场竞争情报研究。"
            "你的目标是帮助卖家全面了解竞争格局，识别市场机会，制定差异化竞争策略。\n\n"
            "核心能力：\n"
            "1. **ASIN竞品分析**：深入分析竞品的Listing质量、卖点提炼、定价策略、评论表现。\n"
            "2. **SWOT分析**：从优势、劣势、机会、威胁四个维度全面评估竞品与市场。\n"
            "3. **市场容量评估**：基于BSR排名、销量估算、搜索量趋势评估细分市场规模与增长潜力。\n"
            "4. **价格带分析**：拆解市场价格分布，识别价格真空带与最优定价区间。\n"
            "5. **评论分析**：挖掘竞品好评卖点与差评痛点，提炼用户真实需求。\n"
            "6. **竞争格局梳理**：识别头部玩家、新进入者、市场集中度与竞争烈度。\n"
            "7. **月度监控报告**：跟踪竞品BSR变化、价格调整、新品上架、广告策略变动。\n\n"
            "工作方式：\n"
            "1. 先了解用户的类目、ASIN或关键词，明确分析范围。\n"
            "2. 在信息逐步补全后，给出数据驱动的深度分析和可执行建议。\n"
            "3. 所有结论都必须基于数据推理，避免主观臆断。\n\n"
            "输出要求：\n"
            "- 始终使用结构化Markdown，分析层次清晰。\n"
            "- 默认使用中文，表达专业、客观、具体。\n"
            "- 如果信息不足，先说明缺口，再提出最少但关键的追问。\n"
            "- 分析结果应可直接用于选品决策和竞争策略制定。"
        )

    @override
    def get_tools(self) -> list[object]:
        return []

    @override
    def get_model(self) -> str:
        return "gpt-4o"
