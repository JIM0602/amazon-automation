"""Ads mock data generators.

Generates reproducible advertising data using a fixed random seed (42).
Provides: 5 Portfolios, 20 Campaigns (SP/SB/SD distribution), 50 Ad Groups,
100 Ad Products, plus targeting, search terms, negative targeting, and logs.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from random import Random
from typing import Any

from src.utils.timezone import (
    last_24h_range,
    month_range,
    now_site_time,
    site_today_range,
    week_range,
    year_range,
)

_rng = Random(42)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_AD_TYPES = ["SP", "SB", "SD"]
_AD_TYPE_WEIGHTS = [12, 5, 3]  # 20 total campaigns: 12 SP, 5 SB, 3 SD

_BIDDING_STRATEGIES = ["Dynamic bids - down only", "Dynamic bids - up and down", "Fixed bids"]
_MATCH_TYPES = ["Exact", "Phrase", "Broad"]
_NEG_STATUSES = ["Campaign Negative", "Ad Group Negative"]
_SERVICE_STATUSES = ["Delivering", "Paused", "Out of budget", "Ended"]
_OPERATION_TYPES = [
    "修改预算", "修改出价", "暂停投放", "启用投放",
    "添加否定词", "修改匹配方式", "调整竞价策略", "新增Campaign",
]

_PORTFOLIO_NAMES = [
    "宠物床品系列",
    "宠物饮水器系列",
    "宠物玩具系列",
    "宠物美容系列",
    "宠物出行系列",
]

_CAMPAIGN_NAME_TEMPLATES = [
    "SP-Auto-{product}",
    "SP-Manual-Exact-{product}",
    "SP-Manual-Broad-{product}",
    "SP-Brand-Defense-{product}",
    "SP-Competitor-{product}",
    "SP-Category-{product}",
    "SP-ASIN-Targeting-{product}",
    "SP-Discovery-{product}",
    "SP-Top-of-Search-{product}",
    "SP-Product-Page-{product}",
    "SP-Retarget-{product}",
    "SP-Seasonal-{product}",
    "SB-Brand-Video-{product}",
    "SB-Store-Spotlight-{product}",
    "SB-Custom-Image-{product}",
    "SB-Headline-{product}",
    "SB-Collection-{product}",
    "SD-Retarget-Views-{product}",
    "SD-Audience-InMarket-{product}",
    "SD-Contextual-{product}",
]

_PRODUCT_TITLES = [
    "PUDIWIND Memory Foam Pet Bed - Large",
    "PUDIWIND Memory Foam Pet Bed - Medium",
    "PUDIWIND Auto Pet Water Fountain",
    "PUDIWIND Smart Pet Water Fountain Pro",
    "PUDIWIND Interactive Dog Toy Set",
    "PUDIWIND Durable Chew Toy 3-Pack",
    "PUDIWIND Self-Cleaning Pet Brush",
    "PUDIWIND Pet Nail Trimmer Kit",
    "PUDIWIND Slow Feeder Dog Bowl",
    "PUDIWIND Elevated Pet Bowl Stand",
]

_ASINS = [
    "B0CXYZ0001", "B0CXYZ0002", "B0CXYZ0003", "B0CXYZ0004", "B0CXYZ0005",
    "B0CXYZ0006", "B0CXYZ0007", "B0CXYZ0008", "B0CXYZ0009", "B0CXYZ0010",
]

_KEYWORDS = [
    "dog bed large", "pet bed memory foam", "orthopedic dog bed",
    "pet water fountain", "cat water fountain automatic", "dog fountain stainless",
    "interactive dog toy", "durable chew toy", "puzzle toy for dogs",
    "pet brush self cleaning", "dog nail trimmer", "pet grooming kit",
    "slow feeder bowl", "elevated dog bowl", "dog leash retractable",
    "dog harness no pull", "pet car seat cover", "dog travel carrier",
    "pet blanket waterproof", "led dog collar", "gps pet tracker",
    "automatic pet feeder", "dog treats natural", "dental chew dogs",
    "pet house wooden", "foldable dog crate", "pet shampoo oatmeal",
    "large dog bed washable", "cooling dog bed", "heated pet bed",
]

_SEARCH_TERMS = [
    "best dog bed for large dogs", "memory foam pet bed xl", "orthopedic bed dog",
    "automatic water fountain cat", "stainless steel pet fountain", "quiet pet fountain",
    "indestructible dog toy", "chew toys for aggressive chewers", "treat puzzle toy",
    "self cleaning brush for dogs", "professional nail trimmer pet", "grooming tools",
    "slow feeder bowl large dog", "raised dog bowl stand", "anti-slip dog bowl",
    "retractable leash 26ft", "no pull dog harness medium", "reflective harness",
    "waterproof car seat protector", "airline approved pet carrier", "pet travel bag",
    "smart pet feeder wifi", "natural dog treats grain free", "dental sticks dogs",
    "outdoor dog house waterproof", "heavy duty dog crate", "calming pet shampoo",
    "luxury dog bed", "dog bed with removable cover", "pet bed for senior dogs",
]


# ---------------------------------------------------------------------------
#  Time range resolution (shared with dashboard)
# ---------------------------------------------------------------------------

def _resolve_time_range(time_range: str) -> tuple[datetime, datetime]:
    mapping = {
        "site_today": site_today_range,
        "last_24h": last_24h_range,
        "this_week": week_range,
        "this_month": month_range,
        "this_year": year_range,
    }
    func = mapping.get(time_range, site_today_range)
    return func()


def _days_in_range(start: datetime, end: datetime) -> int:
    delta = (end.date() - start.date()).days
    return max(delta, 1)


def _resolve_custom_or_named_range(
    time_range: str,
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    if time_range == "custom" and start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        if end < start:
            start, end = end, start
        return start, end
    return _resolve_time_range(time_range)


# ---------------------------------------------------------------------------
#  Data pool generation (deterministic, cached at module level)
# ---------------------------------------------------------------------------

def _generate_portfolios(rng: Random) -> list[dict[str, Any]]:
    portfolios = []
    for i, name in enumerate(_PORTFOLIO_NAMES, 1):
        portfolios.append({
            "id": f"portfolio_{i:03d}",
            "name": name,
            "budget": round(rng.uniform(1000, 10000), 2),
            "spend": round(rng.uniform(200, 5000), 2),
        })
    return portfolios


def _generate_campaigns(rng: Random, portfolios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    campaigns = []
    product_names = ["PetBed", "Fountain", "Toy", "Brush", "Bowl",
                     "Leash", "Harness", "CarSeat", "Blanket", "Collar",
                     "Treats", "House", "Feeder", "Shampoo", "Crate",
                     "Mat", "Trimmer", "Carrier", "Chew", "Puzzle"]

    # Build ad_type list: 12 SP + 5 SB + 3 SD = 20
    ad_types: list[str] = []
    for t, count in zip(_AD_TYPES, _AD_TYPE_WEIGHTS):
        ad_types.extend([t] * count)

    for i in range(20):
        portfolio = portfolios[i % len(portfolios)]
        ad_type = ad_types[i]
        product = product_names[i]
        template = _CAMPAIGN_NAME_TEMPLATES[i]
        campaign_name = template.format(product=product)

        daily_budget = round(rng.uniform(20, 200), 2)
        budget_remaining = round(daily_budget * rng.uniform(0.1, 0.9), 2)
        impressions = round(rng.uniform(500, 50000))
        clicks = round(impressions * rng.uniform(0.005, 0.03))
        ad_spend = round(clicks * rng.uniform(0.3, 2.5), 2)
        ad_orders = round(clicks * rng.uniform(0.05, 0.2))
        ad_sales = round(ad_orders * rng.uniform(15, 80), 2) if ad_orders else 0.0
        ctr = round(clicks / impressions, 4) if impressions else 0.0
        cpc = round(ad_spend / clicks, 2) if clicks else 0.0
        cvr = round(ad_orders / clicks, 4) if clicks else 0.0
        acos = round(ad_spend / ad_sales, 4) if ad_sales else 0.0
        tacos = round(ad_spend / (ad_sales * rng.uniform(1.5, 3.0)), 4) if ad_sales else 0.0
        ad_units = round(ad_orders * rng.uniform(1.0, 1.5))
        is_active = rng.random() > 0.15
        service_status = "Delivering" if is_active else rng.choice(["Paused", "Out of budget", "Ended"])
        start_date = (now_site_time() - timedelta(days=rng.randint(30, 365))).strftime("%Y-%m-%d")

        campaigns.append({
            "id": f"campaign_{i + 1:03d}",
            "campaign_name": campaign_name,
            "is_active": is_active,
            "service_status": service_status,
            "portfolio_id": portfolio["id"],
            "portfolio_name": portfolio["name"],
            "ad_type": ad_type,
            "daily_budget": daily_budget,
            "budget_remaining": budget_remaining,
            "bidding_strategy": rng.choice(_BIDDING_STRATEGIES),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "ad_spend": ad_spend,
            "cpc": cpc,
            "ad_orders": ad_orders,
            "cvr": cvr,
            "acos": min(acos, 1.0),
            "tacos": min(tacos, 1.0),
            "ad_sales": ad_sales,
            "ad_units": ad_units,
            "start_date": start_date,
        })
    return campaigns


def _generate_ad_groups(rng: Random, campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ad_groups = []
    group_templates = ["Auto-Group", "Manual-Exact", "Manual-Broad", "Keyword-Group", "ASIN-Group"]

    for i in range(50):
        campaign = campaigns[i % len(campaigns)]
        group_name = f"{group_templates[i % len(group_templates)]}-{i + 1:03d}"
        product_count = rng.randint(1, 5)
        is_active = rng.random() > 0.1
        service_status = "Delivering" if is_active else rng.choice(["Paused", "Out of budget"])
        default_bid = round(rng.uniform(0.3, 3.0), 2)

        ad_groups.append({
            "id": f"adgroup_{i + 1:03d}",
            "group_name": group_name,
            "is_active": is_active,
            "product_count": product_count,
            "service_status": service_status,
            "campaign_id": campaign["id"],
            "campaign_name": campaign["campaign_name"],
            "portfolio_id": campaign["portfolio_id"],
            "portfolio_name": campaign["portfolio_name"],
            "default_bid": default_bid,
        })
    return ad_groups


def _generate_ad_products(rng: Random, ad_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products = []
    for i in range(100):
        ad_group = ad_groups[i % len(ad_groups)]
        title_idx = i % len(_PRODUCT_TITLES)
        asin_idx = i % len(_ASINS)
        is_active = rng.random() > 0.08
        service_status = "Delivering" if is_active else rng.choice(["Paused", "Ended"])
        fba_available = rng.randint(0, 500)
        price = round(rng.uniform(9.99, 79.99), 2)
        reviews_count = rng.randint(0, 3000)
        rating = round(rng.uniform(3.0, 5.0), 1)

        campaign = next(c for c in _CAMPAIGNS if c["id"] == ad_group["campaign_id"])

        products.append({
            "id": f"adproduct_{i + 1:04d}",
            "product_title": _PRODUCT_TITLES[title_idx],
            "asin": _ASINS[asin_idx],
            "is_active": is_active,
            "service_status": service_status,
            "fba_available": fba_available,
            "price": price,
            "reviews_count": reviews_count,
            "rating": rating,
            "group_id": ad_group["id"],
            "group_name": ad_group["group_name"],
            "campaign_id": ad_group["campaign_id"],
            "campaign_name": ad_group["campaign_name"],
            "portfolio_id": campaign["portfolio_id"],
            "portfolio_name": campaign["portfolio_name"],
            "ad_type": campaign["ad_type"],
        })
    return products


def _generate_targeting(rng: Random, ad_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targeting_items = []
    for i in range(80):
        ad_group = ad_groups[i % len(ad_groups)]
        keyword = _KEYWORDS[i % len(_KEYWORDS)]
        is_active = rng.random() > 0.1
        service_status = "Delivering" if is_active else "Paused"
        match_type = rng.choice(_MATCH_TYPES)
        bid = round(rng.uniform(0.3, 5.0), 2)
        suggested_bid = round(bid * rng.uniform(0.7, 1.5), 2)

        targeting_items.append({
            "id": f"targeting_{i + 1:04d}",
            "keyword": keyword,
            "is_active": is_active,
            "service_status": service_status,
            "match_type": match_type,
            "group_id": ad_group["id"],
            "group_name": ad_group["group_name"],
            "campaign_id": ad_group["campaign_id"],
            "campaign_name": ad_group["campaign_name"],
            "bid": bid,
            "suggested_bid": suggested_bid,
        })
    return targeting_items


def _generate_search_terms(rng: Random) -> list[dict[str, Any]]:
    search_terms = []
    for i in range(60):
        keyword = _KEYWORDS[i % len(_KEYWORDS)]
        search_term = _SEARCH_TERMS[i % len(_SEARCH_TERMS)]
        match_type = rng.choice(_MATCH_TYPES)
        suggested_bid = round(rng.uniform(0.5, 4.0), 2)
        source_bid = round(suggested_bid * rng.uniform(0.6, 1.3), 2)
        aba_rank = rng.randint(1000, 500000) if rng.random() > 0.3 else None
        rank_change_rate = round(rng.uniform(-0.5, 0.5), 4) if aba_rank else None

        search_terms.append({
            "id": f"searchterm_{i + 1:04d}",
            "search_term": search_term,
            "targeting": keyword,
            "match_type": match_type,
            "suggested_bid": suggested_bid,
            "source_bid": source_bid,
            "aba_rank": aba_rank,
            "rank_change_rate": rank_change_rate,
        })
    return search_terms


def _generate_negative_targeting(rng: Random, ad_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    neg_items = []
    neg_keywords = [
        "cheap", "free", "used", "broken", "refurbished",
        "diy", "homemade", "fake", "knock off", "replica",
        "wholesale", "bulk", "sample", "clearance", "damaged",
        "return", "defective", "recalled", "unsafe", "toxic",
    ]
    for i in range(40):
        ad_group = ad_groups[i % len(ad_groups)]
        keyword = neg_keywords[i % len(neg_keywords)]
        neg_status = rng.choice(_NEG_STATUSES)
        match_type = rng.choice(["Negative Exact", "Negative Phrase"])

        neg_items.append({
            "id": f"negtarget_{i + 1:04d}",
            "keyword": keyword,
            "neg_status": neg_status,
            "match_type": match_type,
            "group_id": ad_group["id"],
            "group_name": ad_group["group_name"],
            "campaign_id": ad_group["campaign_id"],
            "campaign_name": ad_group["campaign_name"],
        })
    return neg_items


def _generate_logs(rng: Random, campaigns: list[dict[str, Any]], portfolios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logs = []
    base_time = now_site_time()
    for i in range(100):
        campaign = campaigns[i % len(campaigns)]
        portfolio = portfolios[int(campaign["portfolio_id"].split("_")[1]) - 1]
        op_time = (base_time - timedelta(hours=rng.randint(1, 720))).strftime("%Y-%m-%d %H:%M:%S")
        op_type = rng.choice(_OPERATION_TYPES)

        # Generate operation content based on type
        if "预算" in op_type:
            old_val = round(rng.uniform(20, 150), 2)
            new_val = round(old_val * rng.uniform(0.8, 1.5), 2)
            op_content = f"日预算 ${old_val} → ${new_val}"
        elif "出价" in op_type:
            old_val = round(rng.uniform(0.3, 3.0), 2)
            new_val = round(old_val * rng.uniform(0.7, 1.4), 2)
            op_content = f"出价 ${old_val} → ${new_val}"
        elif "暂停" in op_type:
            op_content = "状态: 投放中 → 已暂停"
        elif "启用" in op_type:
            op_content = "状态: 已暂停 → 投放中"
        elif "否定词" in op_type:
            neg_kw = rng.choice(["cheap", "free", "used", "broken", "diy"])
            op_content = f"添加否定关键词: {neg_kw} (Negative Exact)"
        elif "匹配" in op_type:
            old_match = rng.choice(["Broad", "Phrase"])
            new_match = "Exact"
            op_content = f"匹配方式: {old_match} → {new_match}"
        elif "竞价策略" in op_type:
            old_strat = rng.choice(_BIDDING_STRATEGIES[:2])
            new_strat = _BIDDING_STRATEGIES[2]
            op_content = f"竞价策略: {old_strat} → {new_strat}"
        else:
            op_content = f"新增Campaign: {campaign['campaign_name']}"

        # Determine operation target
        group_name = f"Auto-Group-{(i % 50) + 1:03d}" if rng.random() > 0.3 else ""
        op_target = campaign["campaign_name"]
        if group_name:
            op_target = f"{campaign['campaign_name']} > {group_name}"

        logs.append({
            "id": f"log_{i + 1:04d}",
            "operation_time": op_time,
            "portfolio_name": portfolio["name"],
            "ad_type": campaign["ad_type"],
            "campaign_name": campaign["campaign_name"],
            "group_name": group_name,
            "operation_target": op_target,
            "operation_type": op_type,
            "operation_content": op_content,
        })

    # Sort logs by time descending
    logs.sort(key=lambda x: x["operation_time"], reverse=True)
    return logs


# ---------------------------------------------------------------------------
#  Cached data pools (generated once, deterministic)
# ---------------------------------------------------------------------------
_data_rng = Random(42)
_PORTFOLIOS = _generate_portfolios(_data_rng)
_CAMPAIGNS = _generate_campaigns(_data_rng, _PORTFOLIOS)
_AD_GROUPS = _generate_ad_groups(_data_rng, _CAMPAIGNS)
_AD_PRODUCTS = _generate_ad_products(_data_rng, _AD_GROUPS)
_TARGETING = _generate_targeting(_data_rng, _AD_GROUPS)
_SEARCH_TERMS_DATA = _generate_search_terms(_data_rng)
_NEGATIVE_TARGETING = _generate_negative_targeting(_data_rng, _AD_GROUPS)
_LOGS = _generate_logs(_data_rng, _CAMPAIGNS, _PORTFOLIOS)


# ---------------------------------------------------------------------------
#  Pagination helper
# ---------------------------------------------------------------------------

def _paginate(
    items: list[dict[str, Any]],
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Apply sorting + pagination and return {items, total_count, summary_row}."""
    if sort_by:
        reverse = sort_order == "desc"
        items = sorted(items, key=lambda x: x.get(sort_by) or 0, reverse=reverse)

    total_count = len(items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]

    return {
        "items": page_items,
        "total_count": total_count,
        "summary_row": None,
    }


