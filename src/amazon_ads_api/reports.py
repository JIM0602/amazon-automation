"""Amazon Ads 报告 API 封装（只读）。

使用 Amazon Ads API v3 Reporting 端点：
  POST /reporting/reports
  Content-Type: application/vnd.createasyncreportrequest.v3+json

参考文档：https://advertising.amazon.com/API/docs/en-us/guides/reporting/v3/overview
"""
from __future__ import annotations

import gzip
import io
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, cast

try:
    import importlib
    logger = importlib.import_module("loguru").logger
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


REPORT_STATUS_DONE = "COMPLETED"
REPORT_STATUS_IN_PROGRESS = "PROCESSING"
REPORT_STATUS_PENDING = "PENDING"
REPORT_STATUS_CANCELLED = "CANCELLED"
REPORT_STATUS_FATAL = "FAILED"

# Amazon Ads v3 报告创建需要的特殊 Content-Type
V3_CONTENT_TYPE = "application/vnd.createasyncreportrequest.v3+json"


def _default_date_range() -> tuple[str, str]:
    """返回默认日期范围：最近 14 天（到昨天为止）。

    Amazon Ads 报告数据通常有 1-3 天延迟，使用 T-3 到 T-1 更安全，
    但为覆盖更多数据，默认取最近 14 天。
    """
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=1)    # 昨天
    start = end - timedelta(days=13)   # 14 天前
    return start.isoformat(), end.isoformat()


class ReportsApiError(Exception):
    """报告 API 错误。"""


