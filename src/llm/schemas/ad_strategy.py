"""广告策略 Schema（预留）。

定义广告策略 Agent 的输出结构（Phase 3 使用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.llm.schemas.base import BaseOutputSchema


class AdKeywordSchema(BaseOutputSchema):
    """广告关键词条目。"""

    keyword: str = Field(..., description="关键词", min_length=1)
    match_type: str = Field(default="broad", description="匹配类型: broad/phrase/exact")
    suggested_bid: float = Field(default=0.0, ge=0.0, description="建议出价 (USD)")
    estimated_impressions: Optional[int] = Field(default=None, ge=0, description="预估曝光量")


class AdCampaignSchema(BaseOutputSchema):
    """广告活动配置。"""

    campaign_name: str = Field(..., description="活动名称", min_length=1)
    asin: str = Field(..., description="目标 ASIN", min_length=1)
    budget_daily: float = Field(default=10.0, ge=0.0, description="每日预算 (USD)")
    targeting_type: str = Field(
        default="auto", description="定向类型: auto/manual/product"
    )
    keywords: List[AdKeywordSchema] = Field(
        default_factory=list, description="关键词列表"
    )
    start_date: Optional[str] = Field(default=None, description="开始日期 (YYYY-MM-DD)")
    notes: Optional[str] = Field(default=None, description="备注")


class AdStrategySchema(BaseOutputSchema):
    """广告策略完整结果 Schema（预留，Phase 3 使用）。"""

    category: str = Field(..., description="目标类目", min_length=1)
    strategy_date: str = Field(..., description="策略日期 (YYYY-MM-DD)")
    campaigns: List[AdCampaignSchema] = Field(
        default_factory=list, description="广告活动列表"
    )
    total_budget_daily: float = Field(default=0.0, ge=0.0, description="总每日预算 (USD)")
    strategy_notes: Optional[str] = Field(default=None, description="策略说明")
    agent_run_id: Optional[str] = Field(default=None, description="Agent 运行 ID")

    @field_validator("strategy_date")
    @classmethod
    def validate_strategy_date(cls, v: str) -> str:
        """日期格式校验。"""
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"strategy_date 格式错误，应为 YYYY-MM-DD，实际为: {v!r}")
        return v
