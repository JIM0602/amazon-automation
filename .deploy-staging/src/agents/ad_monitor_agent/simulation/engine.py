from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from src.agents.ad_monitor_agent.algorithm import (
    AdOptimizer,
    BidDirection,
    BidRecommendation,
    BusinessContext,
    Campaign,
    DaypartPerformance,
    KeywordPerformance,
    OptimizationResult,
    PlacementPerformance,
    SearchTermPerformance,
    calculate_acos,
    calculate_roas,
)

from .data_loader import HistoricalDataLoader, SimulationInput


class SimulationMode(str, Enum):
    BACKTEST = "backtest"
    WHAT_IF = "what_if"
    STRESS_TEST = "stress_test"


@dataclass(slots=True)
class SimulationConfig:
    mode: SimulationMode
    days: int = 30
    target_acos: float = 30.0
    budget_multiplier: float = 1.0
    cpc_multiplier: float = 1.0
    conversion_multiplier: float = 1.0
    stress_scenario: str = ""


@dataclass(slots=True)
class SimulationResult:
    mode: SimulationMode
    config: SimulationConfig
    actual_acos: float = 0.0
    actual_roas: float = 0.0
    actual_spend: float = 0.0
    actual_sales: float = 0.0
    simulated_acos: float = 0.0
    simulated_roas: float = 0.0
    simulated_spend: float = 0.0
    simulated_sales: float = 0.0
    acos_improvement_pct: float = 0.0
    roas_improvement_pct: float = 0.0
    spend_change_pct: float = 0.0
    sales_change_pct: float = 0.0
    recommendations_count: int = 0
    safety_blocks_count: int = 0
    confidence_level: str = ""
    risk_assessment: str = ""
    disclaimer: str = "⚠️ 以上结果为模拟推算，非实际保证。实际效果受市场竞争、季节性等因素影响。"
    daily_comparison: list[dict[str, Any]] = field(default_factory=list)
    recommendation_details: list[dict[str, Any]] = field(default_factory=list)


