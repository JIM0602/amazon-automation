"""Dashboard mock data generators.

All generators use a fixed random seed (42) for reproducible results.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from random import Random
from typing import Any

from src.utils.timezone import (
    last_24h_range,
    month_range,
    site_today_range,
    week_range,
    year_range,
)

_rng = Random(42)

# ---------------------------------------------------------------------------
#  SKU pool (shared across generators)
# ---------------------------------------------------------------------------
_SKUS = [
    {"sku": "PDW-BED-001", "title": "PUDIWIND Memory Foam Pet Bed - Large"},
    {"sku": "PDW-BED-002", "title": "PUDIWIND Memory Foam Pet Bed - Medium"},
    {"sku": "PDW-FNT-001", "title": "PUDIWIND Auto Pet Water Fountain"},
    {"sku": "PDW-FNT-002", "title": "PUDIWIND Smart Pet Water Fountain Pro"},
    {"sku": "PDW-TOY-001", "title": "PUDIWIND Interactive Dog Toy Set"},
    {"sku": "PDW-TOY-002", "title": "PUDIWIND Durable Chew Toy 3-Pack"},
    {"sku": "PDW-GRM-001", "title": "PUDIWIND Self-Cleaning Pet Brush"},
    {"sku": "PDW-GRM-002", "title": "PUDIWIND Pet Nail Trimmer Kit"},
    {"sku": "PDW-BWL-001", "title": "PUDIWIND Slow Feeder Dog Bowl"},
    {"sku": "PDW-BWL-002", "title": "PUDIWIND Elevated Pet Bowl Stand"},
    {"sku": "PDW-LSH-001", "title": "PUDIWIND Retractable Dog Leash"},
    {"sku": "PDW-LSH-002", "title": "PUDIWIND Reflective Dog Harness"},
    {"sku": "PDW-CAR-001", "title": "PUDIWIND Pet Car Seat Cover"},
    {"sku": "PDW-CAR-002", "title": "PUDIWIND Pet Travel Carrier"},
    {"sku": "PDW-BLK-001", "title": "PUDIWIND Thermal Pet Blanket"},
    {"sku": "PDW-BLK-002", "title": "PUDIWIND Waterproof Pet Mat"},
    {"sku": "PDW-CLR-001", "title": "PUDIWIND LED Pet Collar"},
    {"sku": "PDW-CLR-002", "title": "PUDIWIND Smart GPS Pet Collar"},
    {"sku": "PDW-TRT-001", "title": "PUDIWIND Natural Dog Treats"},
    {"sku": "PDW-TRT-002", "title": "PUDIWIND Dental Care Dog Chews"},
    {"sku": "PDW-HSE-001", "title": "PUDIWIND Wooden Pet House"},
    {"sku": "PDW-HSE-002", "title": "PUDIWIND Foldable Pet Crate"},
    {"sku": "PDW-FDR-001", "title": "PUDIWIND Automatic Pet Feeder"},
    {"sku": "PDW-FDR-002", "title": "PUDIWIND Portion Control Feeder"},
    {"sku": "PDW-SHM-001", "title": "PUDIWIND Oatmeal Pet Shampoo"},
]

IMAGE_PLACEHOLDER = "https://placehold.co/80x80?text=SKU"


# ---------------------------------------------------------------------------
#  Time range helpers
# ---------------------------------------------------------------------------

def _resolve_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Map a time_range string to (start, end) datetimes."""
    mapping = {
        "site_today": site_today_range,
        "last_24h": last_24h_range,
        "this_week": week_range,
        "this_month": month_range,
        "this_year": year_range,
    }
    func = mapping.get(time_range)
    if func is None:
        # Default to site_today
        func = site_today_range
    return func()


def _days_in_range(start: datetime, end: datetime) -> int:
    """Number of calendar days in a range (min 1)."""
    delta = (end.date() - start.date()).days
    return max(delta, 1)


# ---------------------------------------------------------------------------
#  Metrics (10 indicator cards)
# ---------------------------------------------------------------------------

