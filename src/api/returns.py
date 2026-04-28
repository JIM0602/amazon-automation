"""Returns API endpoints — FBA return list.

All endpoints return mock data and require JWT authentication.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_user
from data.mock.returns import get_return_analysis, get_return_analysis_summary, get_returns

router = APIRouter(prefix="/api/returns", tags=["returns"])


@router.get("")
async def list_returns(
    time_range: Optional[str] = Query(default=None, description="Time range filter: site_today | last_24h | this_week | this_month | this_year"),
    reason: Optional[str] = Query(default=None, description="Filter by return reason: DEFECTIVE | UNWANTED_ITEM | CUSTOMER_CHANGED_MIND | WRONG_ITEM | DAMAGED_BY_FC | NOT_AS_DESCRIBED"),
    status: Optional[str] = Query(default=None, description="Filter by return status: Pending | Received | Refunded | Closed"),
    search: Optional[str] = Query(default=None, description="Search by order_id, product name/sku, or ASIN"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return paginated FBA return list with filtering.

    Response: {total_count, items[], summary_row}
    Items contain 18 columns for the return management table.
    """
    result = get_returns(
        time_range=time_range,
        reason=reason,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/analysis")
async def returns_analysis(
    dimension: str = Query(default="order", description="Analysis dimension: parent_asin | asin | msku | order"),
    site: Optional[str] = Query(default=None, description="Marketplace/site filter, e.g. US"),
    shop: Optional[str] = Query(default=None, description="Shop/store fuzzy filter"),
    owner: Optional[str] = Query(default=None, description="Owner/salesperson fuzzy filter"),
    tag: Optional[str] = Query(default=None, description="After-sale tag fuzzy filter"),
    time_range: Optional[str] = Query(default=None, description="Time range filter"),
    search_type: Optional[str] = Query(default=None, description="Search field: order_id | asin | parent_asin | msku | sku | product_name"),
    search: Optional[str] = Query(default=None, description="Search keyword"),
    reason: Optional[str] = Query(default=None, description="Return reason"),
    status: Optional[str] = Query(default=None, description="Return handling status"),
    disposition: Optional[str] = Query(default=None, description="Inventory disposition/property fuzzy filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return Saihu-style return analysis rows for order/product dimensions."""
    return get_return_analysis(
        dimension=dimension,
        site=site,
        shop=shop,
        owner=owner,
        tag=tag,
        time_range=time_range,
        search_type=search_type,
        search=search,
        reason=reason,
        status=status,
        disposition=disposition,
        page=page,
        page_size=page_size,
    )


@router.get("/analysis/summary")
async def returns_analysis_summary(
    dimension: str = Query(default="order", description="Analysis dimension: parent_asin | asin | msku | order"),
    site: Optional[str] = Query(default=None, description="Marketplace/site filter, e.g. US"),
    shop: Optional[str] = Query(default=None, description="Shop/store fuzzy filter"),
    owner: Optional[str] = Query(default=None, description="Owner/salesperson fuzzy filter"),
    tag: Optional[str] = Query(default=None, description="After-sale tag fuzzy filter"),
    time_range: Optional[str] = Query(default=None, description="Time range filter"),
    search_type: Optional[str] = Query(default=None, description="Search field"),
    search: Optional[str] = Query(default=None, description="Search keyword"),
    reason: Optional[str] = Query(default=None, description="Return reason"),
    status: Optional[str] = Query(default=None, description="Return handling status"),
    disposition: Optional[str] = Query(default=None, description="Inventory disposition/property fuzzy filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return aggregate metrics for return analysis filters."""
    return get_return_analysis_summary(
        dimension=dimension,
        site=site,
        shop=shop,
        owner=owner,
        tag=tag,
        time_range=time_range,
        search_type=search_type,
        search=search,
        reason=reason,
        status=status,
        disposition=disposition,
    )
