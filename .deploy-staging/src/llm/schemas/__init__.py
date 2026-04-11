"""src/llm/schemas 包公共接口。

导出所有 Schema 类，方便其他模块直接导入。
"""
from src.llm.schemas.base import BaseOutputSchema
from src.llm.schemas.selection_result import (
    SelectionResultSchema,
    ProductCandidateSchema,
    MarketDataSchema,
)
from src.llm.schemas.daily_report import (
    DailyReportSchema,
    SalesDataSchema,
    AgentProgressSchema,
    MarketDataReportSchema,
)
from src.llm.schemas.ad_strategy import AdStrategySchema

__all__ = [
    # 基类
    "BaseOutputSchema",
    # 选品结果
    "SelectionResultSchema",
    "ProductCandidateSchema",
    "MarketDataSchema",
    # 日报
    "DailyReportSchema",
    "SalesDataSchema",
    "AgentProgressSchema",
    "MarketDataReportSchema",
    # 广告策略（预留）
    "AdStrategySchema",
]