def get_metrics_data(time_range: str = "site_today") -> list[dict[str, Any]]:
    """Generate 10 metric cards for the dashboard.

    Each card: {key, label, value, change_percentage, unit}
    tacos/acos are in 0.0~1.0 range (ratio, not percentage).
    """
    rng = Random(42)
    start, end = _resolve_time_range(time_range)
    days = _days_in_range(start, end)

    # Base daily values
    daily_sales = 3200.0
    daily_orders = 85
    daily_units = 120
    daily_ad_spend = 450.0
    daily_ad_orders = 25
    daily_returns = 3

    factor = days
    total_sales = round(daily_sales * factor * rng.uniform(0.85, 1.15), 2)
    total_orders = round(daily_orders * factor * rng.uniform(0.85, 1.15))
    units_sold = round(daily_units * factor * rng.uniform(0.85, 1.15))
    ad_spend = round(daily_ad_spend * factor * rng.uniform(0.85, 1.15), 2)
    ad_orders = round(daily_ad_orders * factor * rng.uniform(0.85, 1.15))
    returns_count = round(daily_returns * factor * rng.uniform(0.5, 1.5))

    # Derived ratios (0.0~1.0)
    tacos = round(ad_spend / total_sales, 4) if total_sales else 0.0
    acos = round(ad_spend / (ad_orders * (total_sales / total_orders)), 4) if (ad_orders and total_orders) else 0.0

    # Conversion rate & average order value
    conversion_rate = round(total_orders / (total_orders * rng.uniform(8, 15)), 4)
    avg_order_value = round(total_sales / total_orders, 2) if total_orders else 0.0

    metrics = [
        {"key": "total_sales", "label": "Total Sales", "value": total_sales, "change_percentage": round(rng.uniform(-15, 25), 1), "unit": "USD"},
        {"key": "total_orders", "label": "Total Orders", "value": total_orders, "change_percentage": round(rng.uniform(-10, 20), 1), "unit": ""},
        {"key": "units_sold", "label": "Units Sold", "value": units_sold, "change_percentage": round(rng.uniform(-10, 20), 1), "unit": ""},
        {"key": "ad_spend", "label": "Ad Spend", "value": ad_spend, "change_percentage": round(rng.uniform(-20, 30), 1), "unit": "USD"},
        {"key": "ad_orders", "label": "Ad Orders", "value": ad_orders, "change_percentage": round(rng.uniform(-15, 25), 1), "unit": ""},
        {"key": "tacos", "label": "TACoS", "value": tacos, "change_percentage": round(rng.uniform(-10, 10), 1), "unit": "ratio"},
        {"key": "acos", "label": "ACoS", "value": acos, "change_percentage": round(rng.uniform(-10, 10), 1), "unit": "ratio"},
        {"key": "returns_count", "label": "Returns", "value": returns_count, "change_percentage": round(rng.uniform(-20, 15), 1), "unit": ""},
        {"key": "conversion_rate", "label": "Conversion Rate", "value": conversion_rate, "change_percentage": round(rng.uniform(-5, 10), 1), "unit": "ratio"},
        {"key": "avg_order_value", "label": "Avg Order Value", "value": avg_order_value, "change_percentage": round(rng.uniform(-8, 12), 1), "unit": "USD"},
    ]
    return metrics


# ---------------------------------------------------------------------------
#  Trend data
# ---------------------------------------------------------------------------

