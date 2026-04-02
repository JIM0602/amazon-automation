"""Policy Engine — 内置规则定义。

内置规则分三类：
1. 价格规则（decision_type: "price_adjustment"）
   - PriceMaxChangePctRule:   单次调价幅度 ≤ 20%
   - PriceMinCostRule:        价格不低于成本价 × (1 + min_margin)
   - PriceMaxDailyChangesRule: 当日调价次数 ≤ 3

2. 广告规则（decision_type: "ad_budget" | "ad_keyword"）
   - AdMaxDailyBudgetRule:    单日预算 ≤ 上限
   - AdAcosThresholdRule:     ACoS 超阈值时阻止加投
   - AdMaxKeywordBidRule:     关键词出价 ≤ 上限

3. 库存规则（decision_type: "inventory_replenishment"）
   - InvMaxReplenishUnitsRule: 单次补货 ≤ 上限
   - InvSafetyStockWarningRule: 安全库存预警

payload 字段约定（见各规则 docstring）。
"""
from __future__ import annotations

import logging
from typing import List

from src.policy.config import get_policy_config
from src.policy.models import Rule, Violation, Warning

logger = logging.getLogger(__name__)


# ===========================================================================
# 1. 价格规则
# ===========================================================================

class PriceMaxChangePctRule(Rule):
    """单次调价幅度不超过配置的最大百分比（默认 20%）。

    payload 必须字段：
        current_price (float): 当前价格（正数）
        new_price     (float): 目标价格（正数）

    payload 可选字段：
        sku           (str):   SKU 标识（用于错误信息）
    """

    rule_id = "price.max_change_pct"
    rule_name = "单次调价幅度限制"
    applicable_decision_types = ["price_adjustment"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        current = payload.get("current_price")
        new_price = payload.get("new_price")

        if current is None or new_price is None:
            return [], []  # 缺少字段，跳过（不惩罚）

        if current <= 0:
            return [], []  # 无效价格，跳过

        change_pct = abs(new_price - current) / current
        threshold = cfg.price_max_change_pct

        if change_pct > threshold:
            sku = payload.get("sku", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"调价幅度 {change_pct:.1%} 超过限制 {threshold:.1%}"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="new_price",
                    actual=round(change_pct, 4),
                    threshold=threshold,
                )
            ], []

        return [], []


class PriceMinCostRule(Rule):
    """价格不得低于成本价 × (1 + min_margin)。

    payload 必须字段：
        new_price  (float): 目标价格（正数）
        cost_price (float): 成本价（正数）

    payload 可选字段：
        sku (str): SKU 标识
    """

    rule_id = "price.min_cost"
    rule_name = "最低成本价格限制"
    applicable_decision_types = ["price_adjustment"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        new_price = payload.get("new_price")
        cost_price = payload.get("cost_price")

        if new_price is None or cost_price is None:
            return [], []

        if cost_price <= 0:
            return [], []

        min_allowed = cost_price * (1 + cfg.price_min_margin)

        if new_price < min_allowed:
            sku = payload.get("sku", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"目标价格 {new_price:.2f} 低于最低允许价格 {min_allowed:.2f}"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="new_price",
                    actual=new_price,
                    threshold=min_allowed,
                )
            ], []

        return [], []


class PriceMaxDailyChangesRule(Rule):
    """单日调价次数不超过限制（默认 3 次）。

    payload 必须字段：
        daily_change_count (int): 今日已调价次数（含本次）

    payload 可选字段：
        sku (str): SKU 标识
    """

    rule_id = "price.max_daily_changes"
    rule_name = "每日调价次数限制"
    applicable_decision_types = ["price_adjustment"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        daily_count = payload.get("daily_change_count")
        if daily_count is None:
            return [], []

        threshold = cfg.price_max_daily_changes

        if daily_count > threshold:
            sku = payload.get("sku", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"今日已调价 {daily_count} 次，超过每日限制 {threshold} 次"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="daily_change_count",
                    actual=daily_count,
                    threshold=threshold,
                )
            ], []

        # 达到上限时给出警告
        if daily_count == threshold:
            sku = payload.get("sku", "")
            return [], [
                Warning(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"今日调价次数已达上限 {threshold} 次"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="daily_change_count",
                )
            ]

        return [], []


# ===========================================================================
# 2. 广告规则
# ===========================================================================

class AdMaxDailyBudgetRule(Rule):
    """单日广告预算不超过上限（默认 500 美元）。

    payload 必须字段：
        daily_budget_usd (float): 目标单日预算（美元）

    payload 可选字段：
        campaign_id (str): 广告活动 ID
    """

    rule_id = "ad.max_daily_budget"
    rule_name = "每日广告预算上限"
    applicable_decision_types = ["ad_budget"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        budget = payload.get("daily_budget_usd")
        if budget is None:
            return [], []

        threshold = cfg.ad_max_daily_budget_usd

        if budget > threshold:
            campaign = payload.get("campaign_id", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"目标日预算 ${budget:.2f} 超过上限 ${threshold:.2f}"
                        + (f"（Campaign: {campaign}）" if campaign else "")
                    ),
                    field="daily_budget_usd",
                    actual=budget,
                    threshold=threshold,
                )
            ], []

        # 超过 80% 时给出警告
        if budget > threshold * 0.8:
            return [], [
                Warning(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=f"目标日预算 ${budget:.2f} 已接近上限 ${threshold:.2f}（{budget/threshold:.0%}）",
                    field="daily_budget_usd",
                )
            ]

        return [], []


