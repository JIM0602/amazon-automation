"""Minimal Amazon Ads sync chain for phase 1."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.amazon_ads_api import AmazonAdsClient, CampaignsApi
from src.amazon_ads_api.reports import ReportsApi
from src.config import settings
from src.db.models import AdsAdGroup, AdsCampaign, AdsMetricsDaily, AdsNegativeTargeting, AdsSearchTerm, AdsTargeting, SyncJob
from src.services.phase1_common import first_value, safe_float, safe_int

MAX_V3_LIST_PAGES = 500


class AdsSyncIncompleteError(RuntimeError):
    """Raised when a list endpoint may have returned incomplete data."""

    def __init__(self, message: str, payload: dict[str, Any]):
        super().__init__(message)
        self.payload = payload


def _ads_client() -> AmazonAdsClient:
    has_credentials = all([
        settings.AMAZON_ADS_CLIENT_ID,
        settings.AMAZON_ADS_CLIENT_SECRET,
        settings.AMAZON_ADS_REFRESH_TOKEN,
        settings.AMAZON_ADS_PROFILE_ID,
    ])
    return AmazonAdsClient(
        client_id=settings.AMAZON_ADS_CLIENT_ID or "",
        client_secret=settings.AMAZON_ADS_CLIENT_SECRET or "",
        refresh_token=settings.AMAZON_ADS_REFRESH_TOKEN or "",
        profile_id=settings.AMAZON_ADS_PROFILE_ID or "",
        region=settings.AMAZON_ADS_REGION,
        dry_run=settings.DRY_RUN or not has_credentials,
    )


def sync_ads(db: Session, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    job = SyncJob(
        job_name="amazon_ads_minimal_sync",
        job_type="ads",
        status="running",
        records_count=0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    records = 0
    list_diagnostics: list[dict[str, Any]] = []
    try:
        client = _ads_client()
        campaigns_api = CampaignsApi(client)
        now = datetime.now(timezone.utc)
        campaigns = campaigns_api.list_campaigns()
        for payload in campaigns:
            _upsert_campaign(db, payload, now)
            records += 1

        for payload in _list_v3_items(client, "/sp/adGroups/list", "adGroups", "application/vnd.spadGroup.v3+json", list_diagnostics):
            _upsert_ad_group(db, payload, now)
            records += 1

        for payload in _list_v3_items(client, "/sp/targets/list", "targetingClauses", "application/vnd.sptargetingClause.v3+json", list_diagnostics):
            _upsert_targeting(db, payload, now)
            records += 1

        for payload in _list_v3_items(client, "/sp/negativeTargets/list", "negativeTargetingClauses", "application/vnd.spnegativeTargetingClause.v3+json", list_diagnostics):
            _upsert_negative(db, payload, now)
            records += 1

        if not start_date or not end_date:
            end = (now.date() - timedelta(days=1)).isoformat()
            start = (now.date() - timedelta(days=14)).isoformat()
        else:
            start, end = start_date, end_date
        metrics = campaigns_api.get_campaign_metrics(start_date=start, end_date=end)
        for payload in metrics:
            _upsert_campaign_metric(db, payload, end)
            records += 1

        for payload in _search_term_report(client, start, end):
            _upsert_search_term(db, payload, end)
            records += 1

        job.status = "success"
        job.records_count = records
        job.finished_at = datetime.now(timezone.utc)
        job.extra_payload = {"dry_run": client.dry_run, "start_date": start, "end_date": end, "list_diagnostics": list_diagnostics}
        return {"status": "success", "records_count": records, "dry_run": client.dry_run}
    except AdsSyncIncompleteError as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.records_count = records
        job.finished_at = datetime.now(timezone.utc)
        job.extra_payload = {"reason": "pagination_incomplete", **exc.payload, "records_count_before_failure": records}
        db.commit()
        raise
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.records_count = records
        job.finished_at = datetime.now(timezone.utc)
        raise


def _list_v3_items(
    client: AmazonAdsClient,
    path: str,
    key: str,
    content_type: str,
    diagnostics: list[dict[str, Any]],
    max_pages: int = MAX_V3_LIST_PAGES,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_token: str | None = None
    page_count = 0
    while True:
        if page_count >= max_pages:
            payload = {
                "path": path,
                "key": key,
                "pages_read": page_count,
                "items_read": len(items),
                "max_pages": max_pages,
                "has_next_token": bool(next_token),
            }
            diagnostics.append({**payload, "complete": False})
            raise AdsSyncIncompleteError(f"{path} exceeded pagination safety limit after {page_count} pages", payload)

        body = {"nextToken": next_token} if next_token else {}
        response = client.post(path, json_body=body, content_type=content_type, accept=content_type)
        page_count += 1
        value = response.get(key) or response.get("items") or []
        if isinstance(value, list):
            items.extend(value)
        next_token = response.get("nextToken")
        if not next_token:
            break
    diagnostics.append({"path": path, "key": key, "pages_read": page_count, "items_read": len(items), "complete": True})
    return items


def _nested_budget(payload: dict[str, Any]) -> Any:
    budget = payload.get("budget")
    if isinstance(budget, dict):
        return budget.get("budget") or budget.get("amount")
    return budget


def _expression_text(payload: dict[str, Any]) -> str | None:
    value = first_value(payload, ["keywordText", "keyword"])
    if value:
        return str(value)
    expression = payload.get("expression")
    if isinstance(expression, list):
        parts = []
        for item in expression:
            if isinstance(item, dict):
                parts.append(str(item.get("value") or item.get("type") or ""))
        return " ".join(part for part in parts if part) or None
    return str(expression) if expression else None


def _expression_match_type(payload: dict[str, Any]) -> str | None:
    value = first_value(payload, ["matchType", "match_type"])
    if value:
        return str(value)
    expression = payload.get("expression")
    if isinstance(expression, list) and expression and isinstance(expression[0], dict):
        return str(expression[0].get("type") or "") or None
    return None


def _upsert_campaign(db: Session, payload: dict[str, Any], synced_at: datetime) -> AdsCampaign:
    campaign_id = str(first_value(payload, ["campaignId", "campaign_id", "campaignIdString"], ""))
    if not campaign_id:
        raise ValueError(f"campaign payload missing id: {payload}")
    row = db.execute(select(AdsCampaign).where(AdsCampaign.campaign_id == campaign_id)).scalar_one_or_none()
    if row is None:
        row = AdsCampaign(campaign_id=campaign_id)
        db.add(row)
    row.campaign_name = str(first_value(payload, ["campaignName", "name", "campaign_name"], campaign_id))
    row.portfolio_id = first_value(payload, ["portfolioId", "portfolio_id"])
    row.ad_type = str(first_value(payload, ["adType", "ad_type"], "SP"))
    row.state = str(first_value(payload, ["state", "status"], "enabled")).lower()
    row.serving_status = first_value(payload, ["servingStatus", "serving_status"])
    budget = first_value(payload, ["dailyBudget", "budgetAmount"]) or _nested_budget(payload)
    row.daily_budget = safe_float(budget) if budget is not None else row.daily_budget
    row.budget_currency = str(first_value(payload, ["budgetCurrency", "currency"], row.budget_currency or "USD"))
    dynamic_bidding = payload.get("dynamicBidding")
    row.bidding_strategy = first_value(payload, ["biddingStrategy", "strategy"]) or (
        dynamic_bidding.get("strategy") if isinstance(dynamic_bidding, dict) else None
    )
    row.last_synced_at = synced_at
    row.raw_payload = payload
    return row


def _upsert_ad_group(db: Session, payload: dict[str, Any], synced_at: datetime) -> AdsAdGroup:
    ad_group_id = str(first_value(payload, ["adGroupId", "ad_group_id"], ""))
    if not ad_group_id:
        raise ValueError(f"ad group payload missing id: {payload}")
    row = db.execute(select(AdsAdGroup).where(AdsAdGroup.ad_group_id == ad_group_id)).scalar_one_or_none()
    if row is None:
        row = AdsAdGroup(ad_group_id=ad_group_id)
        db.add(row)
    row.campaign_id = str(first_value(payload, ["campaignId", "campaign_id"], ""))
    row.group_name = str(first_value(payload, ["adGroupName", "name", "group_name"], ad_group_id))
    row.state = str(first_value(payload, ["state", "status"], "enabled")).lower()
    bid = first_value(payload, ["defaultBid", "bid"])
    row.default_bid = safe_float(bid) if bid is not None else row.default_bid
    row.last_synced_at = synced_at
    row.raw_payload = payload
    return row


def _upsert_targeting(db: Session, payload: dict[str, Any], synced_at: datetime) -> AdsTargeting:
    targeting_id = str(first_value(payload, ["targetId", "keywordId", "targeting_id"], ""))
    if not targeting_id:
        raise ValueError(f"targeting payload missing id: {payload}")
    row = db.execute(select(AdsTargeting).where(AdsTargeting.targeting_id == targeting_id)).scalar_one_or_none()
    if row is None:
        row = AdsTargeting(targeting_id=targeting_id)
        db.add(row)
    row.campaign_id = str(first_value(payload, ["campaignId", "campaign_id"], ""))
    row.ad_group_id = first_value(payload, ["adGroupId", "ad_group_id"])
    row.keyword_text = _expression_text(payload)
    row.match_type = _expression_match_type(payload)
    row.state = str(first_value(payload, ["state", "status"], "enabled")).lower()
    bid = first_value(payload, ["bid"])
    row.bid = safe_float(bid) if bid is not None else row.bid
    row.last_synced_at = synced_at
    row.raw_payload = payload
    return row


def _upsert_negative(db: Session, payload: dict[str, Any], synced_at: datetime) -> AdsNegativeTargeting:
    negative_id = first_value(payload, ["negativeTargetId", "targetId", "keywordId", "negative_id"])
    campaign_id = str(first_value(payload, ["campaignId", "campaign_id"], ""))
    keyword = str(_expression_text(payload) or "")
    lookup_id = str(negative_id or f"{campaign_id}:{first_value(payload, ['adGroupId', 'ad_group_id'], '')}:{keyword}")
    row = db.execute(select(AdsNegativeTargeting).where(AdsNegativeTargeting.negative_id == lookup_id)).scalar_one_or_none()
    if row is None:
        row = AdsNegativeTargeting(negative_id=lookup_id)
        db.add(row)
    row.campaign_id = campaign_id
    row.ad_group_id = first_value(payload, ["adGroupId", "ad_group_id"])
    row.keyword_text = keyword
    row.match_type = _expression_match_type(payload)
    row.state = str(first_value(payload, ["state", "status"], "enabled")).lower()
    row.last_synced_at = synced_at
    row.raw_payload = payload
    return row


def _search_term_report(client: AmazonAdsClient, start: str, end: str) -> list[dict[str, Any]]:
    if client.dry_run:
        return []
    reports_api = ReportsApi(client)
    report = reports_api.request_report(
        report_type="sp_search_term",
        metrics=[
            "date",
            "campaignId",
            "adGroupId",
            "keyword",
            "keywordId",
            "searchTerm",
            "matchType",
            "impressions",
            "clicks",
            "cost",
            "purchases7d",
            "sales7d",
        ],
        start_date=start,
        end_date=end,
        time_unit="DAILY",
        group_by=["searchTerm"],
    )
    report_id = str(report.get("reportId") or "")
    if not report_id:
        return []
    status = reports_api.wait_for_report(report_id)
    download_url = status.get("url") or status.get("location") or status.get("downloadUrl")
    if not download_url:
        return []
    return reports_api.download_report(str(download_url))


def _upsert_search_term(db: Session, payload: dict[str, Any], fallback_date: str) -> AdsSearchTerm:
    campaign_id = str(first_value(payload, ["campaignId", "campaign_id"], ""))
    ad_group_id = first_value(payload, ["adGroupId", "ad_group_id"])
    search_term = str(first_value(payload, ["query", "searchTerm", "search_term"], ""))
    if not campaign_id or not search_term:
        raise ValueError(f"search term payload missing campaign/search term: {payload}")
    metric_date = date.fromisoformat(str(first_value(payload, ["date"], fallback_date))[:10])
    targeting_keyword = first_value(payload, ["keyword", "targetingKeyword", "targeting_keyword"])
    row = db.execute(
        select(AdsSearchTerm).where(
            AdsSearchTerm.date == metric_date,
            AdsSearchTerm.campaign_id == campaign_id,
            AdsSearchTerm.ad_group_id == (str(ad_group_id) if ad_group_id is not None else None),
            AdsSearchTerm.search_term == search_term,
        )
    ).scalar_one_or_none()
    if row is None:
        row = AdsSearchTerm(
            date=metric_date,
            campaign_id=campaign_id,
            ad_group_id=str(ad_group_id) if ad_group_id is not None else None,
            search_term=search_term,
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)
    row.targeting_keyword = str(targeting_keyword) if targeting_keyword is not None else None
    row.match_type = first_value(payload, ["matchType", "match_type"])
    clicks = safe_int(first_value(payload, ["clicks"]))
    impressions = safe_int(first_value(payload, ["impressions"]))
    cost = safe_float(first_value(payload, ["cost", "spend"]))
    orders = safe_int(first_value(payload, ["purchases7d", "purchases14d", "orders", "purchases"]))
    sales = safe_float(first_value(payload, ["sales7d", "sales14d", "sales", "ad_sales"]))
    row.impressions = impressions
    row.clicks = clicks
    row.cost = cost
    row.ad_orders = orders
    row.ad_sales = sales
    row.acos = round(cost / sales, 6) if sales else 0.0
    row.cvr = round(orders / clicks, 6) if clicks else 0.0
    return row


def _upsert_campaign_metric(db: Session, payload: dict[str, Any], fallback_date: str) -> AdsMetricsDaily:
    campaign_id = str(first_value(payload, ["campaign_id", "campaignId"], ""))
    metric_date = date.fromisoformat(str(first_value(payload, ["date"], fallback_date))[:10])
    row = db.execute(
        select(AdsMetricsDaily).where(
            AdsMetricsDaily.campaign_id == campaign_id,
            AdsMetricsDaily.date == metric_date,
            AdsMetricsDaily.ad_group_id.is_(None),
            AdsMetricsDaily.sku.is_(None),
        )
    ).scalar_one_or_none()
    if row is None:
        row = AdsMetricsDaily(campaign_id=campaign_id, date=metric_date, created_at=datetime.now(timezone.utc))
        db.add(row)
    spend = safe_float(first_value(payload, ["spend", "cost"]))
    sales = safe_float(first_value(payload, ["sales", "ad_sales", "sales7d", "sales14d"]))
    clicks = safe_int(first_value(payload, ["clicks"]))
    impressions = safe_int(first_value(payload, ["impressions"]))
    orders = safe_int(first_value(payload, ["orders", "purchases", "purchases7d", "purchases14d"]))
    row.impressions = impressions
    row.clicks = clicks
    row.cost = spend
    row.ad_sales = sales
    row.ad_orders = orders
    row.ad_units = orders
    row.ctr = round(clicks / impressions, 6) if impressions else 0.0
    row.cpc = round(spend / clicks, 6) if clicks else 0.0
    row.acos = round(spend / sales, 6) if sales else 0.0
    row.cvr = round(orders / clicks, 6) if clicks else 0.0
    return row
