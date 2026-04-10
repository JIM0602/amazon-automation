from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from math import log
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from .metrics import (
    bayesian_smoothed_cvr,
    calculate_acos,
    calculate_cpc,
    calculate_cvr,
    calculate_ctr,
    calculate_roas,
    calculate_tacos,
    decayed_weight,
    get_confidence_level,
    normalize,
    placement_efficiency_score,
)
from .models import (
    AdGroup,
    BidDirection,
    BidHistoryEntry,
    BidRecommendation,
    BudgetRecommendation,
    BusinessContext,
    Campaign,
    CampaignPhase,
    ConfidenceLevel,
    DaypartPerformance,
    KeywordMatchType,
    KeywordPerformance,
    OptimizationResult,
    PlacementPerformance,
    PlacementRecommendation,
    SearchTermAction,
    SearchTermPerformance,
)
from .safety import SafetyContext, SafetyRails


class AdOptimizer:
    def __init__(self, target_acos: float = 30.0, max_bid: float = 3.0) -> None:
        self.target_acos = target_acos
        self.max_bid = max_bid
        self._safety = SafetyRails()

    def optimize(
        self,
        campaigns: Sequence[Campaign],
        ad_groups: Sequence[AdGroup],
        keywords: Sequence[KeywordPerformance],
        *,
        search_terms: Sequence[SearchTermPerformance | Mapping[str, Any]] | None = None,
        placements: Sequence[PlacementPerformance | Mapping[str, Any]] | None = None,
        business_context: BusinessContext | Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> OptimizationResult:
        now = now or datetime.utcnow()
        campaign_map = {c.campaign_id: c for c in campaigns}
        ad_group_map = {a.ad_group_id: a for a in ad_groups}
        bid_recommendations: list[BidRecommendation] = []

        for keyword in keywords:
            campaign = campaign_map.get(keyword.campaign_id, Campaign(campaign_id=keyword.campaign_id))
            ad_group = ad_group_map.get(keyword.ad_group_id, AdGroup(ad_group_id=keyword.ad_group_id, campaign_id=keyword.campaign_id, current_bid=keyword.current_bid, avg_cpc=keyword.current_bid))
            phase = campaign.phase or self._classify_phase(campaign, keyword)

            if phase == CampaignPhase.COLD_START:
                recommendation = self._cold_start_optimize(keyword, campaign, ad_group, now)
            else:
                recommendation = self._mature_optimize(keyword, campaign, ad_group, now)

            recommendation = self._apply_business_adjustments(recommendation, campaign, business_context)
            safety_context = self._build_safety_context(keyword, ad_group, now)
            recommendation = self._safety.apply(recommendation, safety_context)
            bid_recommendations.append(recommendation)

        placement_recommendations = self._placement_optimization(placements or [], now=now)
        search_term_actions = self._analyze_search_terms(search_terms or [])
        budget_recommendations = self._lagrangian_budget_allocation(campaigns)
        dayparting = self._dayparting_optimization(keywords)

        summary = (
            f"bid={len(bid_recommendations)}, placement={len(placement_recommendations)}, "
            f"budget={len(budget_recommendations)}, search_terms={len(search_term_actions)}"
        )
        return OptimizationResult(
            bid_recommendations=bid_recommendations,
            placement_recommendations=placement_recommendations,
            budget_recommendations=budget_recommendations,
            search_term_actions=search_term_actions,
            dayparting=dayparting,
            summary=summary,
        )

    def _classify_phase(self, campaign: Campaign, keyword: KeywordPerformance) -> CampaignPhase:
        if campaign.days_active < 7 or campaign.clicks < 15:
            return CampaignPhase.COLD_START
        if campaign.clicks >= 15 and campaign.orders >= 3:
            return CampaignPhase.MATURE
        if keyword.clicks < 15 or keyword.orders < 3:
            return CampaignPhase.COLD_START
        return CampaignPhase.MATURE

    def _cold_start_optimize(
        self,
        keyword: KeywordPerformance,
        campaign: Campaign,
        ad_group: AdGroup,
        now: datetime,
    ) -> BidRecommendation:
        current = keyword.current_bid or ad_group.current_bid or 0.05
        avg_cpc = ad_group.avg_cpc or current or 0.05
        cap = min(self.max_bid, avg_cpc * 3.0, self.max_bid * 0.5 if self.max_bid else avg_cpc * 3.0)
        cap = max(cap, 0.05)

        if keyword.impressions == 0 and current >= cap:
            suggested = avg_cpc
            reason = "zero_impressions_at_cap_reset"
            direction = BidDirection.HOLD
        else:
            probe = max(current * 0.10, 0.05)
            suggested = min(current + probe, cap)
            reason = "cold_start_probe"
            direction = BidDirection.INCREASE if suggested > current else BidDirection.HOLD

        if keyword.clicks < 15:
            smoothed = bayesian_smoothed_cvr(keyword.orders, keyword.clicks)
            reason += f"|bayesian_cvr={smoothed:.4f}"

        return BidRecommendation(
            keyword_id=keyword.keyword_id,
            current_bid=current,
            suggested_bid=suggested,
            direction=direction,
            confidence=get_confidence_level(keyword.orders, keyword.clicks, keyword.spend),
            reason=reason,
            campaign_id=campaign.campaign_id,
            ad_group_id=ad_group.ad_group_id,
            phase=CampaignPhase.COLD_START,
        )

    def _mature_optimize(
        self,
        keyword: KeywordPerformance,
        campaign: Campaign,
        ad_group: AdGroup,
        now: datetime,
    ) -> BidRecommendation:
        window = self._aggregate_history(keyword.bid_history, now)
        clicks = window["clicks"] or keyword.clicks
        orders = window["orders"] or keyword.orders
        spend = window["spend"] or keyword.spend
        sales = window["sales"] or keyword.sales
        asp = self._resolve_asp(campaign, sales, orders)
        cvr = calculate_cvr(orders, clicks)
        acos = calculate_acos(spend, sales)
        target_bid = (cvr * asp * (self.target_acos / 100.0)) / 100.0
        elasticity = self._estimate_elasticity(keyword.bid_history, now)
        current = keyword.current_bid or ad_group.current_bid or 0.0
        suggested = current + elasticity * (target_bid - current)

        if acos > self.target_acos:
            direction = BidDirection.DECREASE
            reason = f"mature_high_acos:{acos:.2f}>target:{self.target_acos:.2f}"
        elif acos < self.target_acos * 0.9:
            direction = BidDirection.INCREASE
            reason = f"mature_low_acos:{acos:.2f}<target:{self.target_acos:.2f}"
        else:
            direction = BidDirection.HOLD
            reason = f"mature_neutral_acos:{acos:.2f}"

        return BidRecommendation(
            keyword_id=keyword.keyword_id,
            current_bid=current,
            suggested_bid=max(0.0, min(suggested, self.max_bid)),
            direction=direction,
            confidence=get_confidence_level(orders, clicks, spend),
            reason=reason + f"|target_bid={target_bid:.4f}|elasticity={elasticity:.2f}",
            campaign_id=campaign.campaign_id,
            ad_group_id=ad_group.ad_group_id,
            phase=CampaignPhase.MATURE,
        )

    def _aggregate_history(self, bid_history: Sequence[BidHistoryEntry], now: datetime) -> dict[str, float]:
        clicks = orders = spend = sales = 0.0
        for entry in bid_history:
            timestamp = entry.timestamp
            if isinstance(timestamp, datetime):
                age = now - timestamp
                if not (timedelta(days=4) <= age <= timedelta(days=30)):
                    continue
            clicks += entry.clicks
            orders += entry.orders
            spend += entry.spend
            sales += entry.sales
        return {"clicks": clicks, "orders": orders, "spend": spend, "sales": sales}

    def _estimate_elasticity(self, bid_history: Sequence[BidHistoryEntry], now: datetime) -> float:
        points: list[tuple[float, float, float]] = []
        for entry in bid_history:
            if entry.bid <= 0 or entry.clicks < 1:
                continue
            weight = 1.0
            if isinstance(entry.timestamp, datetime):
                weight = decayed_weight((now - entry.timestamp).days)
            points.append((log(entry.bid), log(entry.clicks + 1.0), weight))
        if len(points) < 2:
            return 0.8

        x_mean = sum(x * w for x, _, w in points) / sum(w for _, _, w in points)
        y_mean = sum(y * w for _, y, w in points) / sum(w for _, _, w in points)
        numerator = sum(w * (x - x_mean) * (y - y_mean) for x, y, w in points)
        denominator = sum(w * (x - x_mean) ** 2 for x, _, w in points)
        if denominator == 0:
            return 0.8
        return max(0.1, min(2.0, numerator / denominator))

    def _resolve_asp(self, campaign: Campaign, sales: float, orders: float) -> float:
        if campaign.asp > 0:
            return campaign.asp
        if orders > 0:
            return sales / orders
        return 1.0

    def _analyze_search_terms(
        self,
        search_terms: Sequence[SearchTermPerformance | Mapping[str, Any]],
    ) -> list[SearchTermAction]:
        results: list[SearchTermAction] = []
        wasteful_terms: list[tuple[str, str, str]] = []
        root_counter: Counter[str] = Counter()

        for item in search_terms:
            row = self._as_mapping(item)
            term = str(row.get("search_term", "")).strip()
            match_type = self._normalize_match_type(row.get("match_type"))
            clicks = int(row.get("clicks", 0) or 0)
            orders = int(row.get("orders", 0) or 0)
            sales = float(row.get("sales", 0.0) or 0.0)
            spend = float(row.get("spend", 0.0) or 0.0)
            roas = calculate_roas(sales, spend)
            if clicks >= 5 and orders == 0:
                wasteful_terms.append((term, str(row.get("campaign_id", "")), str(row.get("ad_group_id", ""))))
                for token in self._tokenize(term):
                    root_counter[token] += 1

            if match_type in {KeywordMatchType.BROAD, KeywordMatchType.PHRASE} and orders >= 3 and roas >= 2.0:
                new_type = KeywordMatchType.PHRASE if match_type == KeywordMatchType.BROAD else KeywordMatchType.EXACT
                results.append(
                    SearchTermAction(
                        search_term=term,
                        campaign_id=str(row.get("campaign_id", "")),
                        ad_group_id=str(row.get("ad_group_id", "")),
                        match_type=match_type,
                        action=f"migrate_to_{new_type.value.lower()}",
                        reason="funnel_migration",
                        traffic_isolation=True,
                    )
                )

        for root, count in root_counter.items():
            if count >= 3:
                related = next((term for term, _, _ in wasteful_terms if root in self._tokenize(term)), root)
                results.append(
                    SearchTermAction(
                        search_term=related,
                        action="negative_phrase",
                        reason=f"ngram_noise_root={root}",
                        traffic_isolation=False,
                    )
                )

        return results

    def _explore_exploit_allocation(self, keywords: Sequence[KeywordPerformance]) -> dict[str, float]:
        core = [k for k in keywords if calculate_roas(k.sales, k.spend) >= 2.5 and k.orders >= 3]
        explore = [k for k in keywords if k not in core]
        allocations = {"core": 0.8 if core else 0.0, "explore": 0.2 if explore else 0.0}
        failures = sum(1 for k in explore if k.orders == 0 and k.clicks >= 5)
        if failures >= 5:
            allocations["explore"] = max(0.0, allocations["explore"] - 0.4)
        return allocations

    def _lagrangian_budget_allocation(self, campaigns: Sequence[Campaign]) -> list[BudgetRecommendation]:
        if not campaigns:
            return []
        scores = []
        for campaign in campaigns:
            roas = calculate_roas(campaign.sales, campaign.spend)
            cvr = calculate_cvr(campaign.orders, campaign.clicks)
            score = (roas * 0.7) + (cvr / 100.0 * 0.3)
            scores.append((campaign, score))
        avg_score = mean(score for _, score in scores)
        recommendations: list[BudgetRecommendation] = []
        for campaign, score in scores:
            delta = 0.0 if avg_score == 0 else (score - avg_score) / max(abs(avg_score), 1e-9)
            delta = max(-0.5, min(0.5, delta))
            suggested = max(1.0, campaign.budget * (1 + delta))
            recommendations.append(
                BudgetRecommendation(
                    campaign_id=campaign.campaign_id,
                    current_budget=campaign.budget,
                    suggested_budget=suggested,
                    confidence=get_confidence_level(campaign.orders, campaign.clicks, campaign.spend),
                    reason="lagrangian_budget_allocation",
                )
            )
        return recommendations

    def _placement_optimization(
        self,
        placements: Sequence[PlacementPerformance | Mapping[str, Any]],
        *,
        now: datetime,
    ) -> list[PlacementRecommendation]:
        if not placements:
            return []
        rows = [self._as_mapping(item) for item in placements]
        scored_rows = []
        for row in rows:
            days_ago = int(row.get("days_ago", 0) or 0)
            if days_ago < 0 or days_ago > 90:
                continue
            if days_ago < 3:
                continue
            weight = decayed_weight(days_ago)
            roas = calculate_roas(float(row.get("sales", 0.0) or 0.0), float(row.get("spend", 0.0) or 0.0))
            acos = calculate_acos(float(row.get("spend", 0.0) or 0.0), float(row.get("sales", 0.0) or 0.0))
            cvr = calculate_cvr(int(row.get("orders", 0) or 0), int(row.get("clicks", 0) or 0))
            cpc = calculate_cpc(float(row.get("spend", 0.0) or 0.0), int(row.get("clicks", 0) or 0))
            scored_rows.append((row, weight, roas, acos, cvr, cpc))

        if not scored_rows:
            return []

        roas_vals = [item[2] for item in scored_rows]
        acos_vals = [item[3] for item in scored_rows]
        cvr_vals = [item[4] for item in scored_rows]
        cpc_vals = [item[5] for item in scored_rows]
        min_roas, max_roas = min(roas_vals), max(roas_vals)
        min_acos, max_acos = min(acos_vals), max(acos_vals)
        min_cvr, max_cvr = min(cvr_vals), max(cvr_vals)
        min_cpc, max_cpc = min(cpc_vals), max(cpc_vals)

        placements_by_campaign: dict[str, list[tuple[dict[str, Any], float, float]]] = defaultdict(list)
        for row, weight, roas, acos, cvr, cpc in scored_rows:
            score = placement_efficiency_score(
                normalize(roas, min_roas, max_roas),
                normalize(acos, min_acos, max_acos),
                normalize(cvr, min_cvr, max_cvr),
                normalize(cpc, min_cpc, max_cpc),
            )
            placements_by_campaign[str(row.get("campaign_id", ""))].append((row, weight, score))

        recommendations: list[PlacementRecommendation] = []
        for campaign_id, items in placements_by_campaign.items():
            avg_score = sum(score * weight for _, weight, score in items) / sum(weight for _, weight, _ in items)
            for row, weight, score in items:
                confidence = get_confidence_level(int(row.get("orders", 0) or 0), int(row.get("clicks", 0) or 0), float(row.get("spend", 0.0) or 0.0))
                if confidence == ConfidenceLevel.HIGH:
                    max_adjust = 0.20
                elif confidence == ConfidenceLevel.MEDIUM_HIGH:
                    max_adjust = 0.20
                elif confidence == ConfidenceLevel.MEDIUM:
                    max_adjust = 0.10
                elif confidence == ConfidenceLevel.LOW:
                    max_adjust = 0.05
                else:
                    max_adjust = 0.0

                strategy = str(row.get("strategy", "fixed")).lower()
                boost_cap = 1.0 if strategy == "dynamic_up_down" else 2.0
                base = float(row.get("current_multiplier", 1.0) or 1.0)
                delta = max(-max_adjust, min(max_adjust, (score - avg_score) * 0.5))
                suggested = max(0.0, min(base * (1 + delta), 1.0 + boost_cap))
                recommendations.append(
                    PlacementRecommendation(
                        campaign_id=campaign_id,
                        placement=str(row.get("placement", "")),
                        current_multiplier=base,
                        suggested_multiplier=suggested,
                        confidence=confidence,
                        reason=f"placement_score={score:.4f}|avg={avg_score:.4f}",
                    )
                )
        return recommendations

    def _dayparting_optimization(
        self,
        keywords: Sequence[KeywordPerformance],
    ) -> dict[int, float]:
        if not keywords:
            return {}
        hourly = {hour: DaypartPerformance(hour=hour) for hour in range(24)}
        for keyword in keywords:
            for entry in keyword.bid_history:
                if isinstance(entry.timestamp, datetime):
                    hour = entry.timestamp.hour
                    if hour in hourly:
                        bucket = hourly[hour]
                        bucket.clicks += entry.clicks
                        bucket.orders += entry.orders
                        bucket.spend += entry.spend
                        bucket.sales += entry.sales
                        bucket.impressions += entry.impressions
        if all(bucket.clicks == 0 for bucket in hourly.values()):
            return {hour: 1.0 for hour in range(24)}

        max_clicks = max(bucket.clicks for bucket in hourly.values()) or 1
        multipliers: dict[int, float] = {}
        for hour, bucket in hourly.items():
            ctr = calculate_ctr(bucket.clicks, bucket.impressions)
            heat = ctr * 0.6 + (bucket.clicks / max_clicks) * 0.4
            multiplier = max(0.2, min(2.0, heat if heat > 0 else 0.2))
            if 0 <= hour <= 5:
                multiplier = max(0.2, multiplier - 0.05)
            elif 6 <= hour <= 8:
                multiplier = min(2.0, multiplier + 0.02)
            elif 19 <= hour <= 22:
                multiplier = min(2.0, multiplier + 0.05)
            elif hour == 23:
                multiplier = max(0.2, multiplier - 0.02)
            if bucket.clicks >= 10 and calculate_roas(bucket.sales, bucket.spend) < 1.0:
                multiplier = max(0.2, multiplier - 0.10)
            multipliers[hour] = multiplier
        return multipliers

    def _apply_business_adjustments(
        self,
        recommendation: BidRecommendation,
        campaign: Campaign,
        business_context: BusinessContext | Mapping[str, Any] | None,
    ) -> BidRecommendation:
        if business_context is None:
            return recommendation
        ctx = self._as_mapping(business_context)
        adjusted = replace(recommendation, safety_notes=list(recommendation.safety_notes))
        target_factor = 1.0
        asp_change_pct = float(ctx.get("asp_change_pct", 0.0) or 0.0)
        if asp_change_pct < -10:
            target_factor *= 1.3
            adjusted.safety_notes.append("asp_drop_relax_acos")
        elif asp_change_pct > 10:
            target_factor *= 0.9
            adjusted.safety_notes.append("asp_rise_tighten_acos")

        inventory_days = ctx.get("inventory_days", campaign.inventory_days)
        if inventory_days is not None:
            inventory_days = float(inventory_days)
            if inventory_days <= 0:
                adjusted.suggested_bid = 0.0
                adjusted.safety_notes.append("inventory_oos_pause")
            elif inventory_days < 3:
                target_factor *= 0.5
            elif inventory_days < 7:
                target_factor *= 0.7
            elif inventory_days < 14:
                target_factor *= 0.8

        organic_rank = ctx.get("organic_rank", campaign.organic_rank)
        if organic_rank is not None and int(organic_rank) <= 10:
            target_factor *= 0.7
            adjusted.safety_notes.append("organic_top10_reduce")

        if adjusted.suggested_bid > 0:
            adjusted.suggested_bid = max(0.0, min(adjusted.suggested_bid * target_factor, self.max_bid))
        if adjusted.suggested_bid > adjusted.current_bid:
            adjusted.direction = BidDirection.INCREASE
        elif adjusted.suggested_bid < adjusted.current_bid:
            adjusted.direction = BidDirection.DECREASE
        else:
            adjusted.direction = BidDirection.HOLD
        return adjusted

    def _build_safety_context(
        self,
        keyword: KeywordPerformance,
        ad_group: AdGroup,
        now: datetime,
    ) -> SafetyContext:
        history = []
        for item in keyword.bid_history:
            if isinstance(item.timestamp, datetime):
                history.append((item.timestamp, BidDirection.INCREASE if item.bid >= keyword.current_bid else BidDirection.DECREASE))
        return SafetyContext(
            now=now,
            is_placement=False,
            last_adjusted_at=keyword.bid_history[-1].timestamp if keyword.bid_history and isinstance(keyword.bid_history[-1].timestamp, datetime) else None,
            current_bid=keyword.current_bid or ad_group.current_bid,
            initial_bid=keyword.bid_history[0].bid if keyword.bid_history else (keyword.current_bid or ad_group.current_bid),
            avg_cpc=ad_group.avg_cpc or keyword.current_bid,
            impressions_baseline=max(keyword.impressions, 1),
            current_impressions=keyword.impressions,
            bid_history=history,
            cumulative_decrease_7d=sum(
                max(0.0, (keyword.current_bid - entry.bid) / keyword.current_bid)
                for entry in keyword.bid_history
                if keyword.current_bid and entry.bid < keyword.current_bid
            ),
            consecutive_decreases=self._consecutive_decreases(keyword.bid_history),
            zero_impressions_at_cap=keyword.impressions == 0 and keyword.current_bid >= min(self.max_bid, (ad_group.avg_cpc or keyword.current_bid or 0.0) * 3.0, self.max_bid * 0.5 if self.max_bid else self.max_bid),
        )

    def _consecutive_decreases(self, bid_history: Sequence[BidHistoryEntry]) -> int:
        count = 0
        for prev, cur in zip(bid_history, bid_history[1:]):
            if cur.bid < prev.bid:
                count += 1
            else:
                count = 0
        return count

    def _as_mapping(self, item: Any) -> dict[str, Any]:
        if isinstance(item, Mapping):
            return dict(item)
        if hasattr(item, "__dict__"):
            return dict(item.__dict__)
        return {key: getattr(item, key) for key in dir(item) if not key.startswith("_")}

    def _normalize_match_type(self, value: Any) -> KeywordMatchType:
        if isinstance(value, KeywordMatchType):
            return value
        if value is None:
            return KeywordMatchType.BROAD
        text = str(value.value if hasattr(value, "value") else value).upper()
        return KeywordMatchType[text] if text in KeywordMatchType.__members__ else KeywordMatchType.BROAD

    def _tokenize(self, term: str) -> list[str]:
        tokens = []
        for raw in term.lower().replace("/", " ").replace("-", " ").split():
            token = "".join(ch for ch in raw if ch.isalnum())
            if len(token) >= 3:
                tokens.append(token)
        return tokens
