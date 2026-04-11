"""SP-API Brand Analytics 数据接入（只读）。

提供 Brand Analytics Search Terms 报告的请求、解析能力。
需要品牌注册（Brand Registry）；未注册时优雅降级。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.amazon_sp_api.client import SpApiClient
from src.amazon_sp_api.reports import ReportsApi, ReportsApiError

logger = logging.getLogger(__name__)


@dataclass
class SearchTermRecord:
    """Brand Analytics 搜索词数据记录。"""

    search_term: str
    search_frequency_rank: int
    clicked_asin_1: str = ""
    click_share_1: float = 0.0
    conversion_share_1: float = 0.0
    clicked_asin_2: str = ""
    click_share_2: float = 0.0
    conversion_share_2: float = 0.0
    clicked_asin_3: str = ""
    click_share_3: float = 0.0
    conversion_share_3: float = 0.0


class BrandAnalyticsError(Exception):
    """Brand Analytics 错误。"""


class BrandAnalyticsApi:
    """Brand Analytics Search Terms 数据接口。

    需要店铺已完成品牌注册。未注册时 request 将返回错误，
    调用方应通过 is_available() 提前检查。
    """

    def __init__(self, client: SpApiClient) -> None:
        self.client = client
        self._reports = ReportsApi(client)

    def is_available(self) -> bool:
        """检查 Brand Analytics 是否可用（品牌注册状态）。

        dry_run 模式下始终返回 True。
        """
        if self.client.dry_run:
            return True
        # In production, attempt a lightweight check.
        # For now, return True and let request_search_terms_report
        # handle errors gracefully.
        return True

    def request_search_terms_report(
        self,
        start_date: str,
        end_date: str,
        marketplace_ids: list[str] | None = None,
    ) -> str:
        """请求 Brand Analytics Search Terms 报告。

        Args:
            start_date: ISO 8601 格式起始日期
            end_date: ISO 8601 格式结束日期
            marketplace_ids: 目标市场 ID 列表

        Returns:
            report_id: 报告 ID

        Raises:
            BrandAnalyticsError: 请求失败（含品牌未注册情况）
        """
        try:
            result: dict[str, Any] = self._reports.request_report(
                report_type="brand_analytics_search_terms",
                start_date=start_date,
                end_date=end_date,
                marketplace_ids=marketplace_ids,
            )
            report_id: str = result.get("reportId", "")
            logger.info("Brand Analytics report requested: %s", report_id)
            return report_id
        except ReportsApiError as exc:
            logger.warning("Brand Analytics request failed (品牌未注册?): %s", exc)
            raise BrandAnalyticsError(
                f"Brand Analytics 报告请求失败: {exc}"
            ) from exc

    def get_search_terms_data(self, report_id: str) -> list[SearchTermRecord]:
        """获取并解析 Search Terms 报告数据。

        Args:
            report_id: 通过 request_search_terms_report 返回的报告 ID

        Returns:
            解析后的搜索词记录列表
        """
        try:
            status = self._reports.get_report_status(report_id)
            doc_id: str = status.get("reportDocumentId", "")
            if not doc_id:
                raise BrandAnalyticsError(
                    f"Report not ready or no document: {report_id}"
                )

            raw_content = self._reports.download_report(doc_id)
            return self.parse_search_terms(raw_content)
        except ReportsApiError as exc:
            raise BrandAnalyticsError(f"获取报告数据失败: {exc}") from exc

    @staticmethod
    def parse_search_terms(raw_data: str) -> list[SearchTermRecord]:
        """解析 Search Terms 报告原始数据。

        Args:
            raw_data: CSV/TSV 格式的原始报告内容

        Returns:
            解析后的 SearchTermRecord 列表
        """
        records: list[SearchTermRecord] = []
        lines = raw_data.strip().split("\n")
        if len(lines) < 2:
            return records

        # Skip header line
        for line in lines[1:]:
            fields = line.split("\t") if "\t" in line else line.split(",")
            if len(fields) < 2:
                continue
            try:
                record = SearchTermRecord(
                    search_term=fields[0].strip().strip('"'),
                    search_frequency_rank=int(fields[1].strip().strip('"')),
                    clicked_asin_1=(
                        fields[2].strip().strip('"') if len(fields) > 2 else ""
                    ),
                    click_share_1=(
                        float(fields[3].strip().strip('"').rstrip("%"))
                        if len(fields) > 3
                        else 0.0
                    ),
                    conversion_share_1=(
                        float(fields[4].strip().strip('"').rstrip("%"))
                        if len(fields) > 4
                        else 0.0
                    ),
                    clicked_asin_2=(
                        fields[5].strip().strip('"') if len(fields) > 5 else ""
                    ),
                    click_share_2=(
                        float(fields[6].strip().strip('"').rstrip("%"))
                        if len(fields) > 6
                        else 0.0
                    ),
                    conversion_share_2=(
                        float(fields[7].strip().strip('"').rstrip("%"))
                        if len(fields) > 7
                        else 0.0
                    ),
                    clicked_asin_3=(
                        fields[8].strip().strip('"') if len(fields) > 8 else ""
                    ),
                    click_share_3=(
                        float(fields[9].strip().strip('"').rstrip("%"))
                        if len(fields) > 9
                        else 0.0
                    ),
                    conversion_share_3=(
                        float(fields[10].strip().strip('"').rstrip("%"))
                        if len(fields) > 10
                        else 0.0
                    ),
                )
                records.append(record)
            except (ValueError, IndexError) as exc:
                logger.debug("Skipping malformed row: %s (%s)", line[:80], exc)
                continue

        logger.info("Parsed %d search term records", len(records))
        return records
