"""Ads dashboard aggregation backed by local Amazon Ads facts."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import AdsCampaign, AdsMetricsDaily, SalesDaily
from src.services.phase1_common import metric_card, paginate, ratio, resolve_date_window, safe_float, safe_int, sort_items


def _totals(db: Session, start, end) -> dict[str, float]:
    row = db.execute(
        select(
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0),
            func.coalesce(func.sum(AdsMetricsDaily.clicks), 0),
            func.coalesce(func.sum(AdsMetricsDaily.impressions), 0),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0),
            func.coalesce(func.sum(AdsMetricsDaily.ad_units), 0),
        ).where(AdsMetricsDaily.date.between(start, end))
    ).one()
    sales = db.execute(
        select(func.coalesce(func.sum(SalesDaily.sales_amount), 0)).where(SalesDaily.date.between(start, end))
    ).scalar_one()
    spend = safe_float(row[0])
    ad_sales = safe_float(row[1])
    clicks = safe_float(row[2])
    impressions = safe_float(row[3])
    orders = safe_float(row[4])
    return {
        "ad_spend": spend,
        "ad_sales": ad_sales,
        "clicks": clicks,
        "impressions": impressions,
        "ad_orders": orders,
        "ad_units": safe_float(row[5]),
        "acos": ratio(spend, ad_sales),
        "ctr": ratio(clicks, impressions),
        "cvr": ratio(orders, clicks),
        "cpc": ratio(spend, clicks),
        "tacos": ratio(spend, safe_float(sales)),
    }


def get_ads_dashboard_metrics(db: Session, time_range: str) -> dict[str, Any]:
    window = resolve_date_window(time_range)
    current = _totals(db, window.start, window.end)
    previous = _totals(db, window.previous_start, window.previous_end)
    keys = ["ad_spend", "ad_sales", "acos", "clicks", "impressions", "ctr", "cvr", "cpc", "ad_orders", "ad_units", "tacos"]
    return {key: metric_card(current[key], previous[key]) for key in keys}


def get_ads_dashboard_trend(db: Session, time_range: str, metrics: list[str] | None = None) -> list[dict[str, Any]]:
    window = resolve_date_window(time_range)
    rows = db.execute(
        select(
            AdsMetricsDaily.date,
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0).label("ad_spend"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0).label("ad_sales"),
            func.coalesce(func.sum(AdsMetricsDaily.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AdsMetricsDaily.impressions), 0).label("impressions"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0).label("ad_orders"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_units), 0).label("ad_units"),
        )
        .where(AdsMetricsDaily.date.between(window.start, window.end))
        .group_by(AdsMetricsDaily.date)
    ).all()
    sales_rows = db.execute(
        select(SalesDaily.date, func.coalesce(func.sum(SalesDaily.sales_amount), 0).label("sales"))
        .where(SalesDaily.date.between(window.start, window.end))
        .group_by(SalesDaily.date)
    ).all()
    sales_by_date = {row.date: safe_float(row.sales) for row in sales_rows}
    by_date: dict[Any, dict[str, Any]] = {}
    for row in rows:
        spend = safe_float(row.ad_spend)
        sales = safe_float(row.ad_sales)
        clicks = safe_float(row.clicks)
        impressions = safe_float(row.impressions)
        orders = safe_float(row.ad_orders)
        by_date[row.date] = {
            "date": row.date.isoformat(),
            "ad_spend": spend,
            "ad_sales": sales,
            "acos": ratio(spend, sales),
            "clicks": safe_int(clicks),
            "impressions": safe_int(impressions),
            "ctr": ratio(clicks, impressions),
            "cvr": ratio(orders, clicks),
            "cpc": ratio(spend, clicks),
            "ad_orders": safe_int(orders),
            "ad_units": safe_int(row.ad_units),
            "tacos": ratio(spend, sales_by_date.get(row.date, 0.0)),
        }

    wanted = set(metrics or [])
    result = []
    current = window.start
    while current <= window.end:
        item = by_date.get(current, {
            "date": current.isoformat(),
            "ad_spend": 0.0,
            "ad_sales": 0.0,
            "acos": 0.0,
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,
            "cvr": 0.0,
            "cpc": 0.0,
            "ad_orders": 0,
            "ad_units": 0,
            "tacos": 0.0,
        })
        if wanted:
            item = {"date": item["date"], **{key: item.get(key, 0) for key in wanted}}
        result.append(item)
        current = current.fromordinal(current.toordinal() + 1)
    return result


def get_campaign_ranking(
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
    rows = db.execute(
        select(
            AdsCampaign.campaign_id,
            AdsCampaign.campaign_name,
            func.coalesce(func.sum(AdsMetricsDaily.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AdsMetricsDaily.impressions), 0).label("impressions"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0).label("ad_orders"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0).label("ad_sales"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_units), 0).label("ad_units"),
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0).label("ad_spend"),
        )
        .outerjoin(AdsMetricsDaily, (AdsCampaign.campaign_id == AdsMetricsDaily.campaign_id) & AdsMetricsDaily.date.between(window.start, window.end))
        .group_by(AdsCampaign.campaign_id, AdsCampaign.campaign_name)
    ).all()
    items = []
    for row in rows:
        clicks = safe_float(row.clicks)
        impressions = safe_float(row.impressions)
        spend = safe_float(row.ad_spend)
        ad_sales = safe_float(row.ad_sales)
        orders = safe_float(row.ad_orders)
        items.append({
            "id": row.campaign_id,
            "campaign_id": row.campaign_id,
            "name": row.campaign_name,
            "campaign_name": row.campaign_name,
            "clicks": safe_int(clicks),
            "ctr": ratio(clicks, impressions),
            "ad_orders": safe_int(orders),
            "ad_sales": round(ad_sales, 2),
            "ad_units": safe_int(row.ad_units),
            "ad_spend": round(spend, 2),
            "cpc": ratio(spend, clicks),
            "acos": ratio(spend, ad_sales),
            "tacos": 0.0,
        })
    items = sort_items(items, sort_by, sort_order)
    paged, total = paginate(items, page, page_size)
    summary = defaultdict(float)
    for item in items:
        for key in ("clicks", "ad_orders", "ad_sales", "ad_units", "ad_spend"):
            summary[key] += safe_float(item.get(key))
    summary_row = dict(summary)
    summary_row["cpc"] = ratio(summary_row.get("ad_spend", 0), summary_row.get("clicks", 0))
    summary_row["acos"] = ratio(summary_row.get("ad_spend", 0), summary_row.get("ad_sales", 0))
    return {"items": paged, "total_count": total, "summary_row": summary_row}
