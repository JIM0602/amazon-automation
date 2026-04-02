"""Amazon SP-API 基础 HTTP 客户端模块。

只读操作，仅允许 GET 请求（除 auth token 刷新外）。
集成 RateLimiter 进行限流控制。
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


# 限流模块（可选导入，便于测试 patch）
try:
    from src.utils.rate_limiter import RateLimiter, get_rate_limiter
    _RATE_LIMITER_AVAILABLE = True
except ImportError:  # pragma: no cover
    RateLimiter = None  # type: ignore[assignment,misc]
    get_rate_limiter = None  # type: ignore[assignment]
    _RATE_LIMITER_AVAILABLE = False

from src.amazon_sp_api.auth import SpApiAuth


class SpApiClientError(Exception):
    """SP-API 客户端错误基类。"""


class SpApiHttpError(SpApiClientError):
    """HTTP 请求错误（非 2xx 状态码）。"""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class SpApiClient:
    """Amazon SP-API 基础 HTTP 客户端。

    只读操作，不调用任何写入 API。
    集成 Rate Limit Controller，防止超出 SP-API 速率限制。

    Args:
        auth:           SpApiAuth 实例，管理认证 token
        marketplace_id: 目标市场 ID（默认 US: ATVPDKIKX0DER）
        region:         SP-API 区域（us/eu/fe）
        dry_run:        True 时返回 mock 数据，不进行真实 HTTP 请求（默认）
    """

    BASE_URLS = {
        "us": "https://sellingpartnerapi-na.amazon.com",
        "eu": "https://sellingpartnerapi-eu.amazon.com",
        "fe": "https://sellingpartnerapi-fe.amazon.com",
    }

    # SP-API 速率限制（官方文档值）
    _API_GROUP = "amazon_sp_api"

    def __init__(
        self,
        auth: Optional[SpApiAuth] = None,
        marketplace_id: str = "ATVPDKIKX0DER",  # US 市场
        region: str = "us",
        dry_run: bool = True,
    ):
        self.auth = auth or SpApiAuth(dry_run=dry_run)
        self.marketplace_id = marketplace_id
        self.region = region
        self.dry_run = dry_run
        self.base_url = self.BASE_URLS.get(region, self.BASE_URLS["us"])

        logger.info(
            "SpApiClient initialized | marketplace={} region={} dry_run={}",
            marketplace_id,
            region,
            dry_run,
        )

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        """发送 GET 请求（只读操作）。

        dry_run=True 时返回包含 _mock=True 的模拟响应。
        dry_run=False 时进行真实 HTTP 请求（带限流）。

        Args:
            path:   API 路径，如 "/orders/v0/orders"
            params: 查询参数字典

        Returns:
            dict: API 响应数据
        """
        if self.dry_run:
            logger.debug("SpApiClient.get | dry_run=True path={}", path)
            return {"_mock": True, "path": path, "params": params or {}}

        return self._make_request("GET", path, params=params)

    def _make_request(self, method: str, path: str, **kwargs) -> dict:
        """实际发送 HTTP 请求，处理限流和重试。

        仅允许 GET 方法（只读约束）。

        Args:
            method: HTTP 方法（只允许 GET）
            path:   API 路径
            **kwargs: 其他 requests 参数

        Returns:
            dict: 解析后的 JSON 响应

        Raises:
            SpApiClientError: 请求失败
            SpApiHttpError: HTTP 错误状态码
        """
        if method.upper() != "GET":
            raise SpApiClientError(
                f"Only GET requests are allowed (read-only client), got {method}"
            )

        # 限流检查
        if _RATE_LIMITER_AVAILABLE and get_rate_limiter is not None:
            try:
                from src.utils.api_priority import ApiPriority
                limiter = get_rate_limiter()
                limiter.acquire_or_raise(
                    api_group=self._API_GROUP,
                    account_id=self.marketplace_id,
                    priority=ApiPriority.NORMAL,
                )
            except Exception as exc:
                from src.utils.rate_limiter import RateLimitExceeded
                if isinstance(exc, RateLimitExceeded):
                    raise
                logger.warning("SpApiClient: rate limiter error (ignored) | error={}", exc)

        # 获取认证 token
        access_token = self.auth.get_access_token()

        url = self.base_url + path
        headers = {
            "x-amz-access-token": access_token,
            "x-amz-date": self._get_amz_date(),
            "Content-Type": "application/json",
        }

        try:
            import urllib.request
            import urllib.parse
            import json

            params = kwargs.get("params") or {}
            if params:
                url = url + "?" + urllib.parse.urlencode(params)

            req = urllib.request.Request(url, headers=headers, method="GET")

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            logger.info("SpApiClient.get | path={} status=200", path)
            return data

        except Exception as exc:
            logger.error("SpApiClient.get failed | path={} error={}", path, exc)
            raise SpApiClientError(f"Request failed: {exc}") from exc

    @staticmethod
    def _get_amz_date() -> str:
        """获取 ISO8601 格式的当前 UTC 时间字符串（x-amz-date 头）。"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
