from __future__ import annotations

from typing import override

from src.agents.ad_monitor_agent.algorithm import (
    AdOptimizer,
    Campaign,
    KeywordPerformance,
    OptimizationResult,
    calculate_acos,
    calculate_roas,
)
from src.agents.ad_monitor_agent.simulation import (
    HistoricalDataLoader,
    SimulationConfig,
    SimulationEngine,
    SimulationMode,
    SimulationReporter,
    SimulationInput,
)

from src.agents.chat_base_agent import ChatBaseAgent


class AdMonitorChatAgent(ChatBaseAgent):
    def __init__(self):
        super().__init__(name="广告监控Agent")

    @property
    @override
    def agent_type(self) -> str:
        return "ad_monitor"

    @override
    def get_system_prompt(self) -> str:
        return (
            "你是亚马逊广告优化AI助手，专注于广告活动监控、效果分析与投放策略优化。"
            "你的核心目标是帮助卖家最大化广告投资回报，降低无效花费，持续提升广告表现。\n\n"
            "核心能力：\n"
            "1. **广告活动分析**：全面评估SP/SB/SD各类广告活动表现，"
            "识别高效与低效活动，发现优化机会。\n"
            "2. **核心指标优化**：深度分析ACoS、ROAS、CTR、CVR四大核心指标，"
            "基于行业基准和历史趋势给出优化方向。\n"
            "3. **竞价策略建议**：根据关键词竞争度、转化率和利润空间，"
            "推荐最优竞价策略（动态竞价-提高和降低/固定竞价/仅降低）。\n"
            "4. **关键词表现管理**：分析搜索词报告，识别高转化词和浪费词，"
            "提供加词、否词、调价的具体操作建议。\n"
            "5. **预算管理**：监控各活动预算消耗速度，识别预算不足或浪费的活动，"
            "给出预算重新分配方案。\n"
            "6. **广告报告生成**：生成日报/周报级别的广告表现汇总，"
            "突出关键变化和需要关注的异常指标。\n\n"
            "可用工具：\n"
            "- run_optimization_analysis：基于示例活动数据运行优化分析，用于竞价、预算和搜索词动作评估。\n"
            "- run_simulation：运行 backtest / what_if / stress_test 仿真，适合做策略对比与情景推演。\n"
            "- get_campaign_summary：获取活动表现摘要，适合先快速了解整体投放状态。\n"
            "- create_optimization_recommendation：创建单条优化审批请求，仅进入审批队列，不执行任何实际变更。\n"
            "- 所有竞价、预算和投放变更都必须先进入审批队列，严禁直接写入 Ads API。\n"
            "- 需要评估策略影响时，优先使用仿真工具做 what-if 分析，再输出待审批建议。\n\n"
            "工作方式：\n"
            "- 分析前先了解：产品类目、目标ACoS、日预算、投放阶段（新品/成熟期）。\n"
            "- 所有优化建议必须具体可执行，包含操作步骤和预期效果。\n"
            "- 区分优先级：立即执行（止损）> 本周执行（优化）> 长期策略（布局）。\n"
            "- 关注广告与自然流量的协同关系，避免过度依赖广告。\n\n"
            "输出要求：\n"
            "- 使用结构化Markdown，指标数据用表格对比呈现。\n"
            "- 默认使用中文，表达专业、数据驱动、结论明确。\n"
            "- 优化建议需注明预估影响幅度（如：预计ACoS可降低3-5个百分点）。\n"
            "- 重要操作建议标注风险等级和回滚方案。"
        )

    @override
    def get_tools(self) -> list[object]:
        return [
            self.run_optimization_analysis,
            self.run_simulation,
            self.get_campaign_summary,
            self.create_optimization_recommendation,
        ]

    def run_optimization_analysis(self, target_acos: float = 30.0, max_bid: float = 3.0) -> str:
        sample = self._build_sample_data()
        optimizer = AdOptimizer(target_acos=target_acos, max_bid=max_bid)
        result = optimizer.optimize(
            sample.campaigns,
            sample.ad_groups,
            sample.keywords,
            search_terms=sample.search_terms,
            placements=sample.placement_data,
            business_context=sample.business_context,
        )
        return self._format_optimization_report(result, sample.campaigns, sample.keywords)

    def run_simulation(
        self,
        mode: str = "backtest",
        days: int = 30,
        target_acos: float = 30.0,
        budget_multiplier: float = 1.0,
    ) -> str:
        loader = HistoricalDataLoader()
        input_data = loader.generate_sample_data(days=days)
        try:
            simulation_mode = SimulationMode(mode.lower())
        except ValueError:
            simulation_mode = SimulationMode.BACKTEST

        config = SimulationConfig(
            mode=simulation_mode,
            days=days,
            target_acos=target_acos,
            budget_multiplier=budget_multiplier,
        )
        result = SimulationEngine().run(input_data, config)
        return SimulationReporter().to_markdown(result)

    def get_campaign_summary(self) -> str:
        sample = self._build_sample_data()
        campaigns = sorted(sample.campaigns, key=lambda item: item.sales, reverse=True)
        lines = [
            "# 广告活动摘要",
            "",
            "## Top Campaigns",
            "| 活动 | 花费 | 销售额 | ACOS | ROAS | 点击 | 订单 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for campaign in campaigns[:5]:
            acos = calculate_acos(campaign.spend, campaign.sales)
            roas = calculate_roas(campaign.sales, campaign.spend)
            lines.append(
                f"| {campaign.name or campaign.campaign_id} | {campaign.spend:.2f} | {campaign.sales:.2f} | {acos:.2f}% | {roas:.2f} | {campaign.clicks} | {campaign.orders} |"
            )
        lines.extend(
            [
                "",
                "## 结论",
                "- 以上为示例数据摘要，后续可替换为 Ads API 读取结果。",
                "- 当前仅用于监控、分析与策略建议，不执行任何写操作。",
            ]
        )
        return "\n".join(lines)

    def create_optimization_recommendation(
        self,
        campaign_name: str,
        keyword: str,
        current_bid: float,
        suggested_bid: float,
        reason: str,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "agent_type": self.agent_type,
            "action_type": "bid_change",
            "approval_required": True,
            "approval_status": "queued_for_approval",
            "campaign_name": campaign_name,
            "keyword": keyword,
            "current_bid": current_bid,
            "suggested_bid": suggested_bid,
            "reason": reason,
            "approval_service": "src.services.approval.ApprovalService.submit_for_review",
            "ads_api_write": False,
        }
        return {
            "message": "优化建议已进入审批队列，等待老板审批后再执行。",
            "payload": payload,
        }

    @override
    def get_model(self) -> str:
        return "gpt-4o"

    def _build_sample_data(self) -> SimulationInput:
        loader = HistoricalDataLoader()
        return loader.generate_sample_data(num_campaigns=3, num_keywords_per=4, days=30)

    def _format_optimization_report(
        self,
        result: OptimizationResult,
        campaigns: list[Campaign],
        keywords: list[KeywordPerformance],
    ) -> str:
        campaign_lookup = {campaign.campaign_id: campaign for campaign in campaigns}
        keyword_lookup = {keyword.keyword_id: keyword for keyword in keywords}

        lines = [
            "# 优化分析报告",
            "",
            f"- 摘要：{result.summary or '无'}",
            "- 状态：所有建议均为需审批，未执行任何 Ads API 写操作。",
            "",
            "## 竞价建议",
            "| 活动 | 关键词 | 当前出价 | 建议出价 | 方向 | 置信度 | 状态 | 原因 |",
            "|---|---|---:|---:|---|---|---|---|",
        ]

        if result.bid_recommendations:
            for rec in result.bid_recommendations:
                keyword = keyword_lookup.get(rec.keyword_id)
                campaign = campaign_lookup.get(rec.campaign_id)
                lines.append(
                    f"| {campaign.name if campaign else rec.campaign_id} | {keyword.keyword_text if keyword else rec.keyword_id} | {rec.current_bid:.2f} | {rec.suggested_bid:.2f} | {rec.direction.value} | {rec.confidence.value} | 需审批 | {rec.reason} |"
                )
        else:
            lines.append("| - | - | - | - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## 预算建议",
                "| 活动 | 当前预算 | 建议预算 | 置信度 | 状态 | 原因 |",
                "|---|---:|---:|---|---|---|",
            ]
        )
        if result.budget_recommendations:
            for rec in result.budget_recommendations:
                campaign = campaign_lookup.get(rec.campaign_id)
                lines.append(
                    f"| {campaign.name if campaign else rec.campaign_id} | {rec.current_budget:.2f} | {rec.suggested_budget:.2f} | {rec.confidence.value} | 需审批 | {rec.reason} |"
                )
        else:
            lines.append("| - | - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## 搜索词动作",
                "| 搜索词 | 活动 | 动作 | 说明 | 状态 |",
                "|---|---|---|---|---|",
            ]
        )
        if result.search_term_actions:
            for action in result.search_term_actions:
                campaign = campaign_lookup.get(action.campaign_id)
                lines.append(
                    f"| {action.search_term} | {campaign.name if campaign else action.campaign_id} | {action.action} | {action.reason} | 需审批 |"
                )
        else:
            lines.append("| - | - | - | - | - |")

        lines.extend(
            [
                "",
                "## 备注",
                "- 预算、竞价、搜索词动作都需要走审批队列。",
                "- 仅提供建议，不直接写入广告平台。",
            ]
        )
        return "\n".join(lines)
