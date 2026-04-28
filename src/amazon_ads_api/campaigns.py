"""Amazon Ads Sponsored Products campaigns API（只读）。"""
from __future__ import annotations

from typing import Any, Optional, cast

try:
    logger = __import__("loguru").logger
except Exception:  # pragma: no cover
    import logging as _logging

    class logger:  # type: ignore[no-redef]
        @staticmethod
        def info(msg, *args, **kwargs):
            _logging.info(msg.format(*args) if args else msg)

        @staticmethod
        def warning(msg, *args, **kwargs):
            _logging.warning(msg.format(*args) if args else msg)

        @staticmethod
        def error(msg, *args, **kwargs):
            _logging.error(msg.format(*args) if args else msg)

        @staticmethod
        def debug(msg, *args, **kwargs):
            _logging.debug(msg.format(*args) if args else msg)

from src.amazon_ads_api.client import AmazonAdsClient
from src.amazon_ads_api.reports import ReportsApi, REPORT_STATUS_DONE, ReportsApiError


class CampaignsApiError(Exception):
    """Campaigns API 错误。"""


class CampaignsApi:
    """Sponsored Products campaigns API。"""

    _CAMPAIGNS_PATH = "/sp/campaigns"
    _CAMPAIGNS_LIST_PATH = "/sp/campaigns/list"
    _CAMPAIGNS_V3_CONTENT_TYPE = "application/vnd.spcampaign.v3+json"

    def __init__(self, client: AmazonAdsClient):
        self.client = client
        self.reports_api = ReportsApi(client)

    def list_campaigns(self, state_filter: Optional[str] = None) -> list[dict[str, Any]]:
        if self.client.dry_run:
            logger.debug("CampaignsApi.list_campaigns | dry_run=True state_filter={}", state_filter)
            campaigns: list[dict[str, Any]] = [
                {
                    "campaignId": "CAMP001",
                    "campaignName": "Pet Fountain - Exact Match",
                    "state": "enabled",
                },
                {
                    "campaignId": "CAMP002",
                    "campaignName": "Pet Fountain - Broad Match",
                    "state": "enabled",
                },
            ]
            if state_filter:
                campaigns = [c for c in campaigns if c.get("state") == state_filter]
            return campaigns

        body: dict[str, Any] = {}
        if state_filter:
            body["stateFilter"] = {"include": [state_filter.upper()]}
        response = self.client.post(
            self._CAMPAIGNS_LIST_PATH,
            json_body=body,
            content_type=self._CAMPAIGNS_V3_CONTENT_TYPE,
            accept=self._CAMPAIGNS_V3_CONTENT_TYPE,
        )
        campaigns = response.get("campaigns", response.get("items", []))
        return cast(list[dict[str, Any]], campaigns)

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        if self.client.dry_run:
            logger.debug("CampaignsApi.get_campaign | dry_run=True campaign_id={}", campaign_id)
            return {
                "campaignId": campaign_id,
                "campaignName": f"Mock Campaign {campaign_id}",
                "state": "enabled",
            }

        return self.client.get(f"{self._CAMPAIGNS_PATH}/{campaign_id}")

    def get_campaign_metrics(
        self,
        campaign_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.client.dry_run:
            logger.debug(
                "CampaignsApi.get_campaign_metrics | dry_run=True campaign_ids={} start={} end={}",
                campaign_ids,
                start_date,
                end_date,
            )
            metrics: list[dict[str, Any]] = [
                {
                    "campaign_id": "CAMP001",
                    "campaign_name": "Pet Fountain - Exact Match",
                    "acos": 28.5,
                    "roas": 3.51,
                    "ctr": 0.45,
                    "cvr": 12.8,
                    "spend": 142.30,
                    "sales": 499.30,
                    "impressions": 31622,
                    "clicks": 142,
                    "date": "2026-04-01",
                },
                {
                    "campaign_id": "CAMP002",
                    "campaign_name": "Pet Fountain - Broad Match",
                    "acos": 52.3,
                    "roas": 1.91,
                    "ctr": 0.22,
                    "cvr": 8.1,
                    "spend": 287.60,
                    "sales": 549.50,
                    "impressions": 130727,
                    "clicks": 288,
                    "date": "2026-04-01",
                },
            ]
            if campaign_ids:
                metrics = [item for item in metrics if item["campaign_id"] in campaign_ids]
            return metrics

        report = self.reports_api.request_report(
            report_type="sp_campaigns",
            metrics=[
                "campaignId",
                "campaignName",
                "impressions",
                "clicks",
                "cost",
                "purchases7d",
                "sales7d",
            ],
            start_date=start_date or "",
            end_date=end_date or "",
            time_unit="SUMMARY",
            group_by=["campaign"],
        )
        report_id = str(report.get("reportId") or "")
        if not report_id:
            raise CampaignsApiError("Missing reportId from report request")

        # 轮询等待报告完成
        status = self.reports_api.wait_for_report(report_id)

        download_url = (
            status.get("url")
            or status.get("location")
            or status.get("downloadUrl")
        )
        if not download_url:
            raise CampaignsApiError("Missing report download URL")

        rows = self.reports_api.download_report(str(download_url))
        normalized: list[dict[str, Any]] = []
        campaign_filter = set(campaign_ids or [])

        for row in rows:
            campaign_id = str(row.get("campaignId") or row.get("campaign_id") or "")
            if campaign_filter and campaign_id not in campaign_filter:
                continue

            spend = float(cast(Any, row.get("cost") or row.get("spend") or 0.0))
            # v3 API 返回 sales7d, sales14d 等归因窗口字段
            sales = float(cast(Any, row.get("sales7d") or row.get("sales14d") or row.get("sales") or 0.0))
            clicks = int(float(cast(Any, row.get("clicks") or 0)))
            impressions = int(float(cast(Any, row.get("impressions") or 0)))
            # v3 API 返回 purchases7d, purchases14d 等
            orders = float(cast(Any, row.get("purchases7d") or row.get("purchases14d") or row.get("orders") or row.get("purchases") or 0.0))
            ctr = round((clicks / impressions * 100.0) if impressions else 0.0, 2)
            cvr = round((orders / clicks * 100.0) if clicks else 0.0, 2)
            acos = round((spend / sales * 100.0) if sales else 0.0, 2)
            roas = round((sales / spend) if spend else 0.0, 2)

            normalized.append({
                "campaign_id": campaign_id,
                "campaign_name": row.get("campaignName") or row.get("campaign_name") or f"Campaign {campaign_id}",
                "acos": acos,
                "roas": roas,
                "ctr": ctr,
                "cvr": cvr,
                "spend": round(spend, 2),
                "sales": round(sales, 2),
                "impressions": impressions,
                "clicks": clicks,
                "date": end_date or start_date or "",
            })

        return normalized
