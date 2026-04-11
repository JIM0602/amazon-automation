from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CampaignPhase(str, Enum):
    COLD_START = "COLD_START"
    MATURE = "MATURE"


class KeywordMatchType(str, Enum):
    BROAD = "BROAD"
    PHRASE = "PHRASE"
    EXACT = "EXACT"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


class BidDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    HOLD = "HOLD"


@dataclass(slots=True)
class BidHistoryEntry:
    timestamp: Any | None = None
    bid: float = 0.0
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0
    impressions: int = 0


@dataclass(slots=True)
class Campaign:
    campaign_id: str = ""
    name: str = ""
    phase: CampaignPhase | None = None
    target_acos: float = 30.0
    days_active: int = 0
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0
    asp: float = 0.0
    budget: float = 0.0
    cpc_strategy: str = "fixed"
    organic_rank: int | None = None
    inventory_days: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AdGroup:
    ad_group_id: str = ""
    campaign_id: str = ""
    name: str = ""
    current_bid: float = 0.0
    avg_cpc: float = 0.0
    budget: float = 0.0
    strategy: str = "fixed"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KeywordPerformance:
    keyword_id: str = ""
    campaign_id: str = ""
    ad_group_id: str = ""
    keyword_text: str = ""
    match_type: KeywordMatchType = KeywordMatchType.BROAD
    current_bid: float = 0.0
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0
    impressions: int = 0
    days_active: int = 0
    bid_history: list[BidHistoryEntry] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BidRecommendation:
    keyword_id: str
    current_bid: float
    suggested_bid: float
    direction: BidDirection
    confidence: ConfidenceLevel
    reason: str
    campaign_id: str = ""
    ad_group_id: str = ""
    phase: CampaignPhase | None = None
    safety_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlacementRecommendation:
    campaign_id: str
    placement: str
    current_multiplier: float
    suggested_multiplier: float
    confidence: ConfidenceLevel
    reason: str
    safety_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BudgetRecommendation:
    campaign_id: str
    current_budget: float
    suggested_budget: float
    confidence: ConfidenceLevel
    reason: str
    safety_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SearchTermAction:
    search_term: str
    campaign_id: str = ""
    ad_group_id: str = ""
    match_type: KeywordMatchType | None = None
    action: str = ""
    reason: str = ""
    traffic_isolation: bool = False


@dataclass(slots=True)
class OptimizationResult:
    bid_recommendations: list[BidRecommendation] = field(default_factory=list)
    placement_recommendations: list[PlacementRecommendation] = field(default_factory=list)
    budget_recommendations: list[BudgetRecommendation] = field(default_factory=list)
    search_term_actions: list[SearchTermAction] = field(default_factory=list)
    dayparting: dict[int, float] = field(default_factory=dict)
    summary: str = ""


@dataclass(slots=True)
class BusinessContext:
    asp_change_pct: float = 0.0
    inventory_days: float | None = None
    organic_rank: int | None = None
    campaign_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlacementPerformance:
    campaign_id: str
    placement: str
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0
    impressions: int = 0
    current_multiplier: float = 1.0
    strategy: str = "fixed"
    days_ago: int = 0


@dataclass(slots=True)
class SearchTermPerformance:
    campaign_id: str
    ad_group_id: str
    search_term: str
    match_type: KeywordMatchType
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0


@dataclass(slots=True)
class DaypartPerformance:
    hour: int
    clicks: int = 0
    orders: int = 0
    spend: float = 0.0
    sales: float = 0.0
    impressions: int = 0
