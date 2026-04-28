"""Dashboard API endpoints backed by phase-1 database aggregations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.db.connection import get_db
from src.services.dashboard_service import get_dashboard_metrics, get_dashboard_trend, get_sku_ranking

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def dashboard_metrics(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return 10 metric cards for the dashboard overview.

    Each card contains value and change_percentage.
    tacos/acos values are 0.0~1.0 (ratio, not percentage).
    """
    return get_dashboard_metrics(db, time_range)


@router.get("/trend")
async def dashboard_trend(
    time_range: str = Query(default="site_today", description="Time range: site_today | last_24h | this_week | this_month | this_year"),
    metrics: Optional[str] = Query(default=None, description="Comma-separated metric names: sales,orders,units_sold,ad_spend,ad_orders,tacos,acos,returns_count"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return trend chart data points.

    Each data point: {date: "2026-01-01", sales: 1200, orders: 50, ...}
    """
    metrics_list: List[str] | None = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]

    return get_dashboard_trend(db, time_range, metrics_list)


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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return paginated SKU ranking with 12 data columns.

    Response: {items: [...], total_count: N, summary_row: {...}, data_quality: {...}}
    Store-level SP-API orderMetrics aggregates are never returned as a fake SKU row.
    """
    if time_range == "custom" and not (start_date and end_date):
        raise HTTPException(status_code=422, detail="custom time_range requires start_date and end_date")

    return get_sku_ranking(db, time_range, start_date, end_date, sort_by, sort_order, page, page_size)
