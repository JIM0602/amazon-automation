"""Google Trends 集成包 (可选模块).

通过 SerpApi 获取 Google Trends 数据，支持搜索趋势、相关查询和区域兴趣分析。
本模块为可选依赖 — 使用 get_trends_client() 工厂函数获取客户端，
返回 None 表示功能未启用。
"""

from __future__ import annotations

from src.google_trends.client import GoogleTrendsClient, get_trends_client
from src.google_trends.models import (
    RegionalInterest,
    RelatedQuery,
    TrendData,
)

__all__ = [
    "GoogleTrendsClient",
    "get_trends_client",
    "TrendData",
    "RelatedQuery",
    "RegionalInterest",
]
