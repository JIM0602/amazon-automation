"""Sales dashboard aggregation backed by phase-1 database tables."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import AdsMetricsDaily, InventoryDaily, SalesDaily, Sku
from src.services.phase1_common import (
    metric_card,
    paginate,
    ratio,
    resolve_date_window,
    safe_float,
    safe_int,
    sort_items,
)


def _sales_totals(db: Session, start, end) -> dict[str, float]:
    row = db.execute(
        select(
            func.coalesce(func.sum(SalesDaily.sales_amount), 0),
            func.coalesce(func.sum(SalesDaily.order_count), 0),
            func.coalesce(func.sum(SalesDaily.units_sold), 0),
        ).where(SalesDaily.date.between(start, end))
    ).one()
    return {
        "sales": safe_float(row[0]),
        "orders": safe_float(row[1]),
        "units_sold": safe_float(row[2]),
    }


def _ads_totals(db: Session, start, end) -> dict[str, float]:
    row = db.execute(
        select(
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0),
        ).where(AdsMetricsDaily.date.between(start, end))
    ).one()
    return {
        "ad_spend": safe_float(row[0]),
        "ad_orders": safe_float(row[1]),
        "ad_sales": safe_float(row[2]),
    }


def get_dashboard_metrics(db: Session, time_range: str) -> dict[str, Any]:
    window = resolve_date_window(time_range)
    sales = _sales_totals(db, window.start, window.end)
    ads = _ads_totals(db, window.start, window.end)
    previous_sales = _sales_totals(db, window.previous_start, window.previous_end)
    previous_ads = _ads_totals(db, window.previous_start, window.previous_end)

    tacos = ratio(ads["ad_spend"], sales["sales"])
    previous_tacos = ratio(previous_ads["ad_spend"], previous_sales["sales"])
    acos = ratio(ads["ad_spend"], ads["ad_sales"])
    previous_acos = ratio(previous_ads["ad_spend"], previous_ads["ad_sales"])

    return {
        "total_sales": metric_card(sales["sales"], previous_sales["sales"]),
        "total_orders": metric_card(sales["orders"], previous_sales["orders"]),
        "units_sold": metric_card(sales["units_sold"], previous_sales["units_sold"]),
        "ad_spend": metric_card(ads["ad_spend"], previous_ads["ad_spend"]),
        "ad_orders": metric_card(ads["ad_orders"], previous_ads["ad_orders"]),
        "tacos": metric_card(tacos, previous_tacos),
        "acos": metric_card(acos, previous_acos),
        "returns_count": metric_card(0, 0),
    }


def get_dashboard_trend(
    db: Session,
    time_range: str,
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    window = resolve_date_window(time_range)
    by_date: dict[Any, dict[str, Any]] = defaultdict(dict)

    sales_rows = db.execute(
        select(
            SalesDaily.date,
            func.coalesce(func.sum(SalesDaily.sales_amount), 0).label("sales"),
            func.coalesce(func.sum(SalesDaily.order_count), 0).label("orders"),
            func.coalesce(func.sum(SalesDaily.units_sold), 0).label("units_sold"),
        )
        .where(SalesDaily.date.between(window.start, window.end))
        .group_by(SalesDaily.date)
    ).all()
    for row in sales_rows:
        by_date[row.date].update(
            sales=safe_float(row.sales),
            orders=safe_int(row.orders),
            units_sold=safe_int(row.units_sold),
        )

    ads_rows = db.execute(
        select(
            AdsMetricsDaily.date,
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0).label("ad_spend"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0).label("ad_sales"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0).label("ad_orders"),
        )
        .where(AdsMetricsDaily.date.between(window.start, window.end))
        .group_by(AdsMetricsDaily.date)
    ).all()
    for row in ads_rows:
        item = by_date[row.date]
        ad_spend = safe_float(row.ad_spend)
        ad_sales = safe_float(row.ad_sales)
        sales = safe_float(item.get("sales"))
        item.update(
            ad_spend=ad_spend,
            ad_orders=safe_int(row.ad_orders),
            acos=ratio(ad_spend, ad_sales),
            tacos=ratio(ad_spend, sales),
            returns_count=0,
        )

    wanted = set(metrics or [])
    result: list[dict[str, Any]] = []
    current = window.start
    while current <= window.end:
        item = {
            "date": current.isoformat(),
            "sales": 0.0,
            "orders": 0,
            "units_sold": 0,
            "ad_spend": 0.0,
            "ad_orders": 0,
            "tacos": 0.0,
            "acos": 0.0,
            "returns_count": 0,
            **by_date.get(current, {}),
        }
        if wanted:
            item = {"date": item["date"], **{key: item.get(key, 0) for key in wanted}}
        result.append(item)
        current = current.fromordinal(current.toordinal() + 1)
    return result


def get_sku_ranking(
    db: Session,
    time_range: str,
    start_date: str | None,
    end_date: str | None,
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    window = resolve_date_window(time_range, start_date, end_date)
    sales_rows = db.execute(
        select(
            SalesDaily.sku,
            func.max(SalesDaily.asin).label("asin"),
            func.coalesce(func.sum(SalesDaily.sales_amount), 0).label("sales"),
            func.coalesce(func.sum(SalesDaily.order_count), 0).label("orders"),
            func.coalesce(func.sum(SalesDaily.units_sold), 0).label("units_sold"),
        )
        .where(SalesDaily.date.between(window.start, window.end))
        .group_by(SalesDaily.sku)
    ).all()
    items_by_sku: dict[str, dict[str, Any]] = {}
    for row in sales_rows:
        items_by_sku[row.sku] = {
            "sku": row.sku,
            "asin": row.asin,
            "image_url": None,
            "sales": safe_float(row.sales),
            "orders": safe_int(row.orders),
            "units_sold": safe_int(row.units_sold),
            "returns_count": 0,
            "ad_spend": 0.0,
            "acos": 0.0,
            "tacos": 0.0,
            "gross_profit": None,
            "gross_margin": None,
            "fba_stock": 0,
            "estimated_days": None,
        }

    for row in db.execute(select(Sku.sku, Sku.image_url)).all():
        if row.sku in items_by_sku:
            items_by_sku[row.sku]["image_url"] = row.image_url

    ads_rows = db.execute(
        select(
            AdsMetricsDaily.sku,
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0).label("ad_spend"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0).label("ad_sales"),
        )
        .where(AdsMetricsDaily.date.between(window.start, window.end), AdsMetricsDaily.sku.isnot(None))
        .group_by(AdsMetricsDaily.sku)
    ).all()
    for row in ads_rows:
        item = items_by_sku.setdefault(row.sku, {"sku": row.sku, "sales": 0.0, "orders": 0, "units_sold": 0, "returns_count": 0})
        ad_spend = safe_float(row.ad_spend)
        item["ad_spend"] = ad_spend
        item["acos"] = ratio(ad_spend, safe_float(row.ad_sales))
        item["tacos"] = ratio(ad_spend, safe_float(item.get("sales")))

    inventory_sub = (
        select(InventoryDaily.sku, func.max(InventoryDaily.date).label("max_date"))
        .where(InventoryDaily.date <= window.end)
        .group_by(InventoryDaily.sku)
        .subquery()
    )
    inventory_rows = db.execute(
        select(InventoryDaily)
        .join(inventory_sub, (InventoryDaily.sku == inventory_sub.c.sku) & (InventoryDaily.date == inventory_sub.c.max_date))
    ).scalars()
    for row in inventory_rows:
        if row.sku in items_by_sku:
            items_by_sku[row.sku]["fba_stock"] = safe_int(row.fba_available)
            items_by_sku[row.sku]["estimated_days"] = safe_float(row.estimated_days) if row.estimated_days is not None else None

    items = sort_items(list(items_by_sku.values()), sort_by, sort_order)
    paged, total = paginate(items, page, page_size)
    summary = {
        "sales": round(sum(safe_float(i.get("sales")) for i in items), 2),
        "orders": sum(safe_int(i.get("orders")) for i in items),
        "units_sold": sum(safe_int(i.get("units_sold")) for i in items),
        "returns_count": 0,
        "ad_spend": round(sum(safe_float(i.get("ad_spend")) for i in items), 2),
        "acos": ratio(sum(safe_float(i.get("ad_spend")) for i in items), sum(safe_float(i.get("sales")) for i in items)),
        "tacos": ratio(sum(safe_float(i.get("ad_spend")) for i in items), sum(safe_float(i.get("sales")) for i in items)),
        "fba_stock": sum(safe_int(i.get("fba_stock")) for i in items),
    }
    return {"items": paged, "total_count": total, "summary_row": summary}
