"""Amazon Ads OAuth 2.0 认证管理模块。

处理 access token 的获取与自动刷新。
dry_run=True（默认）时不进行真实网络请求，返回 mock token。
"""
from __future__ import annotations

import time
from typing import Optional

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


_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
_TOKEN_TTL = 3600
_TOKEN_REFRESH_BUFFER = 60


class AmazonAdsAuthError(Exception):
    """Amazon Ads 认证错误。"""


class AmazonAdsAuth:
    """Amazon Ads OAuth 2.0 认证管理。"""

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
        region: str = "NA",
        dry_run: bool = True,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.region = region
        self.dry_run = dry_run

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        logger.info(
            "AmazonAdsAuth initialized | region={} dry_run={}",
            region,
            dry_run,
        )

    def get_access_token(self) -> str:
        if self.dry_run:
            logger.debug("AmazonAdsAuth.get_access_token | dry_run=True -> returning mock token")
            return "mock_access_token_12345"

        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise AmazonAdsAuthError(
                "Missing credentials: client_id, client_secret, and refresh_token are required when dry_run=False"
            )

        self._refresh_token_if_needed()
        return self._access_token or ""

    def is_token_expired(self) -> bool:
        if self._access_token is None:
            return True
        return time.time() >= (self._token_expires_at - _TOKEN_REFRESH_BUFFER)

    def _refresh_token_if_needed(self) -> None:
        if self.is_token_expired():
            logger.info("AmazonAdsAuth: token expired or missing, refreshing...")
            self._do_refresh()

    def _do_refresh(self) -> None:
        try:
            import json
            import urllib.parse
            import urllib.request

            payload = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }).encode("utf-8")

            req = urllib.request.Request(
                _TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            self._access_token = data["access_token"]
            expires_in = int(data.get("expires_in", _TOKEN_TTL))
            self._token_expires_at = time.time() + expires_in

            logger.info(
                "AmazonAdsAuth: token refreshed successfully, expires_in={}s",
                expires_in,
            )
        except Exception as exc:
            logger.error("AmazonAdsAuth: token refresh failed | error={}", exc)
            raise AmazonAdsAuthError(f"Token refresh failed: {exc}") from exc

    def set_mock_token(self, token: str, expires_in: float = 3600.0) -> None:
        self._access_token = token
        self._token_expires_at = time.time() + expires_in
        logger.debug("AmazonAdsAuth: mock token set, expires_in={}s", expires_in)
