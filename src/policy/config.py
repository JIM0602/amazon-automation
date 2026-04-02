"""Policy Engine — 规则阈值配置。

所有规则阈值通过此模块统一管理，优先读取环境变量。
使用前缀 POLICY_ 区分，全部提供合理默认值。

环境变量命名规范：
  POLICY_{规则分类}_{阈值名称}
  例如：POLICY_PRICE_MAX_CHANGE_PCT=0.20
"""
from __future__ import annotations

import os
from typing import Optional


def _get_float(key: str, default: float) -> float:
    """从环境变量读取 float，读取失败时返回默认值。"""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _get_int(key: str, default: int) -> int:
    """从环境变量读取 int，读取失败时返回默认值。"""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    """从环境变量读取 bool（'true'/'1' → True），读取失败时返回默认值。"""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.lower() in ("true", "1", "yes")


class PolicyConfig:
    """规则引擎配置（从环境变量读取，含合理默认值）。

    价格规则
    --------
    POLICY_PRICE_MAX_CHANGE_PCT    单次调价最大幅度，默认 0.20（20%）
    POLICY_PRICE_MIN_MARGIN        最低利润率（价格 vs 成本），默认 0.0（不低于成本）
    POLICY_PRICE_MAX_DAILY_CHANGES 单日最多调价次数，默认 3

    广告规则
    --------
    POLICY_AD_MAX_DAILY_BUDGET_USD  单日广告预算上限（美元），默认 500.0
    POLICY_AD_ACOS_THRESHOLD_PCT    ACoS 阻止加投阈值，默认 0.50（50%）
    POLICY_AD_MAX_KEYWORD_BID_USD   关键词出价上限（美元），默认 5.0

    库存规则
    --------
    POLICY_INV_MAX_REPLENISH_UNITS  单次补货上限，默认 10000
    POLICY_INV_SAFETY_STOCK_DAYS    安全库存预警天数，默认 14

    规则开关
    --------
    POLICY_RULE_{RULE_ID}_ENABLED   启用/禁用特定规则，如 POLICY_RULE_PRICE_MAX_CHANGE_PCT_ENABLED=false
    """

    # ----- 价格规则 -----
    @property
    def price_max_change_pct(self) -> float:
        """单次调价最大幅度（百分比，如 0.20 = 20%）。"""
        return _get_float("POLICY_PRICE_MAX_CHANGE_PCT", 0.20)

    @property
    def price_min_margin(self) -> float:
        """最低利润率（0.0 = 不低于成本价）。"""
        return _get_float("POLICY_PRICE_MIN_MARGIN", 0.0)

    @property
    def price_max_daily_changes(self) -> int:
        """单日最多调价次数。"""
        return _get_int("POLICY_PRICE_MAX_DAILY_CHANGES", 3)

    # ----- 广告规则 -----
    @property
    def ad_max_daily_budget_usd(self) -> float:
        """单日广告预算上限（美元）。"""
        return _get_float("POLICY_AD_MAX_DAILY_BUDGET_USD", 500.0)

    @property
    def ad_acos_threshold_pct(self) -> float:
        """ACoS 阻止加投阈值（百分比，如 0.50 = 50%）。"""
        return _get_float("POLICY_AD_ACOS_THRESHOLD_PCT", 0.50)

    @property
    def ad_max_keyword_bid_usd(self) -> float:
        """关键词出价上限（美元）。"""
        return _get_float("POLICY_AD_MAX_KEYWORD_BID_USD", 5.0)

    # ----- 库存规则 -----
    @property
    def inv_max_replenish_units(self) -> int:
        """单次补货上限（件数）。"""
        return _get_int("POLICY_INV_MAX_REPLENISH_UNITS", 10000)

    @property
    def inv_safety_stock_days(self) -> int:
        """安全库存预警天数（低于此值发出警告）。"""
        return _get_int("POLICY_INV_SAFETY_STOCK_DAYS", 14)

    # ----- 规则开关 -----
    def is_rule_enabled(self, rule_id: str, default: bool = True) -> bool:
        """查询特定规则是否启用。

        环境变量格式：POLICY_RULE_{RULE_ID_UPPER}_ENABLED=false
        例：POLICY_RULE_PRICE_MAX_CHANGE_PCT_ENABLED=false
        """
        env_key = f"POLICY_RULE_{rule_id.replace('.', '_').upper()}_ENABLED"
        return _get_bool(env_key, default)


# 模块级单例
_config: Optional[PolicyConfig] = None


def get_policy_config() -> PolicyConfig:
    """返回全局 PolicyConfig 单例。"""
    global _config
    if _config is None:
        _config = PolicyConfig()
    return _config