# ---------------------------------------------------------------------------
#  Public API: Dashboard metrics
# ---------------------------------------------------------------------------

def get_ads_dashboard_metrics(time_range: str = "site_today") -> list[dict[str, Any]]:
    """Generate ad-specific metric cards.

    Returns: [{key, label, value, change_percentage, unit}, ...]
    """
    rng = Random(42)
    start, end = _resolve_time_range(time_range)
    days = _days_in_range(start, end)

    daily_ad_spend = 480.0
    daily_ad_sales = 1800.0
    daily_clicks = 850
    daily_impressions = 45000
    daily_ad_orders = 42
    daily_ad_units = 55

    factor = days
    ad_spend = round(daily_ad_spend * factor * rng.uniform(0.85, 1.15), 2)
    ad_sales = round(daily_ad_sales * factor * rng.uniform(0.85, 1.15), 2)
    clicks = round(daily_clicks * factor * rng.uniform(0.85, 1.15))
    impressions = round(daily_impressions * factor * rng.uniform(0.85, 1.15))
    ad_orders = round(daily_ad_orders * factor * rng.uniform(0.85, 1.15))
    ad_units = round(daily_ad_units * factor * rng.uniform(0.85, 1.15))

    acos = round(ad_spend / ad_sales, 4) if ad_sales else 0.0
    ctr = round(clicks / impressions, 4) if impressions else 0.0
    cvr = round(ad_orders / clicks, 4) if clicks else 0.0
    cpc = round(ad_spend / clicks, 2) if clicks else 0.0

    metrics = [
        {"key": "ad_spend", "label": "Ad Spend", "value": ad_spend, "change_percentage": round(rng.uniform(-15, 25), 1), "unit": "USD"},
        {"key": "ad_sales", "label": "Ad Sales", "value": ad_sales, "change_percentage": round(rng.uniform(-10, 30), 1), "unit": "USD"},
        {"key": "acos", "label": "ACoS", "value": acos, "change_percentage": round(rng.uniform(-10, 10), 1), "unit": "ratio"},
        {"key": "clicks", "label": "Clicks", "value": clicks, "change_percentage": round(rng.uniform(-15, 20), 1), "unit": ""},
        {"key": "impressions", "label": "Impressions", "value": impressions, "change_percentage": round(rng.uniform(-10, 25), 1), "unit": ""},
        {"key": "ctr", "label": "CTR", "value": ctr, "change_percentage": round(rng.uniform(-8, 12), 1), "unit": "ratio"},
        {"key": "cvr", "label": "CVR", "value": cvr, "change_percentage": round(rng.uniform(-8, 15), 1), "unit": "ratio"},
        {"key": "cpc", "label": "CPC", "value": cpc, "change_percentage": round(rng.uniform(-10, 15), 1), "unit": "USD"},
        {"key": "ad_orders", "label": "Ad Orders", "value": ad_orders, "change_percentage": round(rng.uniform(-10, 20), 1), "unit": ""},
        {"key": "ad_units", "label": "Ad Units", "value": ad_units, "change_percentage": round(rng.uniform(-10, 20), 1), "unit": ""},
    ]
    return metrics


