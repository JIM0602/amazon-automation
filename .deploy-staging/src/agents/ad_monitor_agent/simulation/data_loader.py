from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from random import Random
from typing import Any

from src.agents.ad_monitor_agent.algorithm import (
    AdGroup,
    BidHistoryEntry,
    BusinessContext,
    Campaign,
    DaypartPerformance,
    KeywordMatchType,
    KeywordPerformance,
    PlacementPerformance,
    SearchTermPerformance,
)


@dataclass(slots=True)
class SimulationInput:
    campaigns: list[Campaign]
    ad_groups: list[AdGroup]
    keywords: list[KeywordPerformance]
    search_terms: list[SearchTermPerformance]
    hourly_data: list[DaypartPerformance]
    placement_data: list[PlacementPerformance]
    business_context: BusinessContext | None = None


class HistoricalDataLoader:
    """Load and prepare historical campaign data for simulation."""

    def load_from_dict(self, data: dict[str, Any]) -> SimulationInput:
        campaigns = [self._campaign_from_dict(row) for row in data.get("campaigns", [])]
        ad_groups = [self._ad_group_from_dict(row) for row in data.get("ad_groups", [])]
        keywords = [self._keyword_from_dict(row) for row in data.get("keywords", [])]
        search_terms = [self._search_term_from_dict(row) for row in data.get("search_terms", [])]
        hourly_data = [self._hourly_from_dict(row) for row in data.get("hourly_performance", [])]
        placement_data = [self._placement_from_dict(row) for row in data.get("placement_performance", [])]
        business_context = self._business_context_from_dict(data.get("business_context"))
        return SimulationInput(
            campaigns=campaigns,
            ad_groups=ad_groups,
            keywords=keywords,
            search_terms=search_terms,
            hourly_data=hourly_data,
            placement_data=placement_data,
            business_context=business_context,
        )

    def generate_sample_data(self, num_campaigns: int = 2, num_keywords_per: int = 5, days: int = 30) -> SimulationInput:
        rng = Random(42)
        campaigns: list[Campaign] = []
        ad_groups: list[AdGroup] = []
        keywords: list[KeywordPerformance] = []
        search_terms: list[SearchTermPerformance] = []
        hourly_data = [DaypartPerformance(hour=hour) for hour in range(24)]
        placement_data: list[PlacementPerformance] = []
        now = datetime(2026, 4, 9, 12, 0, 0)

        for campaign_index in range(num_campaigns):
            campaign_id = f"camp_{campaign_index + 1}"
            campaign = Campaign(
                campaign_id=campaign_id,
                name=f"Campaign {campaign_index + 1}",
                days_active=days,
                clicks=180 + campaign_index * 25,
                orders=18 + campaign_index * 4,
                spend=240.0 + campaign_index * 35.0,
                sales=720.0 + campaign_index * 120.0,
                asp=24.0,
                budget=100.0 + campaign_index * 40.0,
                organic_rank=8 + campaign_index,
                inventory_days=18.0,
            )
            campaigns.append(campaign)

            ad_group_id = f"ag_{campaign_index + 1}"
            ad_groups.append(
                AdGroup(
                    ad_group_id=ad_group_id,
                    campaign_id=campaign_id,
                    name=f"Ad Group {campaign_index + 1}",
                    current_bid=0.9 + campaign_index * 0.1,
                    avg_cpc=0.85 + campaign_index * 0.08,
                    budget=campaign.budget,
                )
            )

            for keyword_index in range(num_keywords_per):
                keyword_id = f"kw_{campaign_index + 1}_{keyword_index + 1}"
                clicks = 20 + keyword_index * 4 + campaign_index * 2
                orders = max(0, 2 + keyword_index // 2 - campaign_index % 2)
                spend = float(clicks) * (0.75 + keyword_index * 0.04)
                sales = float(max(orders, 1)) * (18.0 + keyword_index * 2.5)
                keyword = KeywordPerformance(
                    keyword_id=keyword_id,
                    campaign_id=campaign_id,
                    ad_group_id=ad_group_id,
                    keyword_text=f"sample keyword {campaign_index + 1}-{keyword_index + 1}",
                    match_type=KeywordMatchType.BROAD if keyword_index % 3 == 0 else KeywordMatchType.PHRASE,
                    current_bid=0.6 + keyword_index * 0.05,
                    clicks=clicks,
                    orders=orders,
                    spend=spend,
                    sales=sales,
                    impressions=clicks * (15 + keyword_index),
                    days_active=days,
                    bid_history=self._build_bid_history(now, keyword_index, clicks, orders, spend, sales, rng),
                )
                keywords.append(keyword)

                search_terms.append(
                    SearchTermPerformance(
                        campaign_id=campaign_id,
                        ad_group_id=ad_group_id,
                        search_term=f"sample term {campaign_index + 1}-{keyword_index + 1}",
                        match_type=keyword.match_type,
                        clicks=max(1, clicks - 5),
                        orders=max(0, orders - 1),
                        spend=spend * 0.8,
                        sales=sales * 0.85,
                    )
                )

                placement_data.append(
                    PlacementPerformance(
                        campaign_id=campaign_id,
                        placement="top_of_search",
                        clicks=clicks,
                        orders=orders,
                        spend=spend * 0.6,
                        sales=sales * 1.1,
                        impressions=clicks * 20,
                        current_multiplier=1.0,
                        strategy="fixed",
                        days_ago=keyword_index + 5,
                    )
                )

                for hour in range(24):
                    hourly_data[hour].clicks += max(0, clicks // 24)
                    hourly_data[hour].orders += max(0, orders // 24)
                    hourly_data[hour].spend += spend / 24.0
                    hourly_data[hour].sales += sales / 24.0
                    hourly_data[hour].impressions += max(1, keyword.impressions // 24)

        return SimulationInput(
            campaigns=campaigns,
            ad_groups=ad_groups,
            keywords=keywords,
            search_terms=search_terms,
            hourly_data=hourly_data,
            placement_data=placement_data,
            business_context=BusinessContext(asp_change_pct=0.0, inventory_days=18.0, organic_rank=10),
        )

    def _campaign_from_dict(self, row: dict[str, Any]) -> Campaign:
        return Campaign(
            campaign_id=str(row.get("campaign_id", "")),
            name=str(row.get("name", "")),
            phase=row.get("phase"),
            target_acos=float(row.get("target_acos", 30.0) or 0.0),
            days_active=int(row.get("days_active", 0) or 0),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
            asp=float(row.get("asp", 0.0) or 0.0),
            budget=float(row.get("budget", 0.0) or 0.0),
            cpc_strategy=str(row.get("cpc_strategy", "fixed")),
            organic_rank=row.get("organic_rank"),
            inventory_days=row.get("inventory_days"),
            attributes=dict(row.get("attributes", {}) or {}),
        )

    def _ad_group_from_dict(self, row: dict[str, Any]) -> AdGroup:
        return AdGroup(
            ad_group_id=str(row.get("ad_group_id", "")),
            campaign_id=str(row.get("campaign_id", "")),
            name=str(row.get("name", "")),
            current_bid=float(row.get("current_bid", 0.0) or 0.0),
            avg_cpc=float(row.get("avg_cpc", 0.0) or 0.0),
            budget=float(row.get("budget", 0.0) or 0.0),
            strategy=str(row.get("strategy", "fixed")),
            attributes=dict(row.get("attributes", {}) or {}),
        )

    def _keyword_from_dict(self, row: dict[str, Any]) -> KeywordPerformance:
        return KeywordPerformance(
            keyword_id=str(row.get("keyword_id", "")),
            campaign_id=str(row.get("campaign_id", "")),
            ad_group_id=str(row.get("ad_group_id", "")),
            keyword_text=str(row.get("keyword_text", "")),
            match_type=self._normalize_match_type(row.get("match_type")),
            current_bid=float(row.get("current_bid", 0.0) or 0.0),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
            impressions=int(row.get("impressions", 0) or 0),
            days_active=int(row.get("days_active", 0) or 0),
            bid_history=[self._bid_history_from_dict(item) for item in row.get("bid_history", [])],
            attributes=dict(row.get("attributes", {}) or {}),
        )

    def _search_term_from_dict(self, row: dict[str, Any]) -> SearchTermPerformance:
        return SearchTermPerformance(
            campaign_id=str(row.get("campaign_id", "")),
            ad_group_id=str(row.get("ad_group_id", "")),
            search_term=str(row.get("search_term", "")),
            match_type=self._normalize_match_type(row.get("match_type")),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
        )

    def _hourly_from_dict(self, row: dict[str, Any]) -> DaypartPerformance:
        return DaypartPerformance(
            hour=int(row.get("hour", 0) or 0),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
            impressions=int(row.get("impressions", 0) or 0),
        )

    def _placement_from_dict(self, row: dict[str, Any]) -> PlacementPerformance:
        return PlacementPerformance(
            campaign_id=str(row.get("campaign_id", "")),
            placement=str(row.get("placement", "")),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
            impressions=int(row.get("impressions", 0) or 0),
            current_multiplier=float(row.get("current_multiplier", 1.0) or 1.0),
            strategy=str(row.get("strategy", "fixed")),
            days_ago=int(row.get("days_ago", 0) or 0),
        )

    def _business_context_from_dict(self, row: Any) -> BusinessContext | None:
        if not row:
            return None
        if isinstance(row, BusinessContext):
            return row
        if not isinstance(row, dict):
            return None
        return BusinessContext(
            asp_change_pct=float(row.get("asp_change_pct", 0.0) or 0.0),
            inventory_days=row.get("inventory_days"),
            organic_rank=row.get("organic_rank"),
            campaign_id=str(row.get("campaign_id", "")),
            attributes=dict(row.get("attributes", {}) or {}),
        )

    def _bid_history_from_dict(self, row: dict[str, Any]) -> BidHistoryEntry:
        return BidHistoryEntry(
            timestamp=row.get("timestamp"),
            bid=float(row.get("bid", 0.0) or 0.0),
            clicks=int(row.get("clicks", 0) or 0),
            orders=int(row.get("orders", 0) or 0),
            spend=float(row.get("spend", 0.0) or 0.0),
            sales=float(row.get("sales", 0.0) or 0.0),
            impressions=int(row.get("impressions", 0) or 0),
        )

    def _normalize_match_type(self, value: Any) -> KeywordMatchType:
        if isinstance(value, KeywordMatchType):
            return value
        if value is None:
            return KeywordMatchType.BROAD
        text = str(getattr(value, "value", value)).upper()
        return KeywordMatchType[text] if text in KeywordMatchType.__members__ else KeywordMatchType.BROAD

    def _build_bid_history(
        self,
        now: datetime,
        keyword_index: int,
        clicks: int,
        orders: int,
        spend: float,
        sales: float,
        rng: Random,
    ) -> list[BidHistoryEntry]:
        history: list[BidHistoryEntry] = []
        for day_offset in range(6):
            timestamp = now - timedelta(days=day_offset + 5)
            bid = round(0.5 + keyword_index * 0.05 + day_offset * 0.03, 2)
            history.append(
                BidHistoryEntry(
                    timestamp=timestamp,
                    bid=bid,
                    clicks=max(1, clicks // 6 + rng.randint(0, 2)),
                    orders=max(0, orders // 6),
                    spend=round(spend / 6.0, 2),
                    sales=round(sales / 6.0, 2),
                    impressions=max(1, clicks * 10 + day_offset),
                )
            )
        return history
