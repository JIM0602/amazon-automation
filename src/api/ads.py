"""Ads API endpoints backed by phase-1 database services."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.db.connection import get_db
from src.services import ads_dashboard_service, ads_read_service, ads_write_service

router = APIRouter(prefix="/api/ads", tags=["ads"])


class AdsActionRequest(BaseModel):
    action_key: str = Field(..., min_length=1)
    target_type: str = Field(..., min_length=1)
    target_ids: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class AdsActionResponse(BaseModel):
    result: str
    action_key: str
    target_type: str
    target_ids: List[str]
    level: str
    committed: bool
    is_real_write: bool
    should_reload: bool
    message: str
    payload: Dict[str, Any]


# ---------------------------------------------------------------------------
#  Dashboard endpoints
# ---------------------------------------------------------------------------


@router.post("/actions")
async def ads_actions(
    request: AdsActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        return ads_write_service.execute_ads_action(
            db=db,
            action_key=request.action_key,
            target_type=request.target_type,
            target_ids=request.target_ids,
            payload=request.payload,
            operator_username=str(current_user.get("username", "unknown")),
        )
    except (ValueError, ads_write_service.AdsWriteError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad-specific metric cards (ad_spend, ad_sales, acos, clicks, etc.).

    Returns flat dict keyed by metric key, each containing {value, change_percentage}.
    """
    return ads_dashboard_service.get_ads_dashboard_metrics(db, time_range)


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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad trend chart data supporting 11 metrics.

    Returns {data: [...]}} where data is an array of trend data points.
    """
    metrics_list: List[str] | None = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]

    data = ads_dashboard_service.get_ads_dashboard_trend(db, time_range, metrics_list)
    return {"data": data}


@router.get("/dashboard/campaign_ranking")
async def ads_campaign_ranking(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h | this_week | this_month | this_year | custom"),
    start_date: Optional[str] = Query(default=None, description="Custom start date: YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="Custom end date: YYYY-MM-DD"),
    sort_by: str = Query(default="ad_spend", description="Sort column"),
    sort_order: str = Query(default="desc", description="Sort order: asc | desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Campaign ranking with 10 columns.

    Response: {items, total_count, summary_row}
    """
    if time_range == "custom" and not (start_date and end_date):
        raise HTTPException(status_code=422, detail="custom time_range requires start_date and end_date")

    return ads_dashboard_service.get_campaign_ranking(db, time_range, start_date, end_date, sort_by, sort_order, page, page_size)


