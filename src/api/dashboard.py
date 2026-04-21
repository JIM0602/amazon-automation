"""Dashboard API endpoints — metrics, trends, SKU ranking.

All endpoints return mock data and require JWT authentication.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_user
from data.mock.dashboard import get_metrics_data, get_sku_ranking, get_trend_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def dashboard_metrics(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return 10 metric cards for the dashboard overview.

    Each card contains value and change_percentage.
    tacos/acos values are 0.0~1.0 (ratio, not percentage).
    """
    raw_metrics = get_metrics_data(time_range)
    # Transform list of {key, value, change_percentage, ...} into flat dict
    # keyed by metric key, e.g. {"total_sales": {"value": 1234, "change_percentage": 5.2}, ...}
    result: Dict[str, Any] = {}
    for item in raw_metrics:
        key = item["key"]
        result[key] = {
            "value": item["value"],
            "change_percentage": item["change_percentage"],
        }
    return result


@router.get("/trend")
async def dashboard_trend(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h | this_week | this_month | this_year"),
    metrics: Optional[str] = Query(default=None, description="Comma-separated metric names: sales,orders,units_sold,ad_spend,ad_orders,tacos,acos,returns_count"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return trend chart data points.

    Each data point: {date: "2026-01-01", sales: 1200, orders: 50, ...}
    """
    metrics_list: List[str] | None = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]

    data = get_trend_data(time_range, metrics_list)
    return data


@router.get("/sku_ranking")
async def dashboard_sku_ranking(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h | this_week | this_month | this_year | custom"),
    start_date: Optional[str] = Query(default=None, description="Custom start date: YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="Custom end date: YYYY-MM-DD"),
    sort_by: str = Query(default="sales", description="Sort column"),
    sort_order: str = Query(default="desc", description="Sort order: asc | desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return paginated SKU ranking with 12 data columns.

    Response: {items: [...], total_count: N, summary_row: {...}}
    """
    if time_range == "custom" and not (start_date and end_date):
        raise HTTPException(status_code=422, detail="custom time_range requires start_date and end_date")

    result = get_sku_ranking(time_range, start_date, end_date, sort_by, sort_order, page, page_size)
    return result
