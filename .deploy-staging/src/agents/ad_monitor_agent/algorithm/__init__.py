"""NextGen Orchestrator 广告优化算法包。"""

from __future__ import annotations

from .core import AdOptimizer
from .metrics import (
    bayesian_smoothed_cvr,
    calculate_acos,
    calculate_cpc,
    calculate_cvr,
    calculate_ctr,
    calculate_roas,
    calculate_tacos,
    get_confidence_level,
    placement_efficiency_score,
)
from .models import (
    AdGroup,
    BidDirection,
    BidHistoryEntry,
    BidRecommendation,
    BudgetRecommendation,
    Campaign,
    CampaignPhase,
    ConfidenceLevel,
    DaypartPerformance,
    KeywordMatchType,
    KeywordPerformance,
    OptimizationResult,
    PlacementRecommendation,
    PlacementPerformance,
    SearchTermAction,
    SearchTermPerformance,
    BusinessContext,
)
from .safety import SafetyContext, SafetyRails

__all__ = [
    "AdOptimizer",
    "SafetyRails",
    "SafetyContext",
    "CampaignPhase",
    "KeywordMatchType",
    "ConfidenceLevel",
    "BidDirection",
    "Campaign",
    "AdGroup",
    "KeywordPerformance",
    "BidHistoryEntry",
    "BidRecommendation",
    "PlacementRecommendation",
    "BudgetRecommendation",
    "SearchTermAction",
    "OptimizationResult",
    "BusinessContext",
    "PlacementPerformance",
    "SearchTermPerformance",
    "DaypartPerformance",
    "calculate_acos",
    "calculate_roas",
    "calculate_tacos",
    "calculate_cpc",
    "calculate_ctr",
    "calculate_cvr",
    "bayesian_smoothed_cvr",
    "get_confidence_level",
    "placement_efficiency_score",
]
