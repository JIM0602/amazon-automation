"""Orders mock data generators.

Generates 50 mock orders with realistic Amazon-style fields.
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
#  Product pool (shared with dashboard)
# ---------------------------------------------------------------------------
_PRODUCTS = [
    {"asin": "B0CXYZ1001", "msku": "PDW-BED-001", "title": "PUDIWIND Memory Foam Pet Bed - Large", "price": 49.99},
    {"asin": "B0CXYZ1002", "msku": "PDW-BED-002", "title": "PUDIWIND Memory Foam Pet Bed - Medium", "price": 39.99},
    {"asin": "B0CXYZ1003", "msku": "PDW-FNT-001", "title": "PUDIWIND Auto Pet Water Fountain", "price": 29.99},
    {"asin": "B0CXYZ1004", "msku": "PDW-FNT-002", "title": "PUDIWIND Smart Pet Water Fountain Pro", "price": 45.99},
    {"asin": "B0CXYZ1005", "msku": "PDW-TOY-001", "title": "PUDIWIND Interactive Dog Toy Set", "price": 19.99},
    {"asin": "B0CXYZ1006", "msku": "PDW-TOY-002", "title": "PUDIWIND Durable Chew Toy 3-Pack", "price": 15.99},
    {"asin": "B0CXYZ1007", "msku": "PDW-GRM-001", "title": "PUDIWIND Self-Cleaning Pet Brush", "price": 24.99},
    {"asin": "B0CXYZ1008", "msku": "PDW-GRM-002", "title": "PUDIWIND Pet Nail Trimmer Kit", "price": 18.99},
    {"asin": "B0CXYZ1009", "msku": "PDW-BWL-001", "title": "PUDIWIND Slow Feeder Dog Bowl", "price": 16.99},
    {"asin": "B0CXYZ1010", "msku": "PDW-BWL-002", "title": "PUDIWIND Elevated Pet Bowl Stand", "price": 34.99},
    {"asin": "B0CXYZ1011", "msku": "PDW-LSH-001", "title": "PUDIWIND Retractable Dog Leash", "price": 22.99},
    {"asin": "B0CXYZ1012", "msku": "PDW-LSH-002", "title": "PUDIWIND Reflective Dog Harness", "price": 27.99},
    {"asin": "B0CXYZ1013", "msku": "PDW-CAR-001", "title": "PUDIWIND Pet Car Seat Cover", "price": 35.99},
    {"asin": "B0CXYZ1014", "msku": "PDW-CAR-002", "title": "PUDIWIND Pet Travel Carrier", "price": 55.99},
    {"asin": "B0CXYZ1015", "msku": "PDW-BLK-001", "title": "PUDIWIND Thermal Pet Blanket", "price": 25.99},
]

# Status distribution: Pending(10%), Shipped(20%), Delivered(50%), Cancelled(10%), Refunded(10%)
# Pre-built pool of 50 statuses with exact distribution, then shuffled with seed
_STATUS_POOL: list[str] = (
    ["Pending"] * 5
    + ["Shipped"] * 10
    + ["Delivered"] * 25
    + ["Cancelled"] * 5
    + ["Refunded"] * 5
)
_status_rng = Random(42)
_status_rng.shuffle(_STATUS_POOL)

_STORES = ["PUDIWIND US", "PUDIWIND EU", "PUDIWIND JP"]

_SHIPPING_METHODS = ["FBA", "FBM", "SFP"]

_LOGISTICS_PROVIDERS = ["Amazon Logistics", "UPS", "FedEx", "USPS", "DHL", "Yamato"]

_PROMO_CODES = [None, None, None, None, "SAVE10", "WELCOME20", "HOLIDAY15", "PET25OFF", None, None]

_BUYER_FIRST_NAMES = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona",
                      "George", "Helen", "Ivan", "Julia", "Kevin", "Laura", "Mike"]
_BUYER_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                     "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Wilson"]

_REGIONS = ["California", "New York", "Texas", "Florida", "Berlin", "Tokyo", "London", "Paris"]
_CITIES = ["Los Angeles", "New York City", "Houston", "Miami", "Berlin", "Tokyo", "London", "Paris"]
_ZIPS = ["90001", "10001", "77001", "33101", "10115", "100-0001", "SW1A 1AA", "75001"]

_BASE_DATE = datetime(2026, 3, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
#  Order generation
# ---------------------------------------------------------------------------

def _generate_orders() -> list[dict[str, Any]]:
    """Generate 50 mock orders with all required fields."""
    rng = Random(42)
    orders: list[dict[str, Any]] = []

    for i in range(50):
        order_id = f"114-{rng.randint(1000000, 9999999)}-{rng.randint(1000000, 9999999)}"
        product = rng.choice(_PRODUCTS)
        status = _STATUS_POOL[i]
        store = rng.choice(_STORES)
        quantity = rng.randint(1, 5)
        unit_price: float = float(product["price"])

        # Times
        order_time = _BASE_DATE + timedelta(
            days=rng.randint(0, 39),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        payment_time = order_time + timedelta(minutes=rng.randint(1, 30))

        refund_time = None
        if status == "Refunded":
            refund_time = payment_time + timedelta(days=rng.randint(3, 14))

        # Financial fields
        product_amount = round(unit_price * quantity, 2)
        promo_code = rng.choice(_PROMO_CODES)
        promo_discount = round(product_amount * rng.uniform(0.05, 0.20), 2) if promo_code else 0.0
        sales_revenue = round(product_amount - promo_discount, 2)

        # Refund
        refund_qty = quantity if status == "Refunded" else 0

        # Profit calculation
        cost_ratio = rng.uniform(0.25, 0.45)
        fba_fee = round(sales_revenue * rng.uniform(0.12, 0.18), 2)
        commission = round(sales_revenue * 0.15, 2)
        other_fees = round(rng.uniform(0.5, 3.0), 2)
        cogs = round(product_amount * cost_ratio, 2)
        order_profit = round(sales_revenue - fba_fee - commission - other_fees - cogs, 2)
        order_profit_rate = round(order_profit / sales_revenue, 4) if sales_revenue else 0.0

        # Buyer info
        buyer_first = rng.choice(_BUYER_FIRST_NAMES)
        buyer_last = rng.choice(_BUYER_LAST_NAMES)
        buyer_name = f"{buyer_first} {buyer_last}"
        buyer_email = f"{buyer_first.lower()}.{buyer_last.lower()}@example.com"

        # Shipping
        region_idx = rng.randint(0, len(_REGIONS) - 1)
        shipping_method = rng.choice(_SHIPPING_METHODS)
        logistics_provider = rng.choice(_LOGISTICS_PROVIDERS)
        tracking_number = f"1Z{rng.randint(100000000, 999999999)}" if status != "Pending" else None
        ship_time = order_time + timedelta(days=rng.randint(1, 3)) if status in ("Shipped", "Delivered", "Refunded") else None
        estimated_delivery = ship_time + timedelta(days=rng.randint(3, 7)) if ship_time else None

        order = {
            # List view columns (14 columns)
            "order_id": order_id,
            "order_time": order_time.isoformat(),
            "payment_time": payment_time.isoformat(),
            "refund_time": refund_time.isoformat() if refund_time else None,
            "status": status,
            "sales_revenue": sales_revenue,
            "product_info": {
                "image_url": IMAGE_PLACEHOLDER,
                "asin": product["asin"],
                "msku": product["msku"],
            },
            "product_name_sku": f"{product['title']} / {product['msku']}",
            "quantity": quantity,
            "refund_qty": refund_qty,
            "promo_code": promo_code,
            "product_amount": product_amount,
            "order_profit": order_profit,
            "order_profit_rate": order_profit_rate,
            "actions": ["view_detail"],

            # Detail-only fields
            "store": store,
            "shipping_method": shipping_method,
            "ship_time": ship_time.isoformat() if ship_time else None,
            "estimated_delivery": estimated_delivery.isoformat() if estimated_delivery else None,
            "logistics_provider": logistics_provider,
            "tracking_number": tracking_number,
            "buyer_name": buyer_name,
            "buyer_email": buyer_email,
            "buyer_tax_id": f"TAX-{rng.randint(100000, 999999)}" if rng.random() > 0.6 else None,
            "recipient_name": buyer_name,
            "recipient_phone": f"+1-{rng.randint(200, 999)}-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
            "recipient_zip": _ZIPS[region_idx],
            "recipient_region": _REGIONS[region_idx],
            "recipient_city": _CITIES[region_idx],
            "recipient_address": f"{rng.randint(100, 9999)} {rng.choice(['Main St', 'Oak Ave', 'Elm Dr', 'Park Blvd', 'River Rd'])} Apt {rng.randint(1, 200)}",
            "ioss_tax_id": f"IM{rng.randint(1000000000, 9999999999)}" if store == "PUDIWIND EU" else None,

            # Product detail for detail view
            "product_detail": {
                "msku": product["msku"],
                "fnsku": f"X00{rng.randint(10000, 99999)}FN",
                "asin": product["asin"],
                "title": product["title"],
                "item_discount": round(promo_discount / quantity, 2) if quantity else 0.0,
                "unit_price": unit_price,
                "quantity": quantity,
            },

            # Fee details (15+ items)
            "fee_details": {
                "product_amount": product_amount,
                "promo_discount": -promo_discount,
                "gift_wrap_fee": round(rng.uniform(0, 3.99), 2) if rng.random() > 0.8 else 0.0,
                "buyer_shipping_fee": round(rng.uniform(0, 5.99), 2) if shipping_method == "FBM" else 0.0,
                "tax": round(sales_revenue * rng.uniform(0.05, 0.10), 2),
                "sales_revenue": sales_revenue,
                "marketplace_tax": round(sales_revenue * rng.uniform(0.01, 0.03), 2),
                "fba_shipping_fee": fba_fee,
                "sales_commission": commission,
                "other_order_fees": other_fees,
                "amazon_payout": round(sales_revenue - fba_fee - commission - other_fees, 2),
                "cogs": cogs,
                "first_mile_fee": round(cogs * rng.uniform(0.08, 0.15), 2),
                "review_cost": round(rng.uniform(0, 5.0), 2) if rng.random() > 0.85 else 0.0,
                "order_profit": order_profit,
                "order_profit_rate": order_profit_rate,
            },
        }
        orders.append(order)

    return orders


# Cache the generated orders (deterministic, generated once)
_ALL_ORDERS: list[dict[str, Any]] = _generate_orders()


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def _match_time_range(order_time: str, time_range: str | None) -> bool:
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
    order_dt = datetime.fromisoformat(order_time)
    return start <= order_dt.astimezone(start.tzinfo) <= end


def get_orders(
    *,
    time_range: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Return paginated order list with filtering.

    Returns: {total_count, items[], summary_row}
    """
    filtered = list(_ALL_ORDERS)

    if time_range:
        filtered = [o for o in filtered if _match_time_range(o["order_time"], time_range)]

    # Filter by status
    if status:
        filtered = [o for o in filtered if o["status"].lower() == status.lower()]

    # Filter by search (order_id, product name, buyer name)
    if search:
        search_lower = search.lower()
        filtered = [
            o for o in filtered
            if search_lower in o["order_id"].lower()
            or search_lower in o["product_name_sku"].lower()
            or search_lower in o["buyer_name"].lower()
        ]

    # Sort by order_time desc
    filtered.sort(key=lambda x: x["order_time"], reverse=True)

    total_count = len(filtered)

    # Summary row (totals over ALL filtered items)
    sum_sales = sum(o["sales_revenue"] for o in filtered)
    sum_product_amount = sum(o["product_amount"] for o in filtered)
    sum_quantity = sum(o["quantity"] for o in filtered)
    sum_refund_qty = sum(o["refund_qty"] for o in filtered)
    sum_profit = sum(o["order_profit"] for o in filtered)
    avg_profit_rate = round(sum_profit / sum_sales, 4) if sum_sales else 0.0

    summary_row = {
        "order_id": "TOTAL",
        "order_time": None,
        "payment_time": None,
        "refund_time": None,
        "status": None,
        "sales_revenue": round(sum_sales, 2),
        "image_url": None,
        "asin": None,
        "msku": None,
        "product_name": None,
        "sku": None,
        "quantity": sum_quantity,
        "refund_quantity": sum_refund_qty,
        "promo_code": None,
        "product_amount": round(sum_product_amount, 2),
        "order_profit": round(sum_profit, 2),
        "profit_rate": avg_profit_rate,
    }

    # Paginate
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    page_items = [
        {
            "order_id": o["order_id"],
            "order_time": o["order_time"],
            "payment_time": o["payment_time"],
            "refund_time": o["refund_time"],
            "status": o["status"],
            "sales_revenue": o["sales_revenue"],
            "image_url": o["product_info"]["image_url"],
            "asin": o["product_info"]["asin"],
            "msku": o["product_info"]["msku"],
            "product_name": o["product_name_sku"].split(" / ")[0],
            "sku": o["product_info"]["msku"],
            "quantity": o["quantity"],
            "refund_quantity": o["refund_qty"],
            "promo_code": o["promo_code"],
            "product_amount": o["product_amount"],
            "order_profit": o["order_profit"],
            "profit_rate": o["order_profit_rate"],
        }
        for o in filtered[start_idx:end_idx]
    ]

    return {
        "total_count": total_count,
        "items": page_items,
        "summary_row": summary_row,
    }


