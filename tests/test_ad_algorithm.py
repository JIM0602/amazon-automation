from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.agents.ad_monitor_agent.algorithm import (
    AdGroup,
    AdOptimizer,
    BidDirection,
    BidHistoryEntry,
    BidRecommendation,
    BusinessContext,
    Campaign,
    CampaignPhase,
    ConfidenceLevel,
    KeywordMatchType,
    KeywordPerformance,
    PlacementPerformance,
    SafetyContext,
    SafetyRails,
    SearchTermPerformance,
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


class TestMetrics:
    def test_calculate_acos(self):
        assert calculate_acos(30, 100) == 30.0

    def test_calculate_roas(self):
        assert calculate_roas(100, 20) == 5.0

    def test_calculate_tacos(self):
        assert calculate_tacos(20, 100) == 20.0

    def test_calculate_cpc(self):
        assert calculate_cpc(20, 4) == 5.0

    def test_calculate_ctr(self):
        assert calculate_ctr(50, 1000) == 5.0

    def test_calculate_cvr(self):
        assert calculate_cvr(10, 50) == 20.0

    def test_zero_division_returns_zero(self):
        assert calculate_acos(10, 0) == 0.0
        assert calculate_roas(10, 0) == 0.0
        assert calculate_tacos(10, 0) == 0.0
        assert calculate_cpc(10, 0) == 0.0
        assert calculate_ctr(0, 0) == 0.0
        assert calculate_cvr(0, 0) == 0.0

    def test_bayesian_smoothed_cvr(self):
        assert bayesian_smoothed_cvr(1, 1) == pytest.approx((1 + 20 * 0.05) / 21)

    def test_confidence_levels(self):
        assert get_confidence_level(20, 200, 100) == ConfidenceLevel.HIGH
        assert get_confidence_level(10, 100, 50) == ConfidenceLevel.MEDIUM_HIGH
        assert get_confidence_level(5, 50, 25) == ConfidenceLevel.MEDIUM
        assert get_confidence_level(2, 20, 0) == ConfidenceLevel.LOW
        assert get_confidence_level(1, 5, 0) == ConfidenceLevel.VERY_LOW

    def test_placement_efficiency_score(self):
        score = placement_efficiency_score(1.0, 0.0, 1.0, 0.0)
        assert score == pytest.approx(1.0)


class TestSafetyRails:
    def _rec(self, current: float, suggested: float, direction: BidDirection = BidDirection.INCREASE) -> BidRecommendation:
        return BidRecommendation(
            keyword_id="k1",
            current_bid=current,
            suggested_bid=suggested,
            direction=direction,
            confidence=ConfidenceLevel.HIGH,
            reason="test",
        )

    def test_cooldown_blocks_change(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 1.3),
            SafetyContext(now=datetime(2026, 4, 9), last_adjusted_at=datetime(2026, 4, 8, 12), current_bid=1.0),
        )
        assert rec.direction == BidDirection.HOLD

    def test_minimum_adjustment_blocks_small_change(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 1.01),
            SafetyContext(now=datetime(2026, 4, 9), current_bid=1.0, last_adjusted_at=datetime(2026, 4, 1)),
        )
        assert rec.direction == BidDirection.HOLD

    def test_circuit_breaker_caps_single_increase(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 2.0),
            SafetyContext(now=datetime(2026, 4, 9), current_bid=1.0, last_adjusted_at=datetime(2026, 4, 1)),
        )
        assert rec.suggested_bid <= 1.2

    def test_decrease_circuit_breaker_blocks(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 0.5, BidDirection.DECREASE),
            SafetyContext(now=datetime(2026, 4, 9), current_bid=1.0, last_adjusted_at=datetime(2026, 4, 1), cumulative_decrease_7d=0.2),
        )
        assert rec.direction == BidDirection.HOLD

    def test_floor_at_half_initial(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 0.1, BidDirection.DECREASE),
            SafetyContext(now=datetime(2026, 4, 9), current_bid=1.0, initial_bid=1.0, last_adjusted_at=datetime(2026, 4, 1)),
        )
        assert rec.suggested_bid >= 0.5

    def test_oscillation_forces_hold(self):
        rails = SafetyRails()
        now = datetime(2026, 4, 9)
        history = [
            (now - timedelta(hours=1), BidDirection.INCREASE),
            (now - timedelta(hours=2), BidDirection.DECREASE),
            (now - timedelta(hours=3), BidDirection.INCREASE),
        ]
        rec = rails.apply(self._rec(1.0, 1.3), SafetyContext(now=now, current_bid=1.0, bid_history=history))
        assert rec.direction == BidDirection.HOLD

    def test_impression_drop_blocks_decrease(self):
        rails = SafetyRails()
        rec = rails.apply(
            self._rec(1.0, 0.8, BidDirection.DECREASE),
            SafetyContext(now=datetime(2026, 4, 9), current_bid=1.0, impressions_baseline=1000, current_impressions=500, last_adjusted_at=datetime(2026, 4, 1)),
        )
        assert rec.direction == BidDirection.HOLD