class ReportsApi:
    """Amazon Ads v3 报告 API 封装。"""

    REPORT_TYPES = {
        "sp_campaigns": "spCampaigns",
        "sp_search_term": "spSearchTerm",
        "sp_targeting": "spTargeting",
    }

    _REPORTS_PATH = "/reporting/reports"

    # 报告轮询配置
    # Amazon Ads v3 报告通常需要 15-30 分钟生成
    _POLL_INTERVAL_SECONDS = 10
    _POLL_MAX_ATTEMPTS = 180  # 最多轮询 30 分钟

    def __init__(self, client: AmazonAdsClient):
        self.client = client

    def request_report(
        self,
        report_type: str,
        metrics: list[str],
        start_date: str = "",
        end_date: str = "",
        time_unit: str = "SUMMARY",
        group_by: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建 v3 异步报告请求。

        Args:
            report_type: 报告类型键名（如 "sp_campaigns"）或直接的 reportTypeId
            metrics:     要包含的列（如 ["campaignId", "impressions", "clicks", "cost"]）
            start_date:  开始日期 YYYY-MM-DD（空则使用默认 14 天范围）
            end_date:    结束日期 YYYY-MM-DD（空则使用默认 14 天范围）
            time_unit:   DAILY 或 SUMMARY（默认 SUMMARY）
            group_by:    分组维度（默认 ["campaign"]）

        Returns:
            API 响应 dict，包含 reportId, status 等
        """
        resolved_type = self.REPORT_TYPES.get(report_type, report_type)

        # 处理空日期：使用默认范围
        if not start_date or not end_date:
            default_start, default_end = _default_date_range()
            start_date = start_date or default_start
            end_date = end_date or default_end
            logger.info(
                "ReportsApi.request_report | 使用默认日期范围 start={} end={}",
                start_date,
                end_date,
            )

        if self.client.dry_run:
            logger.debug(
                "ReportsApi.request_report | dry_run=True type={} start={} end={}",
                resolved_type,
                start_date,
                end_date,
            )
            payload: dict[str, Any] = {
                "reportId": "mock_report_id_001",
                "reportType": resolved_type,
                "status": REPORT_STATUS_DONE,
                "metrics": metrics,
                "startDate": start_date,
                "endDate": end_date,
            }
            return payload

        if group_by is None:
            group_by = ["campaign"]

        body: dict[str, Any] = {
            "name": f"{resolved_type}_{start_date}_{end_date}",
            "startDate": start_date,
            "endDate": end_date,
            "configuration": {
                "adProduct": "SPONSORED_PRODUCTS",
                "groupBy": group_by,
                "columns": metrics,
                "reportTypeId": resolved_type,
                "timeUnit": time_unit,
                "format": "GZIP_JSON",
            },
        }
        logger.info(
            "ReportsApi.request_report | type={} start={} end={} timeUnit={} columns={}",
            resolved_type,
            start_date,
            end_date,
            time_unit,
            metrics,
        )
        return self.client.post(
            self._REPORTS_PATH,
            json_body=body,
            content_type=V3_CONTENT_TYPE,
            accept=V3_CONTENT_TYPE,
        )

    def get_report_status(self, report_id: str) -> dict[str, Any]:
        if self.client.dry_run:
            logger.debug("ReportsApi.get_report_status | dry_run=True report_id={}", report_id)
            payload: dict[str, Any] = {
                "reportId": report_id,
                "status": REPORT_STATUS_DONE,
                "url": f"https://example.com/{report_id}.json",
            }
            return payload

        response = self.client.get(f"{self._REPORTS_PATH}/{report_id}")
        logger.info(
            "ReportsApi.get_report_status | report_id={} status={}",
            report_id,
            response.get("status"),
        )
        return response

    def wait_for_report(self, report_id: str) -> dict[str, Any]:
        """轮询等待报告生成完成。

        Returns:
            包含 status 和 url 的响应 dict

        Raises:
            ReportsApiError: 报告生成失败或超时
        """
        if self.client.dry_run:
            return self.get_report_status(report_id)

        for attempt in range(self._POLL_MAX_ATTEMPTS):
            status_resp = self.get_report_status(report_id)
            status = status_resp.get("status", "")

            if status == REPORT_STATUS_DONE:
                logger.info(
                    "ReportsApi.wait_for_report | report_id={} COMPLETED after {} polls",
                    report_id,
                    attempt + 1,
                )
                return status_resp

            if status in (REPORT_STATUS_FATAL, REPORT_STATUS_CANCELLED):
                reason = status_resp.get("failureReason", "unknown")
                raise ReportsApiError(
                    f"Report {report_id} failed with status={status} reason={reason}"
                )

            if status in (REPORT_STATUS_IN_PROGRESS, REPORT_STATUS_PENDING):
                logger.debug(
                    "ReportsApi.wait_for_report | report_id={} status={} attempt={}/{}",
                    report_id,
                    status,
                    attempt + 1,
                    self._POLL_MAX_ATTEMPTS,
                )
                time.sleep(self._POLL_INTERVAL_SECONDS)
                continue

            # 未知状态，继续轮询
            logger.warning(
                "ReportsApi.wait_for_report | report_id={} 未知状态={} attempt={}",
                report_id,
                status,
                attempt + 1,
            )
            time.sleep(self._POLL_INTERVAL_SECONDS)

        raise ReportsApiError(
            f"Report {report_id} timed out after {self._POLL_MAX_ATTEMPTS} polls"
        )

    def download_report(self, url: str) -> list[dict[str, Any]]:
        """下载报告数据。支持 GZIP_JSON 和普通 JSON 格式。"""
        if self.client.dry_run:
            logger.debug("ReportsApi.download_report | dry_run=True url={}", url)
            return [
                cast(dict[str, Any], {
                    "campaignId": "CAMP001",
                    "campaignName": "Pet Fountain - Exact Match",
                    "cost": 142.30,
                    "purchases7d": 15,
                    "clicks": 142,
                    "impressions": 31622,
                })
            ]

        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                raw_bytes = resp.read()

            # 尝试 gzip 解压（GZIP_JSON 格式）
            try:
                content = gzip.decompress(raw_bytes).decode("utf-8")
                logger.debug("ReportsApi.download_report | GZIP decompressed, size={}", len(content))
            except (gzip.BadGzipFile, OSError):
                # 不是 gzip，当作普通文本
                content = raw_bytes.decode("utf-8")
                logger.debug("ReportsApi.download_report | plain text, size={}", len(content))

            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    for key in ("report", "data", "items"):
                        value = parsed.get(key)
                        if isinstance(value, list):
                            return value
                    return [parsed]
            except Exception:
                pass

            # 降级：尝试 CSV 解析
            lines = [line for line in content.splitlines() if line.strip()]
            if not lines:
                return []
            header = [part.strip() for part in lines[0].split(",")]
            rows: list[dict[str, Any]] = []
            for line in lines[1:]:
                values = [part.strip() for part in line.split(",")]
                rows.append({header[i]: values[i] if i < len(values) else "" for i in range(len(header))})
            return rows
        except Exception as exc:
            logger.error("ReportsApi.download_report failed | url={} error={}", url, exc)
            raise ReportsApiError(f"Download failed: {exc}") from exc