def get_trend_data(
    time_range: str = "site_today",
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate trend data points for the dashboard chart.

    Returns: [{date: "2026-01-01", sales: 1200, orders: 50, ...}, ...]
    """
    rng = Random(42)
    start, end = _resolve_time_range(time_range)
    days = _days_in_range(start, end)

    if metrics is None:
        metrics = ["sales", "orders", "units_sold", "ad_spend", "ad_orders"]

    data_points: list[dict[str, Any]] = []
    for i in range(days):
        day_date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        point: dict[str, Any] = {"date": day_date}

        # Generate values for each requested metric
        if "sales" in metrics:
            point["sales"] = round(3200 * rng.uniform(0.6, 1.4), 2)
        if "orders" in metrics:
            point["orders"] = round(85 * rng.uniform(0.6, 1.4))
        if "units_sold" in metrics:
            point["units_sold"] = round(120 * rng.uniform(0.6, 1.4))
        if "ad_spend" in metrics:
            point["ad_spend"] = round(450 * rng.uniform(0.6, 1.4), 2)
        if "ad_orders" in metrics:
            point["ad_orders"] = round(25 * rng.uniform(0.6, 1.4))
        if "tacos" in metrics:
            s = point.get("sales") or (3200 * rng.uniform(0.6, 1.4))
            asp = point.get("ad_spend") or (450 * rng.uniform(0.6, 1.4))
            point["tacos"] = round(asp / s, 4) if s else 0.0
        if "acos" in metrics:
            point["acos"] = round(rng.uniform(0.10, 0.35), 4)
        if "returns_count" in metrics:
            point["returns_count"] = round(3 * rng.uniform(0.3, 2.0))

        data_points.append(point)

    return data_points


# ---------------------------------------------------------------------------
#  SKU ranking
# ---------------------------------------------------------------------------

def get_sku_ranking(
    sort_by: str = "sales",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Generate paginated SKU ranking data.

    Returns: {items: [...], total_count: N, summary_row: {...}}
    Each item has 12 columns:
        sku, image_url, sales, orders, units_sold, ad_spend, acos, tacos,
        gross_profit (null), gross_margin (null), fba_stock, estimated_days
    """
    rng = Random(42)

    # Generate all SKU rows
    all_items: list[dict[str, Any]] = []
    for sku_info in _SKUS:
        sales = round(rng.uniform(500, 15000), 2)
        orders = round(rng.uniform(15, 400))
        units_sold = round(orders * rng.uniform(1.0, 1.8))
        ad_spend = round(rng.uniform(50, 2000), 2)
        ad_orders_sku = round(rng.uniform(5, int(orders * 0.5)) if orders > 10 else rng.uniform(1, 5))
        avg_price = sales / orders if orders else 0
        acos = round(ad_spend / (ad_orders_sku * avg_price), 4) if (ad_orders_sku and avg_price) else 0.0
        tacos = round(ad_spend / sales, 4) if sales else 0.0
        fba_available = round(rng.uniform(0, 500))
        days_available = round(fba_available / max(units_sold / 30, 1), 1)

        all_items.append({
            "sku": sku_info["sku"],
            "image_url": IMAGE_PLACEHOLDER,
            "sales": sales,
            "orders": orders,
            "units_sold": units_sold,
            "ad_spend": ad_spend,
            "acos": min(acos, 1.0),
            "tacos": min(tacos, 1.0),
            "gross_profit": None,
            "gross_margin": None,
            "fba_stock": fba_available,
            "estimated_days": days_available,
        })

    # Sort
    reverse = sort_order == "desc"
    sort_key = sort_by if sort_by in ("sales", "orders", "units_sold", "ad_spend", "acos", "tacos", "fba_stock", "estimated_days") else "sales"
    all_items.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    # Paginate
    total_count = len(all_items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = all_items[start_idx:end_idx]

    # Summary row (totals / averages over ALL items)
    sum_sales = sum(i["sales"] for i in all_items)
    sum_orders = sum(i["orders"] for i in all_items)
    sum_units = sum(i["units_sold"] for i in all_items)
    sum_ad_spend = sum(i["ad_spend"] for i in all_items)
    avg_acos = round(sum(i["acos"] for i in all_items) / total_count, 4) if total_count else 0.0
    avg_tacos = round(sum(i["tacos"] for i in all_items) / total_count, 4) if total_count else 0.0

    summary_row = {
        "sku": "TOTAL",
        "image_url": None,
        "sales": round(sum_sales, 2),
        "orders": sum_orders,
        "units_sold": sum_units,
        "ad_spend": round(sum_ad_spend, 2),
        "acos": avg_acos,
        "tacos": avg_tacos,
        "gross_profit": None,
        "gross_margin": None,
        "fba_stock": sum(i["fba_stock"] for i in all_items),
        "estimated_days": None,
    }

    return {
        "items": page_items,
        "total_count": total_count,
        "summary_row": summary_row,
    }
