"""Returns mock data generators.

Generates 30 mock FBA return records with realistic Amazon-style fields.
All generators use a fixed random seed (42) for reproducible results.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import Random
from typing import Any, Optional

from src.utils.timezone import (
    last_24h_range,
    month_range,
    site_today_range,
    week_range,
    year_range,
)

_rng = Random(42)

IMAGE_PLACEHOLDER = "https://placehold.co/80x80?text=SKU"

# ---------------------------------------------------------------------------
#  Product pool (shared with orders)
# ---------------------------------------------------------------------------
_PRODUCTS = [
    {"asin": "B0CXYZ1001", "parent_asin": "B0CXYZ1000", "msku": "PDW-BED-001", "title": "PUDIWIND Memory Foam Pet Bed - Large", "price": 49.99},
    {"asin": "B0CXYZ1002", "parent_asin": "B0CXYZ1000", "msku": "PDW-BED-002", "title": "PUDIWIND Memory Foam Pet Bed - Medium", "price": 39.99},
    {"asin": "B0CXYZ1003", "parent_asin": "B0CXYZ1003P", "msku": "PDW-FNT-001", "title": "PUDIWIND Auto Pet Water Fountain", "price": 29.99},
    {"asin": "B0CXYZ1004", "parent_asin": "B0CXYZ1003P", "msku": "PDW-FNT-002", "title": "PUDIWIND Smart Pet Water Fountain Pro", "price": 45.99},
    {"asin": "B0CXYZ1005", "parent_asin": "B0CXYZ1005P", "msku": "PDW-TOY-001", "title": "PUDIWIND Interactive Dog Toy Set", "price": 19.99},
    {"asin": "B0CXYZ1006", "parent_asin": "B0CXYZ1005P", "msku": "PDW-TOY-002", "title": "PUDIWIND Durable Chew Toy 3-Pack", "price": 15.99},
    {"asin": "B0CXYZ1007", "parent_asin": "B0CXYZ1007P", "msku": "PDW-GRM-001", "title": "PUDIWIND Self-Cleaning Pet Brush", "price": 24.99},
    {"asin": "B0CXYZ1008", "parent_asin": "B0CXYZ1007P", "msku": "PDW-GRM-002", "title": "PUDIWIND Pet Nail Trimmer Kit", "price": 18.99},
    {"asin": "B0CXYZ1009", "parent_asin": "B0CXYZ1009P", "msku": "PDW-BWL-001", "title": "PUDIWIND Slow Feeder Dog Bowl", "price": 16.99},
    {"asin": "B0CXYZ1010", "parent_asin": "B0CXYZ1009P", "msku": "PDW-BWL-002", "title": "PUDIWIND Elevated Pet Bowl Stand", "price": 34.99},
    {"asin": "B0CXYZ1011", "parent_asin": "B0CXYZ1011P", "msku": "PDW-LSH-001", "title": "PUDIWIND Retractable Dog Leash", "price": 22.99},
    {"asin": "B0CXYZ1012", "parent_asin": "B0CXYZ1011P", "msku": "PDW-LSH-002", "title": "PUDIWIND Reflective Dog Harness", "price": 27.99},
    {"asin": "B0CXYZ1013", "parent_asin": "B0CXYZ1013P", "msku": "PDW-CAR-001", "title": "PUDIWIND Pet Car Seat Cover", "price": 35.99},
    {"asin": "B0CXYZ1014", "parent_asin": "B0CXYZ1013P", "msku": "PDW-CAR-002", "title": "PUDIWIND Pet Travel Carrier", "price": 55.99},
    {"asin": "B0CXYZ1015", "parent_asin": "B0CXYZ1015P", "msku": "PDW-BLK-001", "title": "PUDIWIND Thermal Pet Blanket", "price": 25.99},
]

# Return reason distribution (30 items):
# DEFECTIVE(8), UNWANTED_ITEM(6), CUSTOMER_CHANGED_MIND(5), WRONG_ITEM(4), DAMAGED_BY_FC(4), NOT_AS_DESCRIBED(3)
_REASON_POOL: list[str] = (
    ["DEFECTIVE"] * 8
    + ["UNWANTED_ITEM"] * 6
    + ["CUSTOMER_CHANGED_MIND"] * 5
    + ["WRONG_ITEM"] * 4
    + ["DAMAGED_BY_FC"] * 4
    + ["NOT_AS_DESCRIBED"] * 3
)
_reason_rng = Random(42)
_reason_rng.shuffle(_REASON_POOL)

# Return status distribution (30 items):
# Pending(6), Received(10), Refunded(9), Closed(5)
_STATUS_POOL: list[str] = (
    ["Pending"] * 6
    + ["Received"] * 10
    + ["Refunded"] * 9
    + ["Closed"] * 5
)
_status_rng = Random(42)
_status_rng.shuffle(_STATUS_POOL)

# After-sale label types
_AFTER_SALE_LABELS = ["FBA退货", "FBA退货", "FBA退货", "FBA换货", "FBA退货"]

_STORES_SITES = ["PUDIWIND US", "PUDIWIND EU", "PUDIWIND JP"]

_WAREHOUSE_IDS = ["FTW1", "PHX6", "ONT8", "SDF8", "BFI4", "NRT1", "FRA3", "LHR2"]

_INVENTORY_ATTRIBUTES = ["可售", "不可售-客损", "不可售-仓损", "可售", "可售", "不可售-客损"]

_BUYER_REMARKS_POOL = [
    "Product arrived damaged",
    "Not what I expected from the description",
    "Wrong size/color received",
    "Changed my mind, no longer needed",
    "Product quality is poor",
    "Doesn't match the listing photos",
    "Received duplicate order",
    "Pet doesn't like it",
    "Too small for my pet",
    "Material feels cheap",
    None,
    None,
    None,
    None,
    None,
]

_BASE_DATE = datetime(2026, 3, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
#  Return record generation
# ---------------------------------------------------------------------------

def _generate_returns() -> list[dict[str, Any]]:
    """Generate 30 mock FBA return records with all required fields."""
    rng = Random(42)
    returns: list[dict[str, Any]] = []

    for i in range(30):
        product = rng.choice(_PRODUCTS)
        reason = _REASON_POOL[i]
        status = _STATUS_POOL[i]
        store_site = rng.choice(_STORES_SITES)

        # Times
        order_time = _BASE_DATE + timedelta(
            days=rng.randint(0, 30),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )
        return_time = order_time + timedelta(days=rng.randint(3, 21))
        site_return_time = return_time + timedelta(days=rng.randint(1, 5))

        # Quantities
        return_qty = rng.randint(1, 3)

        # IDs
        order_id = f"114-{rng.randint(1000000, 9999999)}-{rng.randint(1000000, 9999999)}"
        lpn_number = f"LPN{rng.randint(100000000, 999999999)}" if status != "Pending" else None

        record = {
            "order_id": order_id,
            "after_sale_label": rng.choice(_AFTER_SALE_LABELS),
            "return_time": return_time.isoformat(),
            "order_time": order_time.isoformat(),
            "site_return_time": site_return_time.isoformat(),
            "store_site": store_site,
            "product_info": {
                "image_url": IMAGE_PLACEHOLDER,
                "title": product["title"],
                "asin": product["asin"],
                "msku": product["msku"],
            },
            "product_name_sku": f"{product['title']} / {product['msku']}",
            "parent_asin": product["parent_asin"],
            "buyer_remarks": rng.choice(_BUYER_REMARKS_POOL),
            "return_qty": return_qty,
            "warehouse_id": rng.choice(_WAREHOUSE_IDS),
            "inventory_attribute": rng.choice(_INVENTORY_ATTRIBUTES),
            "return_reason": reason,
            "return_status": {
                "text": status,
                "badge": (
                    "warning" if status == "Pending"
                    else "processing" if status == "Received"
                    else "success" if status == "Refunded"
                    else "default"
                ),
            },
            "lpn_number": lpn_number,
            "remarks": None,
        }
        returns.append(record)

    return returns


# Cache the generated returns (deterministic, generated once)
_ALL_RETURNS: list[dict[str, Any]] = _generate_returns()


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def _match_time_range(return_time: str, time_range: str | None) -> bool:
    if not time_range:
        return True

    mapping = {
        "site_today": site_today_range,
        "last_24h": last_24h_range,
        "this_week": week_range,
        "this_month": month_range,
        "this_year": year_range,
    }
    range_func = mapping.get(time_range)
    if range_func is None:
        return True

    start, end = range_func()
    return_dt = datetime.fromisoformat(return_time)
    return start <= return_dt.astimezone(start.tzinfo) <= end


def get_returns(
    *,
    time_range: Optional[str] = None,
    reason: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Return paginated return list with filtering.

    Returns: {total_count, items[], summary_row}
    """
    filtered = list(_ALL_RETURNS)

    if time_range:
        filtered = [r for r in filtered if _match_time_range(r["return_time"], time_range)]

    # Filter by return reason
    if reason:
        filtered = [r for r in filtered if r["return_reason"].lower() == reason.lower()]

    # Filter by return status
    if status:
        filtered = [r for r in filtered if r["return_status"]["text"].lower() == status.lower()]

    # Filter by search (order_id, product name/sku, asin)
    if search:
        search_lower = search.lower()
        filtered = [
            r for r in filtered
            if search_lower in r["order_id"].lower()
            or search_lower in r["product_name_sku"].lower()
            or search_lower in r["product_info"]["asin"].lower()
            or search_lower in r["parent_asin"].lower()
        ]

    # Sort by return_time desc
    filtered.sort(key=lambda x: x["return_time"], reverse=True)

    total_count = len(filtered)

    # Summary row (totals over ALL filtered items)
    sum_return_qty = sum(r["return_qty"] for r in filtered)

    # Count by status
    status_counts: dict[str, int] = {}
    for r in filtered:
        s = r["return_status"]["text"]
        status_counts[s] = status_counts.get(s, 0) + 1

    # Count by reason
    reason_counts: dict[str, int] = {}
    for r in filtered:
        rsn = r["return_reason"]
        reason_counts[rsn] = reason_counts.get(rsn, 0) + 1

    summary_row = {
        "order_id": "TOTAL",
        "total_returns": total_count,
        "total_return_quantity": sum_return_qty,
        "return_quantity": sum_return_qty,
        "status_breakdown": status_counts,
        "reason_breakdown": reason_counts,
    }

    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = [
        {
            "order_id": r["order_id"],
            "after_sale_tags": [r["after_sale_label"]],
            "return_time": r["return_time"],
            "order_time": r["order_time"],
            "site_return_time": r["site_return_time"],
            "store": r["store_site"].rsplit(" ", 1)[0],
            "site": r["store_site"].rsplit(" ", 1)[-1],
            "image_url": r["product_info"]["image_url"],
            "asin": r["product_info"]["asin"],
            "msku": r["product_info"]["msku"],
            "product_title": r["product_info"]["title"],
            "product_name": r["product_info"]["title"],
            "sku": r["product_info"]["msku"],
            "parent_asin": r["parent_asin"],
            "buyer_notes": r["buyer_remarks"] or "",
            "return_quantity": r["return_qty"],
            "warehouse_id": r["warehouse_id"],
            "inventory_property": r["inventory_attribute"],
            "return_reason": r["return_reason"],
            "status": r["return_status"]["text"],
            "lpn_number": r["lpn_number"],
            "notes": r["remarks"] or "",
        }
        for r in filtered[start_idx:end_idx]
    ]

    return {
        "total_count": total_count,
        "items": page_items,
        "summary_row": summary_row,
    }