def get_ads_dashboard_trend(
    time_range: str = "site_today",
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate ad trend data points.

    Supports 11 metrics: ad_spend, ad_sales, acos, clicks, impressions,
    ctr, cvr, cpc, ad_orders, ad_units, tacos.
    """
    rng = Random(42)
    start, end = _resolve_time_range(time_range)
    days = _days_in_range(start, end)

    if metrics is None:
        metrics = ["ad_spend", "ad_sales", "acos", "clicks", "impressions"]

    data_points: list[dict[str, Any]] = []
    for i in range(days):
        day_date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        point: dict[str, Any] = {"date": day_date}

        _spend = round(480 * rng.uniform(0.6, 1.4), 2)
        _sales = round(1800 * rng.uniform(0.6, 1.4), 2)
        _clicks = round(850 * rng.uniform(0.6, 1.4))
        _impressions = round(45000 * rng.uniform(0.6, 1.4))
        _orders = round(42 * rng.uniform(0.6, 1.4))
        _units = round(55 * rng.uniform(0.6, 1.4))

        if "ad_spend" in metrics:
            point["ad_spend"] = _spend
        if "ad_sales" in metrics:
            point["ad_sales"] = _sales
        if "acos" in metrics:
            point["acos"] = round(_spend / _sales, 4) if _sales else 0.0
        if "clicks" in metrics:
            point["clicks"] = _clicks
        if "impressions" in metrics:
            point["impressions"] = _impressions
        if "ctr" in metrics:
            point["ctr"] = round(_clicks / _impressions, 4) if _impressions else 0.0
        if "cvr" in metrics:
            point["cvr"] = round(_orders / _clicks, 4) if _clicks else 0.0
        if "cpc" in metrics:
            point["cpc"] = round(_spend / _clicks, 2) if _clicks else 0.0
        if "ad_orders" in metrics:
            point["ad_orders"] = _orders
        if "ad_units" in metrics:
            point["ad_units"] = _units
        if "tacos" in metrics:
            # TACoS uses total sales (simulated as ad_sales * 2~3x)
            total_sales = _sales * rng.uniform(2.0, 3.0)
            point["tacos"] = round(_spend / total_sales, 4) if total_sales else 0.0

        data_points.append(point)

    return data_points


def get_campaign_ranking(
    time_range: str = "site_today",
    start_date: str | None = None,
    end_date: str | None = None,
    sort_by: str = "ad_spend",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Campaign ranking for dashboard, 10 columns."""
    start, end = _resolve_custom_or_named_range(time_range, start_date, end_date)
    days = _days_in_range(start, end)
    multiplier = min(max(days / 7, 1), 12)

    items = []
    rng = Random(42)
    for c in _CAMPAIGNS:
        ad_spend = round(c["ad_spend"] * multiplier * rng.uniform(0.9, 1.1), 2)
        ad_sales = round(c["ad_sales"] * multiplier * rng.uniform(0.9, 1.1), 2)
        clicks = round(c["clicks"] * multiplier * rng.uniform(0.9, 1.1))
        ad_orders = round(c["ad_orders"] * multiplier * rng.uniform(0.9, 1.1))
        ad_units = round(c["ad_units"] * multiplier * rng.uniform(0.9, 1.1))
        ctr = round(clicks / max(round(c["impressions"] * multiplier * rng.uniform(0.9, 1.1)), 1), 4)
        cpc = round(ad_spend / clicks, 2) if clicks else 0.0
        acos = round(ad_spend / ad_sales, 4) if ad_sales else 0.0
        tacos = round(c["tacos"] * rng.uniform(0.9, 1.1), 4)

        items.append({
            "name": c["campaign_name"],
            "clicks": clicks,
            "ctr": ctr,
            "ad_orders": ad_orders,
            "ad_sales": ad_sales,
            "ad_units": ad_units,
            "ad_spend": ad_spend,
            "cpc": cpc,
            "acos": min(acos, 1.0),
            "tacos": min(tacos, 1.0),
        })

    valid_cols = {"name", "clicks", "ctr", "ad_orders", "ad_sales", "ad_units", "ad_spend", "cpc", "acos", "tacos"}
    sort_key = sort_by if sort_by in valid_cols else "ad_spend"
    reverse = sort_order == "desc"
    items.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    total_count = len(items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]

    summary_row = {
        "name": "TOTAL",
        "clicks": sum(it["clicks"] for it in items),
        "ctr": round(sum(it["ctr"] for it in items) / total_count, 4) if total_count else 0.0,
        "ad_orders": sum(it["ad_orders"] for it in items),
        "ad_sales": round(sum(it["ad_sales"] for it in items), 2),
        "ad_units": sum(it["ad_units"] for it in items),
        "ad_spend": round(sum(it["ad_spend"] for it in items), 2),
        "cpc": round(sum(it["cpc"] for it in items) / total_count, 2) if total_count else 0.0,
        "acos": round(sum(it["acos"] for it in items) / total_count, 4) if total_count else 0.0,
        "tacos": round(sum(it["tacos"] for it in items) / total_count, 4) if total_count else 0.0,
    }

    return {
        "items": page_items,
        "total_count": total_count,
        "summary_row": summary_row,
    }


# ---------------------------------------------------------------------------
#  Public API: Portfolio tree
# ---------------------------------------------------------------------------

def get_portfolio_tree() -> list[dict[str, Any]]:
    """Return nested portfolio → campaign structure."""
    tree = []
    for p in _PORTFOLIOS:
        p_campaigns = [c for c in _CAMPAIGNS if c["portfolio_id"] == p["id"]]
        tree.append({
            "id": p["id"],
            "name": p["name"],
            "campaign_count": len(p_campaigns),
            "campaigns": [{"id": c["id"], "name": c["campaign_name"]} for c in p_campaigns],
        })
    return tree


# ---------------------------------------------------------------------------
#  Public API: 8 management tabs
# ---------------------------------------------------------------------------

def get_portfolios(
    portfolio_id: str | None = None,
    portfolio_ids: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Portfolios list with campaign count and spend info."""
    selected_ids: set[str] = set()
    if portfolio_id:
        selected_ids.add(portfolio_id)
    if portfolio_ids:
        selected_ids.update(pid.strip() for pid in portfolio_ids.split(",") if pid.strip())

    items = []
    for p in _PORTFOLIOS:
        if selected_ids and p["id"] not in selected_ids:
            continue
        p_campaigns = [c for c in _CAMPAIGNS if c["portfolio_id"] == p["id"]]
        total_spend = sum(c["ad_spend"] for c in p_campaigns)
        total_sales = sum(c["ad_sales"] for c in p_campaigns)
        items.append({
            **p,
            "campaign_count": len(p_campaigns),
            "total_ad_spend": round(total_spend, 2),
            "total_ad_sales": round(total_sales, 2),
            "acos": round(total_spend / total_sales, 4) if total_sales else 0.0,
        })
    return _paginate(items, page, page_size)


def get_campaigns(
    portfolio_id: str | None = None,
    ad_type: str | None = None,
    service_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Campaigns list with all columns."""
    items = list(_CAMPAIGNS)
    if portfolio_id:
        items = [c for c in items if c["portfolio_id"] == portfolio_id]
    if ad_type:
        items = [c for c in items if c["ad_type"] == ad_type]
    if service_status:
        items = [c for c in items if c["service_status"] == service_status]

    result = _paginate(items, page, page_size)

    # Add summary row
    all_items = items
    total_count = len(all_items)
    if total_count:
        result["summary_row"] = {
            "campaign_name": "TOTAL",
            "impressions": sum(c["impressions"] for c in all_items),
            "clicks": sum(c["clicks"] for c in all_items),
            "ctr": round(sum(c["ctr"] for c in all_items) / total_count, 4),
            "ad_spend": round(sum(c["ad_spend"] for c in all_items), 2),
            "cpc": round(sum(c["cpc"] for c in all_items) / total_count, 2),
            "ad_orders": sum(c["ad_orders"] for c in all_items),
            "cvr": round(sum(c["cvr"] for c in all_items) / total_count, 4),
            "acos": round(sum(c["acos"] for c in all_items) / total_count, 4),
            "ad_sales": round(sum(c["ad_sales"] for c in all_items), 2),
        }
    return result


def get_ad_groups(
    campaign_id: str | None = None,
    portfolio_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Ad groups list."""
    items = list(_AD_GROUPS)
    if campaign_id:
        items = [g for g in items if g["campaign_id"] == campaign_id]
    if portfolio_id:
        items = [g for g in items if g["portfolio_id"] == portfolio_id]
    return _paginate(items, page, page_size)


def get_ad_products(
    ad_group_id: str | None = None,
    ad_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Ad products list."""
    items = list(_AD_PRODUCTS)
    if ad_group_id:
        items = [p for p in items if p["group_id"] == ad_group_id]
    if ad_type:
        items = [p for p in items if p["ad_type"] == ad_type]
    return _paginate(items, page, page_size)


def get_targeting(
    campaign_id: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Targeting keywords list."""
    items = list(_TARGETING)
    if campaign_id:
        items = [t for t in items if t["campaign_id"] == campaign_id]
    if keyword:
        normalized_keyword = keyword.strip().lower()
        items = [t for t in items if normalized_keyword in str(t["keyword"]).lower()]
    return _paginate(items, page, page_size)


def get_search_terms(
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search terms list."""
    items = list(_SEARCH_TERMS_DATA)
    if keyword:
        normalized_keyword = keyword.strip().lower()
        items = [s for s in items if normalized_keyword in str(s["search_term"]).lower()]
    return _paginate(items, page, page_size)


def get_negative_targeting(
    campaign_id: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Negative targeting list."""
    items = list(_NEGATIVE_TARGETING)
    if campaign_id:
        items = [n for n in items if n["campaign_id"] == campaign_id]
    if keyword:
        normalized_keyword = keyword.strip().lower()
        items = [n for n in items if normalized_keyword in str(n["keyword"]).lower()]
    return _paginate(items, page, page_size)


def get_logs(
    portfolio_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Operation logs list."""
    items = list(_LOGS)
    if portfolio_id:
        portfolio = next((p for p in _PORTFOLIOS if p["id"] == portfolio_id), None)
        if portfolio is None:
            items = []
        else:
            items = [log for log in items if log["portfolio_name"] == portfolio["name"]]
    return _paginate(items, page, page_size)


# ---------------------------------------------------------------------------
#  Public API: Campaign drill-down
# ---------------------------------------------------------------------------

def get_campaign_ad_groups(campaign_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Ad groups for a specific campaign."""
    return get_ad_groups(campaign_id=campaign_id, page=page, page_size=page_size)


def get_campaign_targeting(campaign_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Targeting for a specific campaign."""
    return get_targeting(campaign_id=campaign_id, page=page, page_size=page_size)


def get_campaign_search_terms(campaign_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Search terms for campaigns matching this campaign_id's keywords."""
    # Filter search terms by keywords that appear in this campaign's targeting
    campaign_keywords = {t["keyword"] for t in _TARGETING if t["campaign_id"] == campaign_id}
    items = [st for st in _SEARCH_TERMS_DATA if st["targeting"] in campaign_keywords]
    if not items:
        # Fallback: return a subset of all search terms
        items = _SEARCH_TERMS_DATA[: min(10, len(_SEARCH_TERMS_DATA))]
    return _paginate(items, page, page_size)


def get_campaign_negative_targeting(campaign_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Negative targeting for a specific campaign."""
    return get_negative_targeting(campaign_id=campaign_id, page=page, page_size=page_size)


def get_campaign_logs(campaign_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Logs for a specific campaign."""
    campaign = next((c for c in _CAMPAIGNS if c["id"] == campaign_id), None)
    if not campaign:
        return {"items": [], "total_count": 0, "summary_row": None}
    items = [log for log in _LOGS if log["campaign_name"] == campaign["campaign_name"]]
    return _paginate(items, page, page_size)


def get_campaign_settings(campaign_id: str) -> dict[str, Any] | None:
    """Full settings for a single campaign."""
    campaign = next((c for c in _CAMPAIGNS if c["id"] == campaign_id), None)
    if not campaign:
        return None
    return {
        **campaign,
        "status": campaign["service_status"],
        "ad_groups_count": len([g for g in _AD_GROUPS if g["campaign_id"] == campaign_id]),
        "products_count": len([p for p in _AD_PRODUCTS if p["campaign_id"] == campaign_id]),
        "targeting_count": len([t for t in _TARGETING if t["campaign_id"] == campaign_id]),
        "negative_targeting_count": len([n for n in _NEGATIVE_TARGETING if n["campaign_id"] == campaign_id]),
    }


def get_ad_group_settings(ad_group_id: str) -> dict[str, Any] | None:
    """Full settings for a single ad group."""
    ad_group = next((g for g in _AD_GROUPS if g["id"] == ad_group_id), None)
    if not ad_group:
        return None
    return {
        **ad_group,
        "ad_group_name": ad_group["group_name"],
        "status": ad_group["service_status"],
        "products_count": len([p for p in _AD_PRODUCTS if p["group_id"] == ad_group_id]),
        "targeting_count": len([t for t in _TARGETING if t["group_id"] == ad_group_id]),
        "negative_targeting_count": len([n for n in _NEGATIVE_TARGETING if n["group_id"] == ad_group_id]),
    }


def get_ad_group_ad_products(ad_group_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Ad products for a specific ad group."""
    return get_ad_products(ad_group_id=ad_group_id, page=page, page_size=page_size)


def get_ad_group_targeting(ad_group_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Targeting for a specific ad group."""
    items = [item for item in _TARGETING if item["group_id"] == ad_group_id]
    return _paginate(items, page, page_size)


def get_ad_group_search_terms(ad_group_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Search terms for a specific ad group."""
    ad_group_keywords = {item["keyword"] for item in _TARGETING if item["group_id"] == ad_group_id}
    items = [item for item in _SEARCH_TERMS_DATA if item["targeting"] in ad_group_keywords]
    if not items:
        items = _SEARCH_TERMS_DATA[: min(10, len(_SEARCH_TERMS_DATA))]
    return _paginate(items, page, page_size)


def get_ad_group_negative_targeting(ad_group_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Negative targeting for a specific ad group."""
    items = [item for item in _NEGATIVE_TARGETING if item["group_id"] == ad_group_id]
    return _paginate(items, page, page_size)


def get_ad_group_logs(ad_group_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Logs for a specific ad group."""
    ad_group = next((g for g in _AD_GROUPS if g["id"] == ad_group_id), None)
    if not ad_group:
        return {"items": [], "total_count": 0, "summary_row": None}
    items = [log for log in _LOGS if log["group_name"] == ad_group["group_name"]]
    return _paginate(items, page, page_size)


_SUPPORTED_ACTIONS = {
    "edit_budget": {
        "level": "L1",
        "message": "预算修改已提交到 mock 网关。",
    },
    "change_status": {
        "level": "L1",
        "message": "状态修改已提交到 mock 网关。",
    },
    "edit_bid": {
        "level": "L1",
        "message": "竞价修改已提交到 mock 网关。",
    },
    "add_negative_keyword": {
        "level": "L1",
        "message": "否定词添加已提交到 mock 网关。",
    },
}


def execute_ads_action(
    action_key: str,
    target_type: str,
    target_ids: list[str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a mock ads action and return unified action feedback."""
    action = _SUPPORTED_ACTIONS.get(action_key)
    if action is None:
        raise ValueError(f"Unsupported action: {action_key}")

    payload = dict(payload or {})

    if action_key == "edit_budget":
        budget_value_raw = payload.get("budgetValue")
        try:
            budget_value = round(float(budget_value_raw), 2)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid budget value") from exc

        updated = False
        for target_id in target_ids:
            campaign = next((c for c in _CAMPAIGNS if c["id"] == target_id), None)
            if campaign is not None:
                campaign["daily_budget"] = budget_value
                campaign["budget_remaining"] = min(campaign.get("budget_remaining", budget_value), budget_value)
                updated = True
            portfolio = next((p for p in _PORTFOLIOS if p["id"] == target_id), None)
            if portfolio is not None:
                portfolio["budget"] = budget_value
                updated = True
        if not updated:
            raise ValueError(f"Unsupported edit_budget target_ids: {target_ids}")

    if action_key == "change_status":
        next_status_raw = str(payload.get("nextStatus") or "").strip().lower()
        status_map = {
            "enabled": "Delivering",
            "paused": "Paused",
            "archived": "Ended",
        }
        service_status = status_map.get(next_status_raw)
        if service_status is None:
            raise ValueError("Invalid next status")

        updated = False
        for target_id in target_ids:
            campaign = next((c for c in _CAMPAIGNS if c["id"] == target_id), None)
            if campaign is not None:
                campaign["service_status"] = service_status
                campaign["is_active"] = service_status == "Delivering"
                updated = True
            portfolio_campaigns = [c for c in _CAMPAIGNS if c["portfolio_id"] == target_id]
            if portfolio_campaigns:
                for campaign_item in portfolio_campaigns:
                    campaign_item["service_status"] = service_status
                    campaign_item["is_active"] = service_status == "Delivering"
                updated = True
        if not updated:
            raise ValueError(f"Unsupported change_status target_ids: {target_ids}")

    return {
        "result": "success",
        "action_key": action_key,
        "target_type": target_type,
        "target_ids": list(target_ids),
        "level": action["level"],
        "committed": True,
        "is_real_write": False,
        "should_reload": True,
        "message": action["message"],
        "payload": payload,
    }
