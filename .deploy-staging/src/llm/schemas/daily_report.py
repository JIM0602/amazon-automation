"""日报 Schema。

定义 daily_report_agent 的输出结构。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.llm.schemas.base import BaseOutputSchema


class ChangeStatsSchema(BaseOutputSchema):
    """环比变化数据。"""

    pct: float = Field(default=0.0, description="变化百分比")
    direction: str = Field(default="flat", description="方向: up/down/flat")
    emoji: str = Field(default="→", description="方向 emoji")
    color: str = Field(default="grey", description="颜色标签")


class SkuRankItemSchema(BaseOutputSchema):
    """SKU 销量排行条目。"""

    rank: int = Field(..., ge=1, description="排名")
    asin: str = Field(..., description="ASIN")
    name: str = Field(default="", description="产品名称")
    qty: int = Field(default=0, ge=0, description="销量")


class SalesDataSchema(BaseOutputSchema):
    """销售数据板块。"""

    date: str = Field(..., description="报告日期 (YYYY-MM-DD)")
    revenue: float = Field(default=0.0, ge=0.0, description="总销售额 (USD)")
    orders: int = Field(default=0, ge=0, description="订单数")
    refunds: int = Field(default=0, ge=0, description="退款数")
    revenue_vs_prev_day: Optional[ChangeStatsSchema] = Field(
        default=None, description="与前日对比"
    )
    orders_vs_prev_day: Optional[ChangeStatsSchema] = Field(
        default=None, description="订单与前日对比"
    )
    revenue_vs_last_week: Optional[ChangeStatsSchema] = Field(
        default=None, description="与上周同期对比"
    )
    sku_ranking: List[SkuRankItemSchema] = Field(
        default_factory=list, description="SKU 销量排行"
    )


class AgentStatusSchema(BaseOutputSchema):
    """单个 Agent 状态。"""

    agent_type: str = Field(..., description="Agent 类型")
    status: str = Field(default="not_run", description="运行状态: success/failed/running/not_run")
    last_run: Optional[str] = Field(default=None, description="最后运行时间")
    run_count: int = Field(default=0, ge=0, description="运行次数")


class AgentProgressSchema(BaseOutputSchema):
    """Agent 任务进度板块。"""

    agent_statuses: List[AgentStatusSchema] = Field(
        default_factory=list, description="各 Agent 状态列表"
    )
    pending_approvals: int = Field(default=0, ge=0, description="待审批任务数")


class MarketDataReportSchema(BaseOutputSchema):
    """市场动态板块。"""

    category: Optional[str] = Field(default=None, description="类目名称")
    market_size_usd: Optional[float] = Field(default=None, ge=0.0, description="市场规模 (USD)")
    growth_rate: Optional[float] = Field(default=None, description="增长率")
    top_keywords: List[str] = Field(default_factory=list, description="热门关键词")
    competitor_alert: Optional[str] = Field(default=None, description="竞品动态")
    inventory_alerts: List[str] = Field(default_factory=list, description="库存告警列表")


class DailyReportSchema(BaseOutputSchema):
    """日报完整结果 Schema（daily_report_agent 主输出）。"""

    report_date: str = Field(..., description="报告日期 (YYYY-MM-DD)")
    agent_run_id: str = Field(default="", description="Agent 运行 ID")
    sales: SalesDataSchema = Field(
        default_factory=SalesDataSchema.model_construct,
        description="销售数据板块",
    )
    agent_progress: AgentProgressSchema = Field(
        default_factory=AgentProgressSchema,
        description="Agent 进度板块",
    )
    market: MarketDataReportSchema = Field(
        default_factory=MarketDataReportSchema,
        description="市场动态板块",
    )
    status: str = Field(default="completed", description="报告状态: completed/failed")
    generated_at: str = Field(default="", description="生成时间 (ISO 格式)")
    dry_run: bool = Field(default=True, description="是否 dry run 模式")

    @field_validator("report_date")
    @classmethod
    def validate_report_date(cls, v: str) -> str:
        """日期格式校验。"""
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"report_date 格式错误，应为 YYYY-MM-DD，实际为: {v!r}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """状态值校验。"""
        allowed = {"completed", "failed", "running"}
        if v not in allowed:
            raise ValueError(f"status 必须为 {allowed} 之一，实际为: {v!r}")
        return v
