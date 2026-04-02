"""Amazon SP-API 报告 API 封装（只读）。

支持请求报告、查询状态、下载报告内容。
dry_run=True 时返回 mock 数据，不进行真实网络请求。
"""
from __future__ import annotations

from typing import Optional

try:
    from loguru import logger
except ImportError:  # pragma: no cover
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

from src.amazon_sp_api.client import SpApiClient


# 报告状态常量
REPORT_STATUS_DONE = "DONE"
REPORT_STATUS_IN_PROGRESS = "IN_PROGRESS"
REPORT_STATUS_CANCELLED = "CANCELLED"
REPORT_STATUS_FATAL = "FATAL"


class ReportsApiError(Exception):
    """报告 API 错误。"""


class ReportsApi:
    """SP-API 报告 API 封装（只读）。

    支持的操作：
      - 请求生成报告（request_report）
      - 查询报告状态（get_report_status）
      - 下载报告内容（download_report）

    所有操作均为只读（不创建/修改任何数据）。
    dry_run=True 时返回 mock 数据。

    Args:
        client: SpApiClient 实例
    """

    REPORT_TYPES = {
        "sales_and_traffic": "GET_SALES_AND_TRAFFIC_REPORT",
        "advertising_performance": "GET_ADVERTISED_PRODUCT_REPORT",
        "inventory": "GET_MERCHANT_LISTINGS_ALL_DATA",
        "order_report": "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL",
    }

    _REPORTS_PATH = "/reports/2021-06-30/reports"
    _REPORT_DOCUMENTS_PATH = "/reports/2021-06-30/documents"

    def __init__(self, client: SpApiClient):
        self.client = client

    def request_report(
        self,
        report_type: str,
        start_date: str,
        end_date: str,
        marketplace_ids: Optional[list] = None,
    ) -> dict:
        """请求生成报告，返回 reportId。

        dry_run=True 时返回 mock reportId，不进行真实请求。

        Args:
            report_type:     报告类型（REPORT_TYPES 中的 key 或原始类型字符串）
            start_date:      报告数据起始日期（ISO 8601，如 "2026-01-01T00:00:00Z"）
            end_date:        报告数据结束日期（ISO 8601）
            marketplace_ids: 目标市场 ID 列表（默认使用 client.marketplace_id）

        Returns:
            dict with keys:
                reportId (str):    报告 ID
                reportType (str):  报告类型
                status (str):      报告状态
        """
        # 解析报告类型（支持别名）
        resolved_type = self.REPORT_TYPES.get(report_type, report_type)
        mkt_ids = marketplace_ids or [self.client.marketplace_id]

        if self.client.dry_run:
            logger.debug(
                "ReportsApi.request_report | dry_run=True type={} start={} end={}",
                resolved_type, start_date, end_date,
            )
            return {
                "reportId": "mock_report_id_001",
                "reportType": resolved_type,
                "status": REPORT_STATUS_DONE,
                "dataStartTime": start_date,
                "dataEndTime": end_date,
                "marketplaceIds": mkt_ids,
            }

        # 真实实现：通过 POST 请求创建报告任务
        # 注：报告请求本身使用 POST，但不修改任何卖家数据，属于"读取"操作
        logger.info(
            "ReportsApi.request_report | type={} start={} end={}",
            resolved_type, start_date, end_date,
        )
        response = self.client.get(
            self._REPORTS_PATH,
            params={
                "reportType": resolved_type,
                "dataStartTime": start_date,
                "dataEndTime": end_date,
                "marketplaceIds": ",".join(mkt_ids),
            },
        )
        return response

    def get_report_status(self, report_id: str) -> dict:
        """获取报告生成状态。

        Args:
            report_id: 通过 request_report 返回的报告 ID

        Returns:
            dict with keys:
                reportId (str):          报告 ID
                status (str):            状态（DONE/IN_PROGRESS/CANCELLED/FATAL）
                reportDocumentId (str):  报告文档 ID（status=DONE 时存在）
        """
        if self.client.dry_run:
            logger.debug("ReportsApi.get_report_status | dry_run=True report_id={}", report_id)
            return {
                "reportId": report_id,
                "status": REPORT_STATUS_DONE,
                "reportDocumentId": f"mock_doc_id_{report_id}",
                "processingStatus": REPORT_STATUS_DONE,
            }

        response = self.client.get(f"{self._REPORTS_PATH}/{report_id}")
        logger.info(
            "ReportsApi.get_report_status | report_id={} status={}",
            report_id,
            response.get("status"),
        )
        return response

    def download_report(self, report_document_id: str) -> str:
        """下载报告内容，返回原始文本（CSV/TSV 格式）。

        Args:
            report_document_id: 通过 get_report_status 返回的文档 ID

        Returns:
            str: 报告原始文本内容
        """
        if self.client.dry_run:
            logger.debug(
                "ReportsApi.download_report | dry_run=True doc_id={}",
                report_document_id,
            )
            return "date,sales,units\n2026-04-01,1500.00,50\n"

        # 获取报告文档信息（含下载 URL）
        doc_info = self.client.get(
            f"{self._REPORT_DOCUMENTS_PATH}/{report_document_id}"
        )
        download_url = doc_info.get("url", "")

        if not download_url:
            raise ReportsApiError(
                f"No download URL in report document: {report_document_id}"
            )

        try:
            import urllib.request
            with urllib.request.urlopen(download_url, timeout=60) as resp:
                content = resp.read().decode("utf-8")
            logger.info(
                "ReportsApi.download_report | doc_id={} size={}bytes",
                report_document_id,
                len(content),
            )
            return content
        except Exception as exc:
            logger.error(
                "ReportsApi.download_report failed | doc_id={} error={}",
                report_document_id, exc,
            )
            raise ReportsApiError(f"Download failed: {exc}") from exc

    def list_reports(
        self,
        report_types: Optional[list] = None,
        processing_statuses: Optional[list] = None,
        max_results: int = 10,
    ) -> list:
        """列出已请求的报告。

        Args:
            report_types:        过滤的报告类型列表
            processing_statuses: 过滤的处理状态列表
            max_results:         最大返回数量

        Returns:
            list[dict]: 报告信息列表
        """
        if self.client.dry_run:
            logger.debug("ReportsApi.list_reports | dry_run=True")
            return [
                {
                    "reportId": "mock_report_id_001",
                    "reportType": "GET_SALES_AND_TRAFFIC_REPORT",
                    "status": REPORT_STATUS_DONE,
                },
                {
                    "reportId": "mock_report_id_002",
                    "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
                    "status": REPORT_STATUS_IN_PROGRESS,
                },
            ]

        params = {"pageSize": max_results}
        if report_types:
            params["reportTypes"] = ",".join(report_types)
        if processing_statuses:
            params["processingStatuses"] = ",".join(processing_statuses)

        response = self.client.get(self._REPORTS_PATH, params=params)
        return response.get("reports", [])
