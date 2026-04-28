"""Amazon SP-API 订单 API（只读，不存储个人信息）。

提供订单数据的只读查询和聚合统计功能。
严格遵守隐私原则：不存储 PII（个人可识别信息），仅聚合统计数据。
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


# PII 字段黑名单（绝不存储这些字段）
_PII_FIELDS = frozenset([
    "BuyerEmail", "BuyerName", "BuyerPhone",
    "ShippingAddress", "BillingAddress",
    "PhoneNumber", "Email",
])


class OrdersApiError(Exception):
    """订单 API 错误。"""


def _strip_pii(order: dict) -> dict:
    """移除订单 dict 中的所有 PII 字段。

    Args:
        order: 原始订单 dict

    Returns:
        dict: 不含 PII 字段的订单 dict
    """
    return {k: v for k, v in order.items() if k not in _PII_FIELDS}


class OrdersApi:
    """SP-API 订单 API（只读，不存储个人信息）。

    支持的操作（均为只读）：
      - 获取订单列表（get_orders）
      - 获取订单指标聚合数据（get_order_metrics）

    隐私保护：
      - 自动过滤 PII 字段（email/phone/address）
      - 仅返回聚合统计，不存储订单详情

    Args:
        client: SpApiClient 实例
    """

    _ORDERS_PATH = "/orders/v0/orders"
    _ORDER_METRICS_PATH = "/sales/v1/orderMetrics"

    def __init__(self, client: SpApiClient):
        self.client = client

    def get_orders(
        self,
        created_after: str,
        marketplace_ids: Optional[list] = None,
        order_statuses: Optional[list] = None,
        max_results: int = 100,
        next_token: Optional[str] = None,
    ) -> list:
        """获取订单列表（只聚合统计，自动过滤 PII）。

        dry_run=True 时返回 mock 订单数据。

        注意：返回数据已自动移除 PII 字段（email/phone/address 等）。

        Args:
            created_after:   订单创建时间起始（ISO 8601）
            marketplace_ids: 目标市场 ID 列表
            order_statuses:  过滤订单状态列表（如 ["Shipped", "Delivered"]）
            max_results:     最大返回数量（上限 100）
            next_token:      分页 token

        Returns:
            list[dict]: 订单信息列表（已过滤 PII）
        """
        mkt_ids = marketplace_ids or [self.client.marketplace_id]

        if self.client.dry_run:
            logger.debug(
                "OrdersApi.get_orders | dry_run=True created_after={}",
                created_after,
            )
            mock_orders = [
                {
                    "OrderId": "MOCK-001-001",
                    "OrderStatus": "Shipped",
                    "OrderTotal": {"Amount": "29.99", "CurrencyCode": "USD"},
                    "PurchaseDate": "2026-04-01T10:00:00Z",
                    "MarketplaceId": mkt_ids[0],
                },
                {
                    "OrderId": "MOCK-001-002",
                    "OrderStatus": "Delivered",
                    "OrderTotal": {"Amount": "49.99", "CurrencyCode": "USD"},
                    "PurchaseDate": "2026-04-01T14:00:00Z",
                    "MarketplaceId": mkt_ids[0],
                },
            ]
            # 过滤 PII（即使 mock 数据也执行过滤，保持一致性）
            return [_strip_pii(o) for o in mock_orders]

        params = {
            "CreatedAfter": created_after,
            "MarketplaceIds": ",".join(mkt_ids),
            "MaxResultsPerPage": min(max_results, 100),
        }
        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)
        if next_token:
            params["NextToken"] = next_token

        response = self.client.get(self._ORDERS_PATH, params=params)
        raw_orders = response.get("Orders", [])

        # 强制过滤 PII
        clean_orders = [_strip_pii(o) for o in raw_orders]
        logger.info(
            "OrdersApi.get_orders | count={} created_after={}",
            len(clean_orders),
            created_after,
        )
        return clean_orders

    def get_order_metrics(
        self,
        granularity: str = "Day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        marketplace_id: Optional[str] = None,
    ) -> dict:
        """获取订单指标聚合数据（纯统计，无 PII）。

        dry_run=True 时返回 mock 聚合数据。

        Args:
            granularity:    聚合粒度（Hour/Day/Week/Month/Year/Total）
            start_date:     统计起始日期（ISO 8601）
            end_date:       统计结束日期（ISO 8601）
            marketplace_id: 目标市场 ID

        Returns:
            dict with keys:
                total_orders (int):      订单总量
                total_revenue (float):   总收入（USD）
                avg_order_value (float): 平均订单价值
        """
        mkt_id = marketplace_id or self.client.marketplace_id

        if self.client.dry_run:
            logger.debug(
                "OrdersApi.get_order_metrics | dry_run=True granularity={}",
                granularity,
            )
            return {
                "total_orders": 25,
                "total_revenue": 750.00,
                "avg_order_value": 30.00,
                "granularity": granularity,
                "marketplaceId": mkt_id,
            }

        params = {
            "granularityTimeZone": "UTC",
            "granularity": granularity,
            "marketplaceIds": mkt_id,
        }
        if start_date:
            params["interval"] = f"{start_date}--{end_date or start_date}"

        response = self.client.get(self._ORDER_METRICS_PATH, params=params)

        # 从响应中提取聚合统计
        payload = response.get("payload", [])
        total_orders = sum(int(item.get("orderCount") or item.get("unitCount") or 0) for item in payload)
        total_units = sum(int(item.get("unitCount") or item.get("orderItemCount") or item.get("orderCount") or 0) for item in payload)
        total_revenue = sum(
            float(
                (item.get("totalSales") or {}).get("amount")
                or float(item.get("orderItemCount", 0)) * float((item.get("averageSalesPerOrderItem") or {}).get("amount", 0))
            )
            for item in payload
        )
        avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0.0

        logger.info(
            "OrdersApi.get_order_metrics | total_orders={} total_revenue={}",
            total_orders,
            total_revenue,
        )
        return {
            "total_orders": total_orders,
            "total_units": total_units,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order_value, 2),
            "granularity": granularity,
            "marketplaceId": mkt_id,
        }
