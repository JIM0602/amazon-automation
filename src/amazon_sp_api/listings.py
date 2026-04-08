"""Amazon SP-API Listings Items API。

提供 Listings Items 的只读查询与受审批控制的写入准备/提交能力。
dry_run=True 时返回 mock 数据，不进行真实网络请求。
"""
from __future__ import annotations

from typing import Any, Optional
import importlib
import logging as _logging

try:
    logger = importlib.import_module("loguru").logger
except Exception:  # pragma: no cover
    def _fmt(msg: object, *args: object) -> str:
        text = str(msg)
        return text.format(*args) if args else text

    class _LoggerFallback:
        @staticmethod
        def info(msg: object, *args: object, **kwargs: object) -> None:
            _logging.info(_fmt(msg, *args))

        @staticmethod
        def warning(msg: object, *args: object, **kwargs: object) -> None:
            _logging.warning(_fmt(msg, *args))

        @staticmethod
        def error(msg: object, *args: object, **kwargs: object) -> None:
            _logging.error(_fmt(msg, *args))

        @staticmethod
        def debug(msg: object, *args: object, **kwargs: object) -> None:
            _logging.debug(_fmt(msg, *args))

    logger = _LoggerFallback()

from src.amazon_sp_api.client import SpApiClient, SpApiClientError


class ListingsApiError(Exception):
    """Listings Items API 错误。"""


class ListingsApi:
    """SP-API Listings Items API wrapper。

    约束：
      - GET 仅用于读取
      - prepare_listing 仅准备 payload，不会提交
      - submit_listing 仅在 approved=True 时允许提交
      - dry_run=True 时返回 mock 数据
    """

    _LISTINGS_PATH = "/listings/2021-08-01/items"

    def __init__(self, client: SpApiClient):
        self.client = client

    def get_listing(
        self,
        seller_id: str,
        sku: str,
        marketplace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """GET listing by SKU — read-only, safe to call."""
        mkt_id = marketplace_id or self.client.marketplace_id

        if self.client.dry_run:
            logger.debug("ListingsApi.get_listing | dry_run=True sku={}", sku)
            return {
                "sellerId": seller_id,
                "sku": sku,
                "marketplaceId": mkt_id,
                "itemName": f"Mock Listing for {sku}",
                "brandName": "MockBrand",
                "productType": "PRODUCT",
                "_mock": True,
            }

        params = {"marketplaceIds": mkt_id}
        response = self.client.get(f"{self._LISTINGS_PATH}/{seller_id}/{sku}", params=params)
        logger.info("ListingsApi.get_listing | seller_id={} sku={}", seller_id, sku)
        return response

    def prepare_listing(
        self,
        seller_id: str,
        sku: str,
        product_data: dict[str, Any],
        marketplace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Validate and prepare a listing payload WITHOUT submitting.

        Returns the prepared payload with requires_approval=True.
        """
        if not isinstance(product_data, dict):
            raise ListingsApiError("product_data must be a dict")

        mkt_id = marketplace_id or self.client.marketplace_id
        title = str(product_data.get("title", "")).strip()
        description = str(product_data.get("description", "")).strip()
        bullet_points = product_data.get("bullet_points", []) or []
        brand = str(product_data.get("brand", "")).strip()
        sku_value = str(product_data.get("sku", sku) or sku).strip()

        missing = [
            field
            for field, value in {
                "title": title,
                "description": description,
                "bullet_points": bullet_points,
                "brand": brand,
                "sku": sku_value,
            }.items()
            if not value
        ]
        if missing:
            raise ListingsApiError(f"Missing required fields: {', '.join(missing)}")

        prepared_payload = {
            "sellerId": seller_id,
            "sku": sku_value,
            "marketplaceId": mkt_id,
            "productType": product_data.get("product_type", "PRODUCT"),
            "attributes": {
                "item_name": [title],
                "brand": [brand],
                "description": [description],
                "bullet_point": [str(bp) for bp in bullet_points],
            },
            "requires_approval": True,
        }

        if self.client.dry_run:
            logger.debug("ListingsApi.prepare_listing | dry_run=True sku={}", sku_value)
            prepared_payload["_mock"] = True
            return prepared_payload

        logger.info("ListingsApi.prepare_listing | seller_id={} sku={}", seller_id, sku_value)
        return prepared_payload

    def submit_listing(
        self,
        seller_id: str,
        sku: str,
        payload: dict[str, Any],
        marketplace_id: Optional[str] = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Submit a prepared listing. ONLY executes if approved=True.

        This method uses PUT which is a WRITE operation.
        """
        mkt_id = marketplace_id or self.client.marketplace_id
        if not isinstance(payload, dict):
            raise ListingsApiError("payload must be a dict")

        if self.client.dry_run:
            logger.warning(
                "ListingsApi.submit_listing | dry_run=True seller_id={} sku={} approved={}",
                seller_id,
                sku,
                approved,
            )
            return {
                "sellerId": seller_id,
                "sku": sku,
                "marketplaceId": mkt_id,
                "status": "mock_submitted",
                "requires_approval": True,
                "approved": True,
                "_mock": True,
            }

        if not approved:
            raise ListingsApiError("Listing submission requires approval (approved=True)")

        if payload.get("requires_approval") is not True:
            raise ListingsApiError("Prepared payload must include requires_approval=True")

        if not payload.get("approved") and not approved:
            raise ListingsApiError("Approved listing payload required before submission")

        path = f"{self._LISTINGS_PATH}/{seller_id}/{sku}"
        body = dict(payload)
        body["marketplaceId"] = mkt_id
        body["approved"] = True
        try:
            response = self.client.put(path, data=body, approved=True)
            logger.info("ListingsApi.submit_listing | seller_id={} sku={}", seller_id, sku)
            return response
        except SpApiClientError as exc:
            raise ListingsApiError(str(exc)) from exc
