"""Google Trends 数据模型.

使用 dataclass(slots=True) 定义轻量级数据结构，
用于在 Google Trends 客户端与调用方之间传递类型安全的趋势数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class TrendPoint:
    """单个时间点的搜索兴趣数据。"""

    date: str
    """日期字符串，格式如 '2024-01-15'。"""

    interest: int
    """相对搜索兴趣值 (0-100)。"""


@dataclass(slots=True)
class TrendData:
    """关键词的搜索趋势数据汇总。"""

    keyword: str
    """查询的关键词。"""

    timeframe: str
    """时间范围，如 'today 12-m'。"""

    geo: str
    """地区代码，如 'US'。"""

    interest_over_time: list[TrendPoint] = field(default_factory=list)
    """时间序列搜索兴趣数据。"""

    fetched_at: datetime = field(default_factory=datetime.utcnow)
    """数据获取的 UTC 时间戳。"""


@dataclass(slots=True)
class RelatedQuery:
    """与关键词相关的搜索查询。"""

    query: str
    """相关查询文本。"""

    value: int
    """相关性/搜索量指标值。"""

    rising: bool
    """是否为上升趋势查询。"""


@dataclass(slots=True)
class RegionalInterest:
    """特定区域的搜索兴趣数据。"""

    region: str
    """区域/国家名称。"""

    interest: int
    """该区域的相对搜索兴趣值 (0-100)。"""
