"""Ads API endpoints — dashboard, 8 management tabs, campaign drill-down.

All endpoints return mock data and require JWT authentication.
Prefix: /api/ads
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_user
from data.mock.ads import (
    get_ad_groups,
    get_ad_products,
    get_ads_dashboard_metrics,
    get_ads_dashboard_trend,
    get_campaign_ad_groups,
    get_campaign_logs,
    get_campaign_negative_targeting,
    get_campaign_ranking,
    get_campaign_search_terms,
    get_campaign_settings,
    get_campaign_targeting,
    get_campaigns,
    get_logs,
    get_negative_targeting,
    get_portfolio_tree,
    get_portfolios,
    get_search_terms,
    get_targeting,
)

router = APIRouter(prefix="/api/ads", tags=["ads"])


# ---------------------------------------------------------------------------
#  Dashboard endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard/metrics")
async def ads_dashboard_metrics(
    time_range: str = Query(
        default="site_today",
        description="Time range: site_today | last_24h | this_week | this_month | this_year",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ad-specific metric cards (ad_spend, ad_sales, acos, clicks, etc.)."""
    metrics = get_ads_dashboard_metrics(time_range)
    return {"items": metrics}


@router.get("/dashboard/trend")
async def ads_dashboard_trend(
    time_range: str = Query(
        default="site_today",
        description="Time range: site_today | last_24h | this_week | this_month | this_year",
    ),
    metrics: Optional[str] = Query(
        default=None,
        description="Comma-separated metrics: ad_spend,ad_sales,acos,clicks,impressions,ctr,cvr,cpc,ad_orders,ad_units,tacos",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ad trend chart data supporting 11 metrics."""
    metrics_list: List[str] | None = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]

    data = get_ads_dashboard_trend(time_range, metrics_list)
    return {"items": data}


@router.get("/dashboard/campaign_ranking")
async def ads_campaign_ranking(
    sort_by: str = Query(default="ad_spend", description="Sort column"),
    sort_order: str = Query(default="desc", description="Sort order: asc | desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Campaign ranking with 10 columns.

    Response: {items, total_count, summary_row}
    """
    return get_campaign_ranking(sort_by, sort_order, page, page_size)


@router.get("/portfolio_tree")
async def ads_portfolio_tree(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Nested portfolio → campaign tree structure.

    Response: {items: [{id, name, campaign_count, campaigns: [{id, name}]}]}
    """
    tree = get_portfolio_tree()
    return {"items": tree}


# ---------------------------------------------------------------------------
#  Management tabs (8 tabs)
# ---------------------------------------------------------------------------

@router.get("/portfolios")
async def ads_portfolios(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Portfolios list with spend summary.

    Response: {items, total_count, summary_row}
    """
    return get_portfolios(page, page_size)


@router.get("/campaigns")
async def ads_campaigns(
    portfolio_id: Optional[str] = Query(default=None, description="Filter by portfolio ID"),
    ad_type: Optional[str] = Query(default=None, description="Filter by ad type: SP | SB | SD | ST"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Campaigns list with full columns.

    Columns: campaign_name, is_active, service_status, portfolio_name, ad_type,
    daily_budget, budget_remaining, bidding_strategy, impressions, clicks, ctr,
    ad_spend, cpc, ad_orders, cvr, acos, start_date

    Response: {items, total_count, summary_row}
    """
    return get_campaigns(portfolio_id, ad_type, page, page_size)


@router.get("/ad_groups")
async def ads_ad_groups(
    campaign_id: Optional[str] = Query(default=None, description="Filter by campaign ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ad groups list.

    Columns: group_name, is_active, product_count, service_status,
    campaign_name, portfolio_name, default_bid

    Response: {items, total_count, summary_row}
    """
    return get_ad_groups(campaign_id, page, page_size)


@router.get("/ad_products")
async def ads_ad_products(
    ad_group_id: Optional[str] = Query(default=None, description="Filter by ad group ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ad products list.

    Columns: product_title, asin, is_active, service_status, fba_available,
    price, reviews_count, rating, group_name, campaign_name

    Response: {items, total_count, summary_row}
    """
    return get_ad_products(ad_group_id, page, page_size)


@router.get("/targeting")
async def ads_targeting(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Targeting keywords list.

    Columns: keyword, is_active, service_status, match_type, group_name,
    campaign_name, bid, suggested_bid

    Response: {items, total_count, summary_row}
    """
    return get_targeting(page=page, page_size=page_size)


@router.get("/search_terms")
async def ads_search_terms(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Search terms list.

    Columns: search_term, targeting, match_type, suggested_bid,
    source_bid, aba_rank, rank_change_rate

    Response: {items, total_count, summary_row}
    """
    return get_search_terms(page, page_size)


@router.get("/negative_targeting")
async def ads_negative_targeting(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Negative targeting list.

    Columns: keyword, neg_status, match_type, group_name, campaign_name

    Response: {items, total_count, summary_row}
    """
    return get_negative_targeting(page=page, page_size=page_size)


@router.get("/logs")
async def ads_logs(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Operation logs list.

    Columns: operation_time, portfolio_name, ad_type, campaign_name,
    group_name, operation_target, operation_type, operation_content

    Response: {items, total_count, summary_row}
    """
    return get_logs(page, page_size)


# ---------------------------------------------------------------------------
#  Campaign drill-down endpoints
# ---------------------------------------------------------------------------

@router.get("/campaigns/{campaign_id}/ad_groups")
async def campaign_drill_ad_groups(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ad groups for a specific campaign."""
    return get_campaign_ad_groups(campaign_id, page, page_size)


@router.get("/campaigns/{campaign_id}/targeting")
async def campaign_drill_targeting(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Targeting for a specific campaign."""
    return get_campaign_targeting(campaign_id, page, page_size)


@router.get("/campaigns/{campaign_id}/search_terms")
async def campaign_drill_search_terms(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Search terms for a specific campaign."""
    return get_campaign_search_terms(campaign_id, page, page_size)


@router.get("/campaigns/{campaign_id}/negative_targeting")
async def campaign_drill_negative_targeting(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Negative targeting for a specific campaign."""
    return get_campaign_negative_targeting(campaign_id, page, page_size)


@router.get("/campaigns/{campaign_id}/logs")
async def campaign_drill_logs(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Operation logs for a specific campaign."""
    return get_campaign_logs(campaign_id, page, page_size)


@router.get("/campaigns/{campaign_id}/settings")
async def campaign_drill_settings(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Full settings for a specific campaign."""
    settings = get_campaign_settings(campaign_id)
    if settings is None:
        raise HTTPException(status_code=404, detail=f"Campaign not found: {campaign_id}")
    return settings
