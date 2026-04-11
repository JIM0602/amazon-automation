"""广告监控Agent Schema — 使用Pydantic定义数据结构。

包含：
  - AdMetrics      — 广告指标快照
  - AlertLevel     — 告警级别常量
  - AdAlert        — 单条告警记录
  - AdMonitorState — LangGraph工作流状态
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False
    BaseModel = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# 告警级别常量
# ---------------------------------------------------------------------------

class AlertLevel:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_VALID_ALERT_LEVELS = {AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL}


# ---------------------------------------------------------------------------
# Pydantic 输出 Schema
# ---------------------------------------------------------------------------

if _PYDANTIC_AVAILABLE:
    class AdMetrics(BaseModel):
        """广告活动指标快照（使用Pydantic验证）。"""

        campaign_id: str = Field(default="", description="广告活动ID")
        campaign_name: str = Field(default="", description="广告活动名称")
        acos: float = Field(default=0.0, description="ACoS百分比，如35.5表示35.5%")
        roas: float = Field(default=0.0, description="ROAS广告支出回报率，如2.8")
        ctr: float = Field(default=0.0, description="CTR点击率百分比")
        cvr: float = Field(default=0.0, description="CVR转化率百分比")
        spend: float = Field(default=0.0, description="花费（美元）")
        sales: float = Field(default=0.0, description="销售额（美元）")
        impressions: int = Field(default=0, description="展示次数")
        clicks: int = Field(default=0, description="点击次数")
        date: str = Field(default="", description="日期（YYYY-MM-DD）")

        @field_validator("acos")
        @classmethod
        def acos_must_be_non_negative(cls, v: float) -> float:
            if v < 0:
                raise ValueError(f"ACoS不能为负数，实际值: {v}")
            return v

        @field_validator("roas")
        @classmethod
        def roas_must_be_non_negative(cls, v: float) -> float:
            if v < 0:
                raise ValueError(f"ROAS不能为负数，实际值: {v}")
            return v

        @field_validator("spend")
        @classmethod
        def spend_must_be_non_negative(cls, v: float) -> float:
            if v < 0:
                raise ValueError(f"花费不能为负数，实际值: {v}")
            return v

        def to_dict(self) -> Dict[str, Any]:
            return self.model_dump()

    class AdAlert(BaseModel):
        """单条广告告警记录。"""

        campaign_id: str = Field(default="", description="广告活动ID")
        metric: str = Field(default="", description="触发告警的指标名，如'acos'")
        current_value: float = Field(default=0.0, description="当前指标值")
        threshold: float = Field(default=0.0, description="阈值")
        level: str = Field(default=AlertLevel.INFO, description="告警级别: info/warning/critical")
        message: str = Field(default="", description="告警消息")
        suggestions: List[str] = Field(default_factory=list, description="优化建议")

        @field_validator("level")
        @classmethod
        def level_must_be_valid(cls, v: str) -> str:
            if v not in _VALID_ALERT_LEVELS:
                raise ValueError(f"告警级别必须是 {_VALID_ALERT_LEVELS} 之一，实际值: {v}")
            return v

        def to_dict(self) -> Dict[str, Any]:
            return self.model_dump()

else:
    # Pydantic 不可用时的降级版本
    class AdMetrics:  # type: ignore[no-redef]
        def __init__(
            self,
            campaign_id: str = "",
            campaign_name: str = "",
            acos: float = 0.0,
            roas: float = 0.0,
            ctr: float = 0.0,
            cvr: float = 0.0,
            spend: float = 0.0,
            sales: float = 0.0,
            impressions: int = 0,
            clicks: int = 0,
            date: str = "",
        ):
            if acos < 0:
                raise ValueError(f"ACoS不能为负数，实际值: {acos}")
            if roas < 0:
                raise ValueError(f"ROAS不能为负数，实际值: {roas}")
            if spend < 0:
                raise ValueError(f"花费不能为负数，实际值: {spend}")
            self.campaign_id = campaign_id
            self.campaign_name = campaign_name
            self.acos = acos
            self.roas = roas
            self.ctr = ctr
            self.cvr = cvr
            self.spend = spend
            self.sales = sales
            self.impressions = impressions
            self.clicks = clicks
            self.date = date

        def to_dict(self) -> Dict[str, Any]:
            return {
                "campaign_id": self.campaign_id,
                "campaign_name": self.campaign_name,
                "acos": self.acos,
                "roas": self.roas,
                "ctr": self.ctr,
                "cvr": self.cvr,
                "spend": self.spend,
                "sales": self.sales,
                "impressions": self.impressions,
                "clicks": self.clicks,
                "date": self.date,
            }

    class AdAlert:  # type: ignore[no-redef]
        def __init__(
            self,
            campaign_id: str = "",
            metric: str = "",
            current_value: float = 0.0,
            threshold: float = 0.0,
            level: str = AlertLevel.INFO,
            message: str = "",
            suggestions: List[str] = None,
        ):
            if level not in _VALID_ALERT_LEVELS:
                raise ValueError(f"告警级别必须是 {_VALID_ALERT_LEVELS} 之一，实际值: {level}")
            self.campaign_id = campaign_id
            self.metric = metric
            self.current_value = current_value
            self.threshold = threshold
            self.level = level
            self.message = message
            self.suggestions = suggestions or []

        def to_dict(self) -> Dict[str, Any]:
            return {
                "campaign_id": self.campaign_id,
                "metric": self.metric,
                "current_value": self.current_value,
                "threshold": self.threshold,
                "level": self.level,
                "message": self.message,
                "suggestions": self.suggestions,
            }


# ---------------------------------------------------------------------------
# LangGraph 状态定义
# ---------------------------------------------------------------------------

class AdMonitorState(dict):
    """LangGraph 工作流状态（继承 dict 保证兼容性）。

    键说明：
      campaigns     (list) — 待监控的广告活动ID列表（空=监控全部）
      ad_metrics    (list) — 原始广告指标列表
      alerts        (list) — 生成的告警列表
      suggestions   (list) — 优化建议列表
      summary       (dict) — 汇总统计
      dry_run       (bool) — 是否dry run模式（True=使用Mock数据）
      agent_run_id  (str)  — agent_runs表主键
      error         (str)  — 错误信息（若有）
      status        (str)  — 当前状态 running/completed/failed
    """

    def __init__(
        self,
        campaigns: List[str] = None,
        ad_metrics: List[Any] = None,
        alerts: List[Any] = None,
        suggestions: List[str] = None,
        summary: Dict[str, Any] = None,
        dry_run: bool = True,
        **kwargs,
    ):
        super().__init__(
            campaigns=campaigns or [],
            ad_metrics=ad_metrics or [],
            alerts=alerts or [],
            suggestions=suggestions or [],
            summary=summary or {},
            dry_run=dry_run,
            agent_run_id=None,
            error=None,
            status="running",
            **kwargs,
        )
