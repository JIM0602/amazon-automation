"""Orders API endpoints — list & detail.

All endpoints return mock data and require JWT authentication.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_current_user
from data.mock.orders import get_orders, get_order_detail

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
async def list_orders(
    time_range: Optional[str] = Query(default=None, description="Time range filter: site_today | last_24h | this_week | this_month | this_year"),
    time_field: Optional[str] = Query(default=None, description="Time field: order_time | payment_time | refund_time"),
    site: Optional[str] = Query(default=None, description="Site/marketplace filter, e.g. US"),
    shop: Optional[str] = Query(default=None, description="Shop/store fuzzy filter"),
    owner: Optional[str] = Query(default=None, description="Owner/salesperson fuzzy filter"),
    fulfillment: Optional[str] = Query(default=None, description="Fulfillment filter: FBA | FBM | SFP"),
    currency: Optional[str] = Query(default=None, description="Currency filter: USD | EUR | JPY"),
    order_type: Optional[str] = Query(default=None, description="Order type filter: Normal | Replacement"),
    search_type: Optional[str] = Query(default=None, description="Search field: order_id | asin | msku | buyer | product_name"),
    status: Optional[str] = Query(default=None, description="Filter by status: Pending | Shipped | Delivered | Cancelled | Refunded"),
    search: Optional[str] = Query(default=None, description="Search by order_id, product name, or buyer name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return paginated order list with filtering.

    Response: {total_count, items[], summary_row}
    Items contain 14 columns + actions.
    """
    result = get_orders(
        time_range=time_range,
        time_field=time_field,
        site=site,
        shop=shop,
        owner=owner,
        fulfillment=fulfillment,
        currency=currency,
        order_type=order_type,
        search_type=search_type,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/{order_id}")
async def order_detail(
    order_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return order detail with 4 sections.

    Sections:
    1. basic_info — order number, status, store, times, logistics, buyer info
    2. shipping_info — recipient, phone, zip, region, address, IOSS
    3. products — MSKU/FNSKU, ASIN/title, discount, amount, quantity
    4. fee_details — 15+ fee line items
    """
    detail = get_order_detail(order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id!r}")
    return detail