class SimulationEngine:
    """Test harness for the AdOptimizer algorithm."""

    def __init__(self):
        self.data_loader = HistoricalDataLoader()

    def run(self, data: dict[str, Any] | SimulationInput, config: SimulationConfig) -> SimulationResult:
        input_data = self.data_loader.load_from_dict(data) if isinstance(data, dict) else data
        if config.mode == SimulationMode.WHAT_IF:
            return self._run_what_if(input_data, config)
        if config.mode == SimulationMode.STRESS_TEST:
            return self._run_stress_test(input_data, config)
        return self._run_backtest(input_data, config)

    def _run_backtest(self, input_data: SimulationInput, config: SimulationConfig) -> SimulationResult:
        actual = self._calculate_actual_metrics(input_data.keywords)
        optimizer = AdOptimizer(target_acos=config.target_acos)
        optimization = optimizer.optimize(
            input_data.campaigns,
            input_data.ad_groups,
            input_data.keywords,
            search_terms=input_data.search_terms,
            placements=input_data.placement_data,
            business_context=input_data.business_context,
        )
        simulated = self._simulate_recommendations(input_data.keywords, optimization)
        result = self._build_result(config, actual, simulated, optimization, input_data)
        result.daily_comparison = self._build_daily_comparison(input_data.hourly_data, actual, simulated, config.days)
        return result

    def _run_what_if(self, input_data: SimulationInput, config: SimulationConfig) -> SimulationResult:
        actual = self._calculate_actual_metrics(input_data.keywords)
        adjusted_keywords = [self._apply_what_if_to_keyword(keyword, config) for keyword in input_data.keywords]
        optimizer = AdOptimizer(target_acos=config.target_acos)
        optimization = optimizer.optimize(
            input_data.campaigns,
            input_data.ad_groups,
            adjusted_keywords,
            search_terms=input_data.search_terms,
            placements=input_data.placement_data,
            business_context=input_data.business_context,
        )
        simulated = self._simulate_recommendations(adjusted_keywords, optimization)
        result = self._build_result(config, actual, simulated, optimization, input_data)
        result.daily_comparison = self._build_daily_comparison(input_data.hourly_data, actual, simulated, config.days)
        return result

    def _run_stress_test(self, input_data: SimulationInput, config: SimulationConfig) -> SimulationResult:
        if config.stress_scenario == "budget_cut_50":
            config = replace(config, budget_multiplier=0.5)
        elif config.stress_scenario == "price_war":
            config = replace(config, cpc_multiplier=2.0)
        elif config.stress_scenario == "seasonal_spike":
            config = replace(config, conversion_multiplier=3.0)

        actual = self._calculate_actual_metrics(input_data.keywords)
        adjusted_keywords = [self._apply_what_if_to_keyword(keyword, config) for keyword in input_data.keywords]
        optimizer = AdOptimizer(target_acos=config.target_acos)
        optimization = optimizer.optimize(
            input_data.campaigns,
            input_data.ad_groups,
            adjusted_keywords,
            search_terms=input_data.search_terms,
            placements=input_data.placement_data,
            business_context=input_data.business_context,
        )
        simulated = self._simulate_recommendations(adjusted_keywords, optimization)
        result = self._build_result(config, actual, simulated, optimization, input_data)
        result.daily_comparison = self._build_daily_comparison(input_data.hourly_data, actual, simulated, config.days)
        return result

    def _calculate_actual_metrics(self, keywords: list[KeywordPerformance]) -> dict[str, float]:
        spend = sum(keyword.spend for keyword in keywords)
        sales = sum(keyword.sales for keyword in keywords)
        return {
            "spend": spend,
            "sales": sales,
            "acos": calculate_acos(spend, sales),
            "roas": calculate_roas(sales, spend),
        }

    def _simulate_recommendations(self, keywords: list[KeywordPerformance], recommendations: OptimizationResult) -> dict[str, float]:
        current_spend = sum(keyword.spend for keyword in keywords)
        current_sales = sum(keyword.sales for keyword in keywords)
        current_cpc = current_spend / max(sum(keyword.clicks for keyword in keywords), 1)
        current_cvr = sum(keyword.orders for keyword in keywords) / max(sum(keyword.clicks for keyword in keywords), 1)
        bid_map = {rec.keyword_id: rec for rec in recommendations.bid_recommendations}

        projected_spend = 0.0
        projected_sales = 0.0
        for keyword in keywords:
            rec = bid_map.get(keyword.keyword_id)
            if rec is None:
                projected_spend += keyword.spend
                projected_sales += keyword.sales
                continue
            bid_ratio = rec.suggested_bid / max(rec.current_bid, 0.05) if rec.current_bid else 1.0
            click_factor = max(0.5, min(1.5, 1 + (bid_ratio - 1) * 0.6))
            conversion_factor = max(0.5, min(1.5, 1 + (rec.suggested_bid - rec.current_bid) * 0.15))
            projected_spend += keyword.spend * click_factor
            projected_sales += keyword.sales * conversion_factor

        # Guard against degenerate math and use some elasticity from the current portfolio.
        if current_spend == 0:
            projected_spend = 0.0
        if current_sales == 0:
            projected_sales = 0.0

        simulated_acos = calculate_acos(projected_spend, projected_sales)
        simulated_roas = calculate_roas(projected_sales, projected_spend)
        return {
            "spend": projected_spend,
            "sales": projected_sales,
            "acos": simulated_acos,
            "roas": simulated_roas,
            "current_cpc": current_cpc,
            "current_cvr": current_cvr,
        }

    def _assess_risk(self, result: SimulationResult) -> str:
        change = max(abs(result.acos_improvement_pct), abs(result.spend_change_pct), abs(result.sales_change_pct))
        if change > 25:
            return "HIGH"
        if change >= 10:
            return "MEDIUM"
        return "LOW"

    def _assess_confidence(self, input_data: SimulationInput) -> str:
        sample_size = len(input_data.keywords)
        if sample_size >= 20:
            return "HIGH"
        if sample_size >= 10:
            return "MEDIUM"
        if sample_size >= 5:
            return "LOW"
        return "VERY_LOW"

    def _build_result(
        self,
        config: SimulationConfig,
        actual: dict[str, float],
        simulated: dict[str, float],
        optimization: OptimizationResult,
        input_data: SimulationInput,
    ) -> SimulationResult:
        result = SimulationResult(mode=config.mode, config=config)
        result.actual_spend = actual["spend"]
        result.actual_sales = actual["sales"]
        result.actual_acos = actual["acos"]
        result.actual_roas = actual["roas"]
        result.simulated_spend = simulated["spend"]
        result.simulated_sales = simulated["sales"]
        result.simulated_acos = simulated["acos"]
        result.simulated_roas = simulated["roas"]
        result.acos_improvement_pct = self._pct_improvement(result.actual_acos, result.simulated_acos, lower_is_better=True)
        result.roas_improvement_pct = self._pct_improvement(result.actual_roas, result.simulated_roas, lower_is_better=False)
        result.spend_change_pct = self._pct_change(result.actual_spend, result.simulated_spend)
        result.sales_change_pct = self._pct_change(result.actual_sales, result.simulated_sales)
        result.recommendations_count = len(optimization.bid_recommendations)
        result.safety_blocks_count = sum(1 for rec in optimization.bid_recommendations if rec.direction == BidDirection.HOLD)
        result.confidence_level = self._assess_confidence(input_data)
        result.risk_assessment = self._assess_risk(result)
        result.recommendation_details = [
            {
                "keyword_id": rec.keyword_id,
                "current_bid": rec.current_bid,
                "suggested_bid": rec.suggested_bid,
                "direction": rec.direction.value,
                "confidence": rec.confidence.value,
                "reason": rec.reason,
                "campaign_id": rec.campaign_id,
                "ad_group_id": rec.ad_group_id,
                "phase": rec.phase.value if rec.phase else None,
                "safety_notes": list(rec.safety_notes),
            }
            for rec in optimization.bid_recommendations
        ]
        return result

    def _build_daily_comparison(
        self,
        hourly_data: list[DaypartPerformance],
        actual: dict[str, float],
        simulated: dict[str, float],
        days: int,
    ) -> list[dict[str, Any]]:
        if not hourly_data:
            return []
        average_hourly_spend = sum(item.spend for item in hourly_data) / len(hourly_data)
        average_hourly_sales = sum(item.sales for item in hourly_data) / len(hourly_data)
        comparisons: list[dict[str, Any]] = []
        for day in range(min(days, len(hourly_data))):
            actual_spend = average_hourly_spend * (1 + day * 0.01)
            simulated_spend = actual_spend * (simulated["spend"] / max(actual["spend"], 1e-9)) if actual["spend"] else 0.0
            actual_sales = average_hourly_sales * (1 + day * 0.008)
            simulated_sales = actual_sales * (simulated["sales"] / max(actual["sales"], 1e-9)) if actual["sales"] else 0.0
            comparisons.append(
                {
                    "date": f"day-{day + 1}",
                    "actual_acos": calculate_acos(actual_spend, actual_sales),
                    "simulated_acos": calculate_acos(simulated_spend, simulated_sales),
                    "actual_roas": calculate_roas(actual_sales, actual_spend),
                    "simulated_roas": calculate_roas(simulated_sales, simulated_spend),
                }
            )
        return comparisons

    def _apply_what_if_to_keyword(self, keyword: KeywordPerformance, config: SimulationConfig) -> KeywordPerformance:
        adjusted_spend = keyword.spend * config.budget_multiplier * config.cpc_multiplier
        adjusted_sales = keyword.sales * config.conversion_multiplier
        adjusted_clicks = keyword.clicks * max(config.budget_multiplier, 0.1) * max(config.cpc_multiplier, 0.1)
        return KeywordPerformance(
            keyword_id=keyword.keyword_id,
            campaign_id=keyword.campaign_id,
            ad_group_id=keyword.ad_group_id,
            keyword_text=keyword.keyword_text,
            match_type=keyword.match_type,
            current_bid=max(0.01, keyword.current_bid * config.cpc_multiplier),
            clicks=int(round(adjusted_clicks)),
            orders=keyword.orders,
            spend=adjusted_spend,
            sales=adjusted_sales,
            impressions=keyword.impressions,
            days_active=keyword.days_active,
            bid_history=list(keyword.bid_history),
            attributes=dict(keyword.attributes),
        )

    def _pct_change(self, actual: float, simulated: float) -> float:
        if actual == 0:
            return 0.0
        return ((simulated - actual) / actual) * 100.0

    def _pct_improvement(self, actual: float, simulated: float, *, lower_is_better: bool) -> float:
        if actual == 0:
            return 0.0
        if lower_is_better:
            return ((actual - simulated) / actual) * 100.0
        return ((simulated - actual) / actual) * 100.0