class TestColdStart:
    def test_probing_increment(self):
        optimizer = AdOptimizer()
        campaign = Campaign(campaign_id="c1", days_active=2)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=0.5, avg_cpc=0.8)
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=0.5, impressions=0, clicks=0)
        rec = optimizer._cold_start_optimize(keyword, campaign, ad_group, datetime(2026, 4, 9))
        assert rec.direction == BidDirection.INCREASE
        assert rec.suggested_bid == pytest.approx(0.55)

    def test_zero_impressions_at_cap_resets(self):
        optimizer = AdOptimizer(max_bid=3.0)
        campaign = Campaign(campaign_id="c1", days_active=2)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=2.0, avg_cpc=1.0)
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=2.5, impressions=0, clicks=0)
        rec = optimizer._cold_start_optimize(keyword, campaign, ad_group, datetime(2026, 4, 9))
        assert rec.reason.startswith("zero_impressions_at_cap_reset")

    def test_bayesian_used_in_reason(self):
        optimizer = AdOptimizer()
        campaign = Campaign(campaign_id="c1", days_active=2)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=0.5, avg_cpc=0.8)
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=0.5, impressions=10, clicks=1, orders=0)
        rec = optimizer._cold_start_optimize(keyword, campaign, ad_group, datetime(2026, 4, 9))
        assert "bayesian_cvr" in rec.reason


class TestMatureAndBusiness:
    def test_mature_high_acos_decreases(self):
        optimizer = AdOptimizer(target_acos=30.0)
        campaign = Campaign(campaign_id="c1", days_active=30, clicks=200, orders=20, asp=20.0)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=1.0, avg_cpc=0.9)
        history = [
            BidHistoryEntry(timestamp=datetime(2026, 3, 10), bid=1.0, clicks=100, orders=8, spend=60, sales=100),
            BidHistoryEntry(timestamp=datetime(2026, 3, 20), bid=1.1, clicks=120, orders=10, spend=80, sales=140),
        ]
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=1.0, clicks=200, orders=20, spend=200, sales=300, bid_history=history)
        rec = optimizer._mature_optimize(keyword, campaign, ad_group, datetime(2026, 4, 9))
        assert rec.direction == BidDirection.DECREASE

    def test_mature_low_acos_increases(self):
        optimizer = AdOptimizer(target_acos=30.0)
        campaign = Campaign(campaign_id="c1", days_active=30, clicks=200, orders=20, asp=20.0)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=0.5, avg_cpc=0.5)
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=0.5, clicks=200, orders=20, spend=50, sales=500)
        rec = optimizer._mature_optimize(keyword, campaign, ad_group, datetime(2026, 4, 9))
        assert rec.direction == BidDirection.INCREASE

    def test_business_inventory_adjustments(self):
        optimizer = AdOptimizer()
        base = BidRecommendation("k1", 1.0, 1.0, BidDirection.HOLD, ConfidenceLevel.HIGH, "base")
        campaign = Campaign(campaign_id="c1", inventory_days=5)
        rec = optimizer._apply_business_adjustments(base, campaign, BusinessContext(inventory_days=5))
        assert rec.suggested_bid < 1.0

    def test_business_oos_not_below_floor(self):
        optimizer = AdOptimizer()
        base = BidRecommendation("k1", 1.0, 1.0, BidDirection.HOLD, ConfidenceLevel.HIGH, "base")
        campaign = Campaign(campaign_id="c1", inventory_days=0)
        rec = optimizer._apply_business_adjustments(base, campaign, BusinessContext(inventory_days=0))
        assert rec.suggested_bid == 0.0

    def test_organic_rank_reduces_bid(self):
        optimizer = AdOptimizer()
        base = BidRecommendation("k1", 1.0, 1.0, BidDirection.HOLD, ConfidenceLevel.HIGH, "base")
        campaign = Campaign(campaign_id="c1", organic_rank=5)
        rec = optimizer._apply_business_adjustments(base, campaign, BusinessContext(organic_rank=5))
        assert rec.suggested_bid < 1.0