class AdAcosThresholdRule(Rule):
    """当 ACoS 超过阈值时阻止加大广告投放（增加预算/出价）。

    判断逻辑：当 current_acos > threshold 且 budget_change_usd > 0（加投）时违规。

    payload 必须字段：
        current_acos      (float): 当前 ACoS（小数，如 0.35 表示 35%）

    payload 可选字段：
        budget_change_usd (float): 预算变化量（正数=加投，负数=减投），默认 0
        bid_change_usd    (float): 出价变化量（正数=提价，负数=降价），默认 0
        campaign_id       (str):   广告活动 ID
    """

    rule_id = "ad.acos_threshold"
    rule_name = "ACoS 超阈值禁止加投"
    applicable_decision_types = ["ad_budget", "ad_keyword"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        current_acos = payload.get("current_acos")
        if current_acos is None:
            return [], []

        threshold = cfg.ad_acos_threshold_pct

        # 检查是否在加投
        budget_change = payload.get("budget_change_usd", 0) or 0
        bid_change = payload.get("bid_change_usd", 0) or 0
        is_increasing = (budget_change > 0) or (bid_change > 0)

        if current_acos > threshold and is_increasing:
            campaign = payload.get("campaign_id", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"当前 ACoS {current_acos:.1%} 超过阈值 {threshold:.1%}，禁止加大投放"
                        + (f"（Campaign: {campaign}）" if campaign else "")
                    ),
                    field="current_acos",
                    actual=current_acos,
                    threshold=threshold,
                )
            ], []

        # ACoS 接近阈值（80%）时警告
        if current_acos > threshold * 0.8:
            return [], [
                Warning(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=f"当前 ACoS {current_acos:.1%} 接近阈值 {threshold:.1%}，请关注",
                    field="current_acos",
                )
            ]

        return [], []


class AdMaxKeywordBidRule(Rule):
    """关键词出价不超过上限（默认 5.0 美元）。

    payload 必须字段：
        keyword_bid_usd (float): 目标出价（美元）

    payload 可选字段：
        keyword         (str):  关键词文本
        campaign_id     (str):  广告活动 ID
    """

    rule_id = "ad.max_keyword_bid"
    rule_name = "关键词出价上限"
    applicable_decision_types = ["ad_keyword"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        bid = payload.get("keyword_bid_usd")
        if bid is None:
            return [], []

        threshold = cfg.ad_max_keyword_bid_usd

        if bid > threshold:
            keyword = payload.get("keyword", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"出价 ${bid:.2f} 超过关键词出价上限 ${threshold:.2f}"
                        + (f"（关键词: {keyword}）" if keyword else "")
                    ),
                    field="keyword_bid_usd",
                    actual=bid,
                    threshold=threshold,
                )
            ], []

        return [], []


# ===========================================================================
# 3. 库存规则
# ===========================================================================

class InvMaxReplenishUnitsRule(Rule):
    """单次补货数量不超过上限（默认 10,000 件）。

    payload 必须字段：
        replenish_units (int): 本次补货数量

    payload 可选字段：
        sku (str): SKU 标识
    """

    rule_id = "inventory.max_replenish_units"
    rule_name = "单次补货数量上限"
    applicable_decision_types = ["inventory_replenishment"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        units = payload.get("replenish_units")
        if units is None:
            return [], []

        if units <= 0:
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=f"补货数量 {units} 必须为正整数",
                    field="replenish_units",
                    actual=units,
                    threshold=1,
                )
            ], []

        threshold = cfg.inv_max_replenish_units

        if units > threshold:
            sku = payload.get("sku", "")
            return [
                Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"补货数量 {units} 件超过单次上限 {threshold} 件"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="replenish_units",
                    actual=units,
                    threshold=threshold,
                )
            ], []

        return [], []


class InvSafetyStockWarningRule(Rule):
    """库存量低于安全库存天数时发出警告（不阻止，仅提示）。

    判断逻辑：当前库存天数 = current_stock_units / daily_sales_units
              如果 < safety_stock_days → 发出警告

    payload 必须字段：
        current_stock_units (int):   当前库存件数
        daily_sales_units   (float): 日均销量（件/天）

    payload 可选字段：
        sku (str): SKU 标识
    """

    rule_id = "inventory.safety_stock_warning"
    rule_name = "安全库存预警"
    applicable_decision_types = ["inventory_replenishment"]

    def check(self, payload: dict) -> tuple[List[Violation], List[Warning]]:
        cfg = get_policy_config()
        if not cfg.is_rule_enabled(self.rule_id):
            return [], []

        current_stock = payload.get("current_stock_units")
        daily_sales = payload.get("daily_sales_units")

        if current_stock is None or daily_sales is None:
            return [], []

        if daily_sales <= 0:
            return [], []

        stock_days = current_stock / daily_sales
        threshold = cfg.inv_safety_stock_days

        if stock_days < threshold:
            sku = payload.get("sku", "")
            return [], [
                Warning(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    message=(
                        f"当前库存仅剩 {stock_days:.1f} 天（安全库存阈值 {threshold} 天）"
                        + (f"（SKU: {sku}）" if sku else "")
                    ),
                    field="current_stock_units",
                )
            ]

        return [], []


# ===========================================================================
# 工厂函数
# ===========================================================================

def get_builtin_rules() -> List[Rule]:
    """返回所有内置规则实例列表。

    规则按 decision_type 分组排列，便于阅读和维护。
    """
    return [
        # 价格规则
        PriceMaxChangePctRule(),
        PriceMinCostRule(),
        PriceMaxDailyChangesRule(),
        # 广告规则
        AdMaxDailyBudgetRule(),
        AdAcosThresholdRule(),
        AdMaxKeywordBidRule(),
        # 库存规则
        InvMaxReplenishUnitsRule(),
        InvSafetyStockWarningRule(),
    ]
