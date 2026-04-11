"""Dashboard API endpoints — metrics, trends, SKU ranking.

All endpoints return mock data and require JWT authentication.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

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
    metrics = get_metrics_data(time_range)
    return {"items": metrics}


@router.get("/trend")
async def dashboard_trend(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h | this_week | this_month | this_year"),
    metrics: Optional[str] = Query(default=None, description="Comma-separated metric names: sales,orders,units_sold,ad_spend,ad_orders,tacos,acos,returns_count"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return trend chart data points.

    Each data point: {date: "2026-01-01", sales: 1200, orders: 50, ...}
    """
    metrics_list: List[str] | None = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]

    data = get_trend_data(time_range, metrics_list)
    return {"items": data}


@router.get("/sku_ranking")
async def dashboard_sku_ranking(
    sort_by: str = Query(default="sales", description="Sort column"),
    sort_order: str = Query(default="desc", description="Sort order: asc | desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return paginated SKU ranking with 12 data columns.

    Response: {items: [...], total_count: N, summary_row: {...}}
    """
    result = get_sku_ranking(sort_by, sort_order, page, page_size)
    return result
