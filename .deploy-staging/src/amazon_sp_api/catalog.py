"""Amazon SP-API 商品目录 API（只读）。

提供商品信息查询和目录搜索功能。
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


class CatalogApiError(Exception):
    """目录 API 错误。"""


class CatalogApi:
    """SP-API 商品目录 API（只读）。

    支持的操作：
      - 获取商品详情（get_catalog_item）
      - 搜索商品目录（search_catalog_items）

    所有操作均为只读 GET 请求。
    dry_run=True 时返回 mock 数据。

    Args:
        client: SpApiClient 实例
    """

    _CATALOG_PATH = "/catalog/2022-04-01/items"

    def __init__(self, client: SpApiClient):
        self.client = client

    def get_catalog_item(
        self,
        asin: str,
        marketplace_id: Optional[str] = None,
        included_data: Optional[list] = None,
    ) -> dict:
        """获取商品详情。

        dry_run=True 时返回基于 ASIN 的 mock 数据。

        Args:
            asin:          Amazon 商品 ASIN
            marketplace_id: 目标市场 ID（默认使用 client.marketplace_id）
            included_data:  需要包含的数据集合（如 ["summaries", "prices"]）

        Returns:
            dict with keys:
                asin (str):    商品 ASIN
                title (str):   商品标题
                brand (str):   品牌
                price (float): 价格
        """
        mkt_id = marketplace_id or self.client.marketplace_id

        if self.client.dry_run:
            logger.debug("CatalogApi.get_catalog_item | dry_run=True asin={}", asin)
            return {
                "asin": asin,
                "title": f"Mock Product for {asin}",
                "brand": "MockBrand",
                "price": 24.99,
                "marketplaceId": mkt_id,
                "summaries": [
                    {
                        "marketplaceId": mkt_id,
                        "asin": asin,
                        "itemName": f"Mock Product for {asin}",
                        "brandName": "MockBrand",
                    }
                ],
            }

        params = {"marketplaceIds": mkt_id}
        if included_data:
            params["includedData"] = ",".join(included_data)

        response = self.client.get(f"{self._CATALOG_PATH}/{asin}", params=params)
        logger.info("CatalogApi.get_catalog_item | asin={}", asin)
        return response

    def search_catalog_items(
        self,
        keywords: str,
        marketplace_id: Optional[str] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> list:
        """搜索商品目录。

        dry_run=True 时返回 mock 搜索结果列表。

        Args:
            keywords:      搜索关键词
            marketplace_id: 目标市场 ID（默认使用 client.marketplace_id）
            page_size:     每页结果数量（最大 20）
            page_token:    分页 token

        Returns:
            list[dict]: 商品信息列表
        """
        mkt_id = marketplace_id or self.client.marketplace_id

        if self.client.dry_run:
            logger.debug(
                "CatalogApi.search_catalog_items | dry_run=True keywords={}",
                keywords,
            )
            return [
                {
                    "asin": "B0MOCK001",
                    "title": "Mock Search Result",
                    "brand": "MockBrand",
                    "price": 19.99,
                }
            ]

        params = {
            "keywords": keywords,
            "marketplaceIds": mkt_id,
            "pageSize": min(page_size, 20),
        }
        if page_token:
            params["pageToken"] = page_token

        response = self.client.get(self._CATALOG_PATH, params=params)
        logger.info(
            "CatalogApi.search_catalog_items | keywords={} count={}",
            keywords,
            len(response.get("items", [])),
        )
        return response.get("items", [])

    def get_catalog_item_pricing(
        self,
        asin: str,
        marketplace_id: Optional[str] = None,
    ) -> dict:
        """获取商品定价信息（只读）。

        Args:
            asin:          Amazon 商品 ASIN
            marketplace_id: 目标市场 ID

        Returns:
            dict: 定价信息
        """
        mkt_id = marketplace_id or self.client.marketplace_id

        if self.client.dry_run:
            logger.debug("CatalogApi.get_catalog_item_pricing | dry_run=True asin={}", asin)
            return {
                "asin": asin,
                "price": 24.99,
                "currency": "USD",
                "marketplaceId": mkt_id,
                "listingPrice": {"amount": 24.99, "currencyCode": "USD"},
            }

        response = self.client.get(
            f"{self._CATALOG_PATH}/{asin}",
            params={"marketplaceIds": mkt_id, "includedData": "prices"},
        )
        return response
