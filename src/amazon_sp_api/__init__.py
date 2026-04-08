"""Amazon SP-API 客户端包。

提供 Amazon Selling Partner API 的只读访问接口。

所有客户端默认以 dry_run=True 模式运行，不进行真实 API 调用。
设置 dry_run=False 并提供有效凭证后才会进行真实请求。

示例::

    from src.amazon_sp_api import SpApiAuth, SpApiClient, OrdersApi

    # dry_run 模式（默认）
    auth = SpApiAuth()
    client = SpApiClient(auth=auth)
    orders_api = OrdersApi(client)
    orders = orders_api.get_orders(created_after="2026-01-01T00:00:00Z")

    # 真实模式（需要有效凭证）
    auth = SpApiAuth(
        client_id="...",
        client_secret="...",
        refresh_token="...",
        dry_run=False,
    )
    client = SpApiClient(auth=auth, dry_run=False)
"""
from .auth import SpApiAuth, SpApiAuthError
from .client import SpApiClient, SpApiClientError, SpApiHttpError
from .reports import ReportsApi, ReportsApiError
from .catalog import CatalogApi, CatalogApiError
from .listings import ListingsApi, ListingsApiError
from .orders import OrdersApi, OrdersApiError

__all__ = [
    # 认证
    "SpApiAuth",
    "SpApiAuthError",
    # 基础客户端
    "SpApiClient",
    "SpApiClientError",
    "SpApiHttpError",
    # 报告 API
    "ReportsApi",
    "ReportsApiError",
    # 目录 API
    "CatalogApi",
    "CatalogApiError",
    # Listings API
    "ListingsApi",
    "ListingsApiError",
    # 订单 API
    "OrdersApi",
    "OrdersApiError",
]
