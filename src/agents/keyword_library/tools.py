"""关键词库工具函数。

提供关键词采集、分类、相关性判断等工具。
数据来源：卖家精灵 MCP、Brand Analytics、Search Term Report、广告数据。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class KeywordSource(str, Enum):
    """关键词数据来源。"""

    SELLER_SPRITE = "seller_sprite"
    BRAND_ANALYTICS = "brand_analytics"
    SEARCH_TERM_REPORT = "search_term_report"
    AD_DATA = "ad_data"
    MANUAL = "manual"


class KeywordTier(str, Enum):
    """关键词层级分类。"""

    CORE = "core"  # 核心词（高搜索量、高相关性）
    LONG_TAIL = "long_tail"  # 长尾词（中等搜索量、高精准度）
    NICHE = "niche"  # 利基词（低搜索量、极高转化率）
    NEGATIVE = "negative"  # 否定词（不相关或低效）


class RelevanceLevel(str, Enum):
    """相关性等级。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IRRELEVANT = "irrelevant"


@dataclass
class KeywordCandidate:
    """关键词候选项。"""

    keyword: str
    source: KeywordSource
    search_volume: int = 0
    tier: KeywordTier = KeywordTier.LONG_TAIL
    relevance: RelevanceLevel = RelevanceLevel.MEDIUM
    competition_index: float = 0.0
    conversion_rate: float = 0.0
    notes: str = ""


def categorize_keyword(search_volume: int, competition: float) -> KeywordTier:
    """根据搜索量和竞争度自动分类关键词层级。"""

    if search_volume >= 10000 and competition < 0.7:
        return KeywordTier.CORE
    elif search_volume >= 1000:
        return KeywordTier.LONG_TAIL
    elif search_volume >= 100:
        return KeywordTier.NICHE
    else:
        return KeywordTier.NICHE


def get_sop_steps() -> list[dict[str, str]]:
    """返回产品词库搭建SOP的4个步骤。"""

    return [
        {
            "step": "1",
            "name": "收集ASIN种子词",
            "description": "通过卖家精灵反查ASIN的核心关键词，结合Brand Analytics和广告Search Term Report收集初始词库。",
        },
        {
            "step": "2",
            "name": "关键词挖掘扩展",
            "description": "基于种子词通过卖家精灵搜索词扩展、关联词挖掘，扩大词库覆盖面。",
        },
        {
            "step": "3",
            "name": "分类与分层",
            "description": "将关键词按核心词、长尾词、利基词、否定词进行分类，标注搜索量、竞争度、相关性。",
        },
        {
            "step": "4",
            "name": "相关性判断与审批",
            "description": "AI对每个关键词的相关性进行初步判断，高不确定性的关键词提交人工审批确认。",
        },
    ]
