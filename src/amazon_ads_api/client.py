"""Amazon Ads 基础 HTTP 客户端模块。

只读操作，仅允许 GET 请求；POST 仅允许用于报告创建。
集成 RateLimiter 进行限流控制。
"""
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


try:
    from src.utils.rate_limiter import RateLimiter, get_rate_limiter
    rate_limiter_available = True
except ImportError:  # pragma: no cover
    RateLimiter = None  # type: ignore[assignment,misc]
    get_rate_limiter = None  # type: ignore[assignment]
    rate_limiter_available = False

from src.amazon_ads_api.auth import AmazonAdsAuth


class AmazonAdsClientError(Exception):
    """Amazon Ads 客户端错误基类。"""


class AmazonAdsHttpError(AmazonAdsClientError):
    """HTTP 请求错误（非 2xx 状态码）。"""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class AmazonAdsClient:
    """Amazon Ads 基础 HTTP 客户端。"""

    BASE_URLS = {
        "NA": "https://advertising-api.amazon.com",
        "EU": "https://advertising-api-eu.amazon.com",
        "FE": "https://advertising-api-fe.amazon.com",
    }

    _API_GROUP = "amazon_ads_api"

    def __init__(
        self,
        auth: Optional[AmazonAdsAuth] = None,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
        profile_id: str = "",
        region: str = "NA",
        dry_run: bool = True,
    ):
        self.auth = auth or AmazonAdsAuth(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            region=region,
            dry_run=dry_run,
        )
        self.client_id = client_id or self.auth.client_id
        self.profile_id = profile_id
        self.region = region
        self.dry_run = dry_run
        self.base_url = self.BASE_URLS.get(region, self.BASE_URLS["NA"])

        logger.info(
            "AmazonAdsClient initialized | profile={} region={} dry_run={}",
            profile_id,
            region,
            dry_run,
        )

    def get(self, path: str, params: Optional[dict[str, str]] = None) -> dict[str, Any]:
        if self.dry_run:
            logger.debug("AmazonAdsClient.get | dry_run=True path={}", path)
            return {"_mock": True, "path": path, "params": params or {}}

        return self._make_request("GET", path, params=params)

    def post(
        self,
        path: str,
        json_body: Optional[dict[str, Any]] = None,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        if not self._is_report_creation_path(path):
            raise AmazonAdsClientError("Only report creation POST requests are allowed")

        if self.dry_run:
            logger.debug("AmazonAdsClient.post | dry_run=True path={}", path)
            return {"_mock": True, "path": path, "body": json_body or {}}

        return self._make_request("POST", path, json_body=json_body, content_type=content_type)

    def _is_report_creation_path(self, path: str) -> bool:
        return path.rstrip("/") in {"/reporting/reports", "/v2/reports", "/reports"} or "/reporting/reports" in path

    def _make_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if method.upper() not in {"GET", "POST"}:
            raise AmazonAdsClientError(f"Only GET/POST requests are allowed, got {method}")

        if method.upper() == "POST" and not self._is_report_creation_path(path):
            raise AmazonAdsClientError("POST is only allowed for report creation requests")

        if rate_limiter_available and get_rate_limiter is not None:
            try:
                from src.utils.api_priority import ApiPriority

                limiter = get_rate_limiter()
                limiter.acquire_or_raise(
                    api_group=self._API_GROUP,
                    account_id=self.profile_id or self.client_id,
                    priority=ApiPriority.NORMAL,
                )
            except Exception as exc:
                from src.utils.rate_limiter import RateLimitExceeded

                if isinstance(exc, RateLimitExceeded):
                    raise
                logger.warning("AmazonAdsClient: rate limiter error (ignored) | error={}", exc)

        access_token = self.auth.get_access_token()
        url = self.base_url + path

        # 使用调用者指定的 Content-Type（v3 报告 API 需要特殊头）
        content_type = kwargs.get("content_type", "application/json")

        headers = {
            "Amazon-Advertising-API-ClientId": self.client_id,
            "Amazon-Advertising-API-Scope": self.profile_id,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
            "Accept": "application/json",
        }

        try:
            import json
            import urllib.parse
            import urllib.request

            params = cast(dict[str, str], kwargs.get("params") or {})
            if params:
                url = url + "?" + urllib.parse.urlencode(params)

            data = None
            if method.upper() == "POST":
                data = json.dumps(cast(dict[str, Any], kwargs.get("json_body") or {})).encode("utf-8")

            req = urllib.request.Request(url, headers=headers, data=data, method=method.upper())

            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                try:
                    return json.loads(raw)
                except Exception:
                    return {"raw": raw}

        except Exception as exc:
            logger.error("AmazonAdsClient request failed | method={} path={} error={}", method, path, exc)
            raise AmazonAdsClientError(f"Request failed: {exc}") from exc