class TestSearchTerms:
    def test_ngram_noise_reduction(self):
        optimizer = AdOptimizer()
        items = [
            SearchTermPerformance("c1", "g1", "cheap repair kit", KeywordMatchType.BROAD, clicks=5, orders=0, spend=10, sales=0),
            SearchTermPerformance("c1", "g1", "cheap replacement part", KeywordMatchType.BROAD, clicks=6, orders=0, spend=12, sales=0),
            SearchTermPerformance("c1", "g1", "cheap quick fix", KeywordMatchType.BROAD, clicks=7, orders=0, spend=14, sales=0),
        ]
        actions = optimizer._analyze_search_terms(items)
        assert any(a.action == "negative_phrase" for a in actions)

    def test_funnel_migration(self):
        optimizer = AdOptimizer()
        items = [
            SearchTermPerformance("c1", "g1", "best widget", KeywordMatchType.BROAD, clicks=30, orders=3, spend=20, sales=80),
            SearchTermPerformance("c1", "g1", "best widget pro", KeywordMatchType.PHRASE, clicks=60, orders=10, spend=40, sales=200),
        ]
        actions = optimizer._analyze_search_terms(items)
        assert any(a.action == "migrate_to_phrase" for a in actions)
        assert any(a.action == "migrate_to_exact" for a in actions)


class TestIntegration:
    def test_optimize_end_to_end(self):
        optimizer = AdOptimizer()
        campaign = Campaign(campaign_id="c1", days_active=30, clicks=200, orders=20, budget=100, asp=20)
        ad_group = AdGroup(ad_group_id="g1", campaign_id="c1", current_bid=1.0, avg_cpc=0.9)
        keyword = KeywordPerformance(keyword_id="k1", campaign_id="c1", ad_group_id="g1", current_bid=1.0, clicks=200, orders=20, spend=200, sales=300)
        result = optimizer.optimize(
            [campaign],
            [ad_group],
            [keyword],
            search_terms=[
                SearchTermPerformance("c1", "g1", "cheap repair kit", KeywordMatchType.BROAD, clicks=5, orders=0, spend=10, sales=0),
                SearchTermPerformance("c1", "g1", "cheap replacement part", KeywordMatchType.BROAD, clicks=6, orders=0, spend=12, sales=0),
                SearchTermPerformance("c1", "g1", "cheap quick fix", KeywordMatchType.BROAD, clicks=7, orders=0, spend=14, sales=0),
            ],
            placements=[PlacementPerformance("c1", "top_of_search", clicks=200, orders=20, spend=120, sales=400, current_multiplier=1.0, strategy="fixed", days_ago=10)],
            business_context=BusinessContext(inventory_days=10, organic_rank=8),
            now=datetime(2026, 4, 9),
        )
        assert result.bid_recommendations
        assert result.placement_recommendations
        assert result.budget_recommendations
        assert result.search_term_actions
        assert result.summary