@router.get("/portfolio_tree")
async def ads_portfolio_tree(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Nested portfolio → campaign tree structure.

    Response: {items: [{id, name, campaign_count, campaigns: [{id, name}]}]}
    """
    tree = ads_read_service.get_portfolio_tree(db)
    return {"items": tree}


# ---------------------------------------------------------------------------
#  Management tabs (8 tabs)
# ---------------------------------------------------------------------------

@router.get("/portfolios")
async def ads_portfolios(
    portfolio_id: Optional[str] = Query(default=None, description="Filter by single portfolio ID"),
    portfolio_ids: Optional[str] = Query(default=None, description="Comma-separated portfolio IDs"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Portfolios list with spend summary.

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_portfolios(db, portfolio_id=portfolio_id, portfolio_ids=portfolio_ids, page=page, page_size=page_size)


@router.get("/campaigns")
async def ads_campaigns(
    portfolio_id: Optional[str] = Query(default=None, description="Filter by portfolio ID"),
    ad_type: Optional[str] = Query(default=None, description="Filter by ad type: SP | SB | SD | ST"),
    service_status: Optional[str] = Query(default=None, description="Filter by service status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Campaigns list with full columns.

    Columns: campaign_name, is_active, service_status, portfolio_name, ad_type,
    daily_budget, budget_remaining, bidding_strategy, impressions, clicks, ctr,
    ad_spend, cpc, ad_orders, cvr, acos, start_date

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_campaigns(db, portfolio_id=portfolio_id, ad_type=ad_type, service_status=service_status, page=page, page_size=page_size)


@router.get("/ad_groups")
async def ads_ad_groups(
    campaign_id: Optional[str] = Query(default=None, description="Filter by campaign ID"),
    portfolio_id: Optional[str] = Query(default=None, description="Filter by portfolio ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad groups list.

    Columns: group_name, is_active, product_count, service_status,
    campaign_name, portfolio_name, default_bid

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_ad_groups(db, campaign_id=campaign_id, portfolio_id=portfolio_id, page=page, page_size=page_size)


@router.get("/ad_products")
async def ads_ad_products(
    ad_group_id: Optional[str] = Query(default=None, description="Filter by ad group ID"),
    ad_type: Optional[str] = Query(default=None, description="Filter by ad type: SP | SB | SD | ST"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad products list.

    Columns: product_title, asin, is_active, service_status, fba_available,
    price, reviews_count, rating, group_name, campaign_name

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_ad_products(db, ad_group_id=ad_group_id, ad_type=ad_type, page=page, page_size=page_size)


@router.get("/targeting")
async def ads_targeting(
    keyword: Optional[str] = Query(default=None, description="Filter by keyword"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Targeting keywords list.

    Columns: keyword, is_active, service_status, match_type, group_name,
    campaign_name, bid, suggested_bid

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_targeting(db, keyword=keyword, campaign_id=None, ad_group_id=None, page=page, page_size=page_size)


@router.get("/search_terms")
async def ads_search_terms(
    keyword: Optional[str] = Query(default=None, description="Filter by keyword"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Search terms list.

    Columns: search_term, targeting, match_type, suggested_bid,
    source_bid, aba_rank, rank_change_rate

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_search_terms(db, keyword=keyword, campaign_id=None, ad_group_id=None, page=page, page_size=page_size)


@router.get("/negative_targeting")
async def ads_negative_targeting(
    keyword: Optional[str] = Query(default=None, description="Filter by keyword"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Negative targeting list.

    Columns: keyword, neg_status, match_type, group_name, campaign_name

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_negative_targeting(db, keyword=keyword, campaign_id=None, ad_group_id=None, page=page, page_size=page_size)


@router.get("/logs")
async def ads_logs(
    portfolio_id: Optional[str] = Query(default=None, description="Filter by portfolio ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Operation logs list.

    Columns: operation_time, portfolio_name, ad_type, campaign_name,
    group_name, operation_target, operation_type, operation_content

    Response: {items, total_count, summary_row}
    """
    return ads_read_service.get_logs(db, portfolio_id=portfolio_id, campaign_id=None, ad_group_id=None, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
#  Campaign drill-down endpoints
# ---------------------------------------------------------------------------

@router.get("/campaigns/{campaign_id}/ad_groups")
async def campaign_drill_ad_groups(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad groups for a specific campaign."""
    return ads_read_service.get_ad_groups(db, campaign_id=campaign_id, portfolio_id=None, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/targeting")
async def campaign_drill_targeting(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Targeting for a specific campaign."""
    return ads_read_service.get_targeting(db, keyword=None, campaign_id=campaign_id, ad_group_id=None, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/search_terms")
async def campaign_drill_search_terms(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Search terms for a specific campaign."""
    return ads_read_service.get_search_terms(db, keyword=None, campaign_id=campaign_id, ad_group_id=None, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/negative_targeting")
async def campaign_drill_negative_targeting(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Negative targeting for a specific campaign."""
    return ads_read_service.get_negative_targeting(db, keyword=None, campaign_id=campaign_id, ad_group_id=None, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/logs")
async def campaign_drill_logs(
    campaign_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Operation logs for a specific campaign."""
    return ads_read_service.get_logs(db, portfolio_id=None, campaign_id=campaign_id, ad_group_id=None, page=page, page_size=page_size)


@router.get("/campaigns/{campaign_id}/settings")
async def campaign_drill_settings(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Full settings for a specific campaign."""
    campaign_settings = ads_read_service.get_campaign_settings(db, campaign_id)
    if campaign_settings is None:
        raise HTTPException(status_code=404, detail=f"Campaign not found: {campaign_id}")
    return campaign_settings


# ---------------------------------------------------------------------------
#  Ad group drill-down endpoints
# ---------------------------------------------------------------------------

@router.get("/ad_groups/{ad_group_id}")
async def ad_group_detail(
    ad_group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Full settings for a specific ad group."""
    ad_group = ads_read_service.get_ad_group_settings(db, ad_group_id)
    if ad_group is None:
        raise HTTPException(status_code=404, detail=f"Ad group not found: {ad_group_id}")
    return {"ad_group": ad_group}


@router.get("/ad_groups/{ad_group_id}/ad_products")
async def ad_group_drill_ad_products(
    ad_group_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ad products for a specific ad group."""
    return ads_read_service.get_ad_products(db, ad_group_id=ad_group_id, ad_type=None, page=page, page_size=page_size)


@router.get("/ad_groups/{ad_group_id}/targeting")
async def ad_group_drill_targeting(
    ad_group_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Targeting for a specific ad group."""
    return ads_read_service.get_targeting(db, keyword=None, campaign_id=None, ad_group_id=ad_group_id, page=page, page_size=page_size)


@router.get("/ad_groups/{ad_group_id}/search_terms")
async def ad_group_drill_search_terms(
    ad_group_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Search terms for a specific ad group."""
    return ads_read_service.get_search_terms(db, keyword=None, campaign_id=None, ad_group_id=ad_group_id, page=page, page_size=page_size)


@router.get("/ad_groups/{ad_group_id}/negative_targeting")
async def ad_group_drill_negative_targeting(
    ad_group_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Negative targeting for a specific ad group."""
    return ads_read_service.get_negative_targeting(db, keyword=None, campaign_id=None, ad_group_id=ad_group_id, page=page, page_size=page_size)


@router.get("/ad_groups/{ad_group_id}/logs")
async def ad_group_drill_logs(
    ad_group_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Operation logs for a specific ad group."""
    return ads_read_service.get_logs(db, portfolio_id=None, campaign_id=None, ad_group_id=ad_group_id, page=page, page_size=page_size)
