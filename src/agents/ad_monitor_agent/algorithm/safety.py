from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

from src.utils.timezone import now_site_time

from .models import BidDirection, BidRecommendation


@dataclass(slots=True)
class SafetyContext:
    now: datetime | None = None
    is_placement: bool = False
    last_adjusted_at: datetime | None = None
    current_bid: float | None = None
    initial_bid: float | None = None
    avg_cpc: float | None = None
    impressions_baseline: int | None = None
    current_impressions: int | None = None
    bid_history: list[tuple[datetime, BidDirection]] = field(default_factory=list)
    cumulative_decrease_7d: float = 0.0
    consecutive_decreases: int = 0
    zero_impressions_at_cap: bool = False
    cap_bid: float | None = None


class SafetyRails:
    def apply(self, recommendation: BidRecommendation, context: SafetyContext) -> BidRecommendation:
        now = context.now or now_site_time()
        result = BidRecommendation(
            keyword_id=recommendation.keyword_id,
            current_bid=recommendation.current_bid,
            suggested_bid=recommendation.suggested_bid,
            direction=recommendation.direction,
            confidence=recommendation.confidence,
            reason=recommendation.reason,
            campaign_id=recommendation.campaign_id,
            ad_group_id=recommendation.ad_group_id,
            phase=recommendation.phase,
            safety_notes=list(recommendation.safety_notes),
        )

        # 4. Oscillation detection: up-down-up in 72h -> HOLD
        if self._has_oscillation(context.bid_history, now):
            result.direction = BidDirection.HOLD
            result.suggested_bid = result.current_bid
            result.safety_notes.append("oscillation_detected_72h")
            return result

        # 1. Cooldown
        cooldown = timedelta(days=7 if context.is_placement else 1)
        if context.last_adjusted_at is not None and now - context.last_adjusted_at < cooldown:
            result.direction = BidDirection.HOLD
            result.suggested_bid = result.current_bid
            result.safety_notes.append("cooldown_active")
            return result

        current = context.current_bid if context.current_bid is not None else result.current_bid
        initial = context.initial_bid if context.initial_bid is not None else current
        if context.zero_impressions_at_cap:
            result.direction = BidDirection.HOLD
            result.suggested_bid = context.avg_cpc if context.avg_cpc is not None else result.current_bid
            result.safety_notes.append("zero_impressions_at_cap_reset")
            return result

        # 5. Impression protection
        if (
            context.impressions_baseline is not None
            and context.current_impressions is not None
            and context.impressions_baseline > 0
        ):
            drop = 1 - (context.current_impressions / context.impressions_baseline)
            if drop > 0.4 and result.direction == BidDirection.DECREASE:
                result.direction = BidDirection.HOLD
                result.suggested_bid = current if current is not None else result.suggested_bid
                result.safety_notes.append("impression_drop_protection")
                return result

        # 2. Minimum adjustment
        if current is not None:
            abs_change = abs(result.suggested_bid - current)
            pct_change = abs_change / current if current else 1.0
            if abs_change < 0.02 and pct_change < 0.05:
                result.direction = BidDirection.HOLD
                result.suggested_bid = current
                result.safety_notes.append("minimum_adjustment_filtered")
                return result

        # 3. Circuit breaker
        delta = result.suggested_bid - current if current is not None else 0.0
        if abs(delta) > 0:
            cap_delta = min(abs(delta), (current or 0.0) * 0.2 if current else abs(delta))
            if delta > 0:
                result.suggested_bid = (current or 0.0) + cap_delta
            else:
                decrease = min(abs(delta), cap_delta)
                if context.cumulative_decrease_7d >= 0.2 or context.consecutive_decreases >= 2:
                    result.direction = BidDirection.HOLD
                    result.suggested_bid = current if current is not None else result.suggested_bid
                    result.safety_notes.append("decrease_circuit_breaker")
                    return result
                result.suggested_bid = (current or 0.0) - decrease
                result.safety_notes.append("single_change_capped_20pct")

        if initial is not None and result.suggested_bid < initial * 0.5:
            result.suggested_bid = initial * 0.5
            result.safety_notes.append("floor_50pct_initial")

        return result

    def _has_oscillation(
        self,
        history: Iterable[tuple[datetime, BidDirection]],
        now: datetime,
    ) -> bool:
        recent = [item for item in history if now - item[0] <= timedelta(hours=72)]
        if len(recent) < 3:
            return False
        directions = [direction for _, direction in recent]
        pattern = [BidDirection.INCREASE, BidDirection.DECREASE, BidDirection.INCREASE]
        return any(
            directions[i : i + 3] == pattern
            for i in range(len(directions) - 2)
        )