def get_order_detail(order_id: str) -> Optional[dict[str, Any]]:
    """Return order detail with 4 sections.

    Returns None if not found. Otherwise:
    {
        basic_info: {...},
        shipping_info: {...},
        products: [...],
        fee_details: {...},
    }
    """
    order = None
    for o in _ALL_ORDERS:
        if o["order_id"] == order_id:
            order = o
            break

    if order is None:
        return None

    return {
        "basic_info": {
            "order_id": order["order_id"],
            "status": order["status"],
            "store": order["store"],
            "order_time": order["order_time"],
            "ship_time": order["ship_time"],
            "shipping_method": order["shipping_method"],
            "estimated_delivery": order["estimated_delivery"],
            "logistics_provider": order["logistics_provider"],
            "tracking_number": order["tracking_number"],
            "buyer_name": order["buyer_name"],
            "buyer_email": order["buyer_email"],
            "buyer_tax_id": order["buyer_tax_id"],
        },
        "shipping_info": {
            "recipient_name": order["recipient_name"],
            "recipient_phone": order["recipient_phone"],
            "recipient_zip": order["recipient_zip"],
            "recipient_region": order["recipient_region"],
            "recipient_address": order["recipient_address"],
            "ioss_tax_id": order["ioss_tax_id"],
        },
        "products": [order["product_detail"]],
        "fee_details": order["fee_details"],
    }
