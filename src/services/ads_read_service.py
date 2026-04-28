"""Read services for the phase-1 ads management pages."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.db.models import (
    AdsActionLog,
    AdsAdGroup,
    AdsCampaign,
    AdsMetricsDaily,
    AdsNegativeTargeting,
    AdsSearchTerm,
    AdsTargeting,
)
from src.services.phase1_common import paginate, ratio, safe_float, safe_int, sort_items, today_utc


def _active(state: str | None) -> bool:
    return str(state or "").lower() in {"enabled", "active"}


def _serving_status_label(state: str | None, serving_status: str | None = None) -> str:
    if serving_status:
        return serving_status
    normalized = str(state or "").lower()
    if normalized == "enabled":
        return "Delivering"
    if normalized == "paused":
        return "Paused"
    if normalized == "archived":
        return "Ended"
    return state or "-"


def _campaign_metrics_subquery():
    start = today_utc().replace(day=1)
    end = today_utc()
    return (
        select(
            AdsMetricsDaily.campaign_id.label("campaign_id"),
            func.coalesce(func.sum(AdsMetricsDaily.impressions), 0).label("impressions"),
            func.coalesce(func.sum(AdsMetricsDaily.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AdsMetricsDaily.cost), 0).label("ad_spend"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_orders), 0).label("ad_orders"),
            func.coalesce(func.sum(AdsMetricsDaily.ad_sales), 0).label("ad_sales"),
        )
        .where(AdsMetricsDaily.date.between(start, end))
        .group_by(AdsMetricsDaily.campaign_id)
        .subquery()
    )


def get_portfolios(db: Session, portfolio_id: str | None, portfolio_ids: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsCampaign.portfolio_id, func.count(AdsCampaign.campaign_id).label("campaign_count"))
    ids = [item.strip() for item in (portfolio_ids or "").split(",") if item.strip()]
    if portfolio_id:
        query = query.where(AdsCampaign.portfolio_id == portfolio_id)
    if ids:
        query = query.where(AdsCampaign.portfolio_id.in_(ids))
    rows = db.execute(query.group_by(AdsCampaign.portfolio_id)).all()
    items = [
        {
            "id": row.portfolio_id or "unassigned",
            "portfolio_id": row.portfolio_id,
            "portfolio_name": row.portfolio_id or "未分组",
            "campaign_count": safe_int(row.campaign_count),
        }
        for row in rows
    ]
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": {"campaign_count": sum(i["campaign_count"] for i in items)}}


def get_portfolio_tree(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(AdsCampaign).order_by(AdsCampaign.portfolio_id, AdsCampaign.campaign_name)).scalars().all()
    grouped: dict[str, list[AdsCampaign]] = defaultdict(list)
    for campaign in rows:
        grouped[campaign.portfolio_id or "unassigned"].append(campaign)
    return [
        {
            "id": portfolio_id,
            "name": portfolio_id if portfolio_id != "unassigned" else "未分组",
            "campaign_count": len(campaigns),
            "campaigns": [{"id": c.campaign_id, "campaign_id": c.campaign_id, "name": c.campaign_name} for c in campaigns],
        }
        for portfolio_id, campaigns in grouped.items()
    ]


def get_campaigns(
    db: Session,
    portfolio_id: str | None,
    ad_type: str | None,
    service_status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    metrics = _campaign_metrics_subquery()
    query = select(AdsCampaign, metrics).outerjoin(metrics, AdsCampaign.campaign_id == metrics.c.campaign_id)
    if portfolio_id:
        query = query.where(AdsCampaign.portfolio_id == portfolio_id)
    if ad_type:
        query = query.where(AdsCampaign.ad_type == ad_type)
    if service_status:
        status_map = {"Delivering": "enabled", "Paused": "paused", "Ended": "archived"}
        mapped_state = status_map.get(service_status)
        query = query.where(AdsCampaign.state == mapped_state) if mapped_state else query.where(AdsCampaign.serving_status == service_status)
    rows = db.execute(query).all()
    items = []
    for row in rows:
        campaign = row[0]
        impressions = safe_float(row.impressions)
        clicks = safe_float(row.clicks)
        spend = safe_float(row.ad_spend)
        sales = safe_float(row.ad_sales)
        orders = safe_float(row.ad_orders)
        items.append({
            "id": campaign.campaign_id,
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.campaign_name,
            "name": campaign.campaign_name,
            "is_active": _active(campaign.state),
            "state": campaign.state,
            "status": campaign.state,
            "service_status": _serving_status_label(campaign.state, campaign.serving_status),
            "portfolio_id": campaign.portfolio_id,
            "portfolio_name": campaign.portfolio_id or "未分组",
            "ad_type": campaign.ad_type,
            "daily_budget": campaign.daily_budget,
            "budget_remaining": None,
            "bidding_strategy": campaign.bidding_strategy,
            "impressions": safe_int(impressions),
            "clicks": safe_int(clicks),
            "ctr": ratio(clicks, impressions),
            "ad_spend": round(spend, 2),
            "cpc": ratio(spend, clicks),
            "ad_orders": safe_int(orders),
            "cvr": ratio(orders, clicks),
            "acos": ratio(spend, sales),
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        })
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": _summary(items)}


def get_ad_groups(db: Session, campaign_id: str | None, portfolio_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsAdGroup, AdsCampaign).join(AdsCampaign, AdsAdGroup.campaign_id == AdsCampaign.campaign_id)
    if campaign_id:
        query = query.where(AdsAdGroup.campaign_id == campaign_id)
    if portfolio_id:
        query = query.where(AdsCampaign.portfolio_id == portfolio_id)
    rows = db.execute(query).all()
    items = [
        {
            "id": ad_group.ad_group_id,
            "ad_group_id": ad_group.ad_group_id,
            "ad_group_name": ad_group.group_name,
            "group_name": ad_group.group_name,
            "is_active": _active(ad_group.state),
            "status": ad_group.state,
            "state": ad_group.state,
            "product_count": 0,
            "service_status": _serving_status_label(ad_group.state),
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.campaign_name,
            "portfolio_id": campaign.portfolio_id,
            "portfolio_name": campaign.portfolio_id or "未分组",
            "default_bid": ad_group.default_bid,
        }
        for ad_group, campaign in rows
    ]
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": {"product_count": 0}}


def get_ad_products(db: Session, ad_group_id: str | None, ad_type: str | None, page: int, page_size: int) -> dict[str, Any]:
    return {"items": [], "total_count": 0, "summary_row": {}}


def get_targeting(db: Session, keyword: str | None, campaign_id: str | None, ad_group_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsTargeting, AdsAdGroup, AdsCampaign).outerjoin(AdsAdGroup, AdsTargeting.ad_group_id == AdsAdGroup.ad_group_id).outerjoin(AdsCampaign, AdsTargeting.campaign_id == AdsCampaign.campaign_id)
    if keyword:
        query = query.where(AdsTargeting.keyword_text.ilike(f"%{keyword}%"))
    if campaign_id:
        query = query.where(AdsTargeting.campaign_id == campaign_id)
    if ad_group_id:
        query = query.where(AdsTargeting.ad_group_id == ad_group_id)
    rows = db.execute(query).all()
    items = []
    for targeting, ad_group, campaign in rows:
        items.append({
            "id": targeting.targeting_id,
            "targeting_id": targeting.targeting_id,
            "keyword": targeting.keyword_text,
            "keyword_text": targeting.keyword_text,
            "is_active": _active(targeting.state),
            "status": targeting.state,
            "service_status": _serving_status_label(targeting.state),
            "match_type": targeting.match_type,
            "group_name": ad_group.group_name if ad_group else None,
            "ad_group_id": targeting.ad_group_id,
            "campaign_id": targeting.campaign_id,
            "campaign_name": campaign.campaign_name if campaign else None,
            "bid": targeting.bid,
            "suggested_bid": targeting.suggested_bid,
        })
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": {}}


def get_search_terms(db: Session, keyword: str | None, campaign_id: str | None, ad_group_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsSearchTerm, AdsCampaign).outerjoin(AdsCampaign, AdsSearchTerm.campaign_id == AdsCampaign.campaign_id)
    if keyword:
        query = query.where(or_(AdsSearchTerm.search_term.ilike(f"%{keyword}%"), AdsSearchTerm.targeting_keyword.ilike(f"%{keyword}%")))
    if campaign_id:
        query = query.where(AdsSearchTerm.campaign_id == campaign_id)
    if ad_group_id:
        query = query.where(AdsSearchTerm.ad_group_id == ad_group_id)
    rows = db.execute(query.order_by(AdsSearchTerm.date.desc())).all()
    items = [
        {
            "id": f"{term.campaign_id}:{term.ad_group_id}:{term.search_term}",
            "date": term.date.isoformat(),
            "search_term": term.search_term,
            "targeting": term.targeting_keyword,
            "targeting_keyword": term.targeting_keyword,
            "match_type": term.match_type,
            "suggested_bid": term.suggested_bid,
            "source_bid": None,
            "aba_rank": None,
            "rank_change_rate": None,
            "campaign_id": term.campaign_id,
            "campaign_name": campaign.campaign_name if campaign else None,
            "ad_group_id": term.ad_group_id,
            "impressions": term.impressions,
            "clicks": term.clicks,
            "ad_spend": term.cost,
            "ad_orders": term.ad_orders,
            "ad_sales": term.ad_sales,
            "acos": term.acos,
            "cvr": term.cvr,
        }
        for term, campaign in rows
    ]
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": _summary(items)}


def get_negative_targeting(db: Session, keyword: str | None, campaign_id: str | None, ad_group_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsNegativeTargeting, AdsAdGroup, AdsCampaign).outerjoin(AdsAdGroup, AdsNegativeTargeting.ad_group_id == AdsAdGroup.ad_group_id).outerjoin(AdsCampaign, AdsNegativeTargeting.campaign_id == AdsCampaign.campaign_id)
    if keyword:
        query = query.where(AdsNegativeTargeting.keyword_text.ilike(f"%{keyword}%"))
    if campaign_id:
        query = query.where(AdsNegativeTargeting.campaign_id == campaign_id)
    if ad_group_id:
        query = query.where(AdsNegativeTargeting.ad_group_id == ad_group_id)
    rows = db.execute(query).all()
    items = [
        {
            "id": neg.negative_id or f"{neg.campaign_id}:{neg.ad_group_id}:{neg.keyword_text}",
            "negative_id": neg.negative_id,
            "keyword": neg.keyword_text,
            "negative_keyword": neg.keyword_text,
            "neg_status": neg.state,
            "status": neg.state,
            "state": neg.state,
            "match_type": neg.match_type,
            "group_name": ad_group.group_name if ad_group else None,
            "ad_group_name": ad_group.group_name if ad_group else None,
            "ad_group_id": neg.ad_group_id,
            "campaign_id": neg.campaign_id,
            "campaign_name": campaign.campaign_name if campaign else None,
        }
        for neg, ad_group, campaign in rows
    ]
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": {}}


def get_logs(db: Session, portfolio_id: str | None, campaign_id: str | None, ad_group_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    query = select(AdsActionLog).order_by(AdsActionLog.created_at.desc())
    if campaign_id:
        query = query.where(AdsActionLog.target_id == campaign_id)
    if ad_group_id:
        query = query.where(AdsActionLog.target_id == ad_group_id)
    rows = db.execute(query).scalars().all()
    items = [
        {
            "id": str(log.id),
            "operation_time": log.created_at.isoformat() if log.created_at else None,
            "portfolio_name": None,
            "ad_type": None,
            "campaign_name": log.target_id if log.target_type == "campaign" else None,
            "group_name": log.target_id if log.target_type == "ad_group" else None,
            "operation_target": log.target_id,
            "operation_type": log.action_key,
            "operation_content": log.request_payload,
            "action_key": log.action_key,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "operator_username": log.operator_username,
            "success": log.success,
            "error_message": log.error_message,
            "response_payload": log.response_payload,
        }
        for log in rows
    ]
    paged, total = paginate(items, page, page_size)
    return {"items": paged, "total_count": total, "summary_row": {}}


def get_campaign_settings(db: Session, campaign_id: str) -> dict[str, Any] | None:
    campaign = db.execute(select(AdsCampaign).where(AdsCampaign.campaign_id == campaign_id)).scalar_one_or_none()
    if campaign is None:
        return None
    return {
        "id": campaign.campaign_id,
        "campaign_id": campaign.campaign_id,
        "campaign_name": campaign.campaign_name,
        "name": campaign.campaign_name,
        "is_active": _active(campaign.state),
        "status": campaign.state,
        "state": campaign.state,
        "portfolio_id": campaign.portfolio_id,
        "ad_type": campaign.ad_type,
        "daily_budget": campaign.daily_budget,
        "budget_currency": campaign.budget_currency,
        "bidding_strategy": campaign.bidding_strategy,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "raw_payload": campaign.raw_payload,
    }


def get_ad_group_settings(db: Session, ad_group_id: str) -> dict[str, Any] | None:
    row = db.execute(
        select(AdsAdGroup, AdsCampaign).outerjoin(AdsCampaign, AdsAdGroup.campaign_id == AdsCampaign.campaign_id).where(AdsAdGroup.ad_group_id == ad_group_id)
    ).one_or_none()
    if row is None:
        return None
    ad_group, campaign = row
    return {
        "id": ad_group.ad_group_id,
        "ad_group_id": ad_group.ad_group_id,
        "ad_group_name": ad_group.group_name,
        "group_name": ad_group.group_name,
        "name": ad_group.group_name,
        "is_active": _active(ad_group.state),
        "status": ad_group.state,
        "state": ad_group.state,
        "default_bid": ad_group.default_bid,
        "campaign_id": ad_group.campaign_id,
        "campaign_name": campaign.campaign_name if campaign else None,
        "raw_payload": ad_group.raw_payload,
    }


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    summary = defaultdict(float)
    for item in items:
        for key in ("impressions", "clicks", "ad_spend", "ad_orders", "ad_sales"):
            summary[key] += safe_float(item.get(key))
    summary["ctr"] = ratio(summary["clicks"], summary["impressions"])
    summary["cpc"] = ratio(summary["ad_spend"], summary["clicks"])
    summary["cvr"] = ratio(summary["ad_orders"], summary["clicks"])
    summary["acos"] = ratio(summary["ad_spend"], summary["ad_sales"])
    return dict(summary)
