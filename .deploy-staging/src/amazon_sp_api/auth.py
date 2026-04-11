"""Amazon SP-API OAuth 2.0 认证管理模块。

处理 access token 的获取与自动刷新。
dry_run=True（默认）时不进行真实网络请求，返回 mock token。
"""
from __future__ import annotations

import time
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


# Amazon OAuth 2.0 token endpoint
_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# Token 有效期默认3600秒，提前60秒刷新
_TOKEN_TTL = 3600
_TOKEN_REFRESH_BUFFER = 60


class SpApiAuthError(Exception):
    """SP-API 认证错误。"""


class SpApiAuth:
    """SP-API OAuth 2.0 认证管理。

    负责管理 access token 的生命周期：
      - dry_run=True：返回 mock token，不进行真实网络请求
      - dry_run=False：通过 Amazon OAuth 2.0 端点换取并刷新 token

    Args:
        client_id:     LWA (Login with Amazon) 客户端 ID
        client_secret: LWA 客户端密钥
        refresh_token: 通过授权流程获取的长期 refresh token
        region:        AWS 区域，如 "us-east-1"
        dry_run:       True 时返回 mock token（默认），False 时进行真实调用
    """

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        refresh_token: str = "",
        region: str = "us-east-1",
        dry_run: bool = True,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.region = region
        self.dry_run = dry_run

        # 当前 access token 及其过期时间
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0  # Unix timestamp

        logger.info(
            "SpApiAuth initialized | region={} dry_run={}",
            region,
            dry_run,
        )

    def get_access_token(self) -> str:
        """获取/刷新 access token。

        dry_run=True 时直接返回 mock token，不检查过期。
        dry_run=False 时检查并在需要时刷新 token。

        Returns:
            str: access token 字符串
        """
        if self.dry_run:
            logger.debug("SpApiAuth.get_access_token | dry_run=True → returning mock token")
            return "mock_access_token_12345"

        # 真实模式：检查凭证
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise SpApiAuthError(
                "Missing credentials: client_id, client_secret, and refresh_token are required "
                "when dry_run=False"
            )

        self._refresh_token_if_needed()
        return self._access_token or ""

    def is_token_expired(self) -> bool:
        """检查当前 access token 是否已过期（含提前刷新缓冲）。

        Returns:
            bool: True 表示 token 已过期或即将过期（需要刷新）
        """
        if self._access_token is None:
            return True
        # 提前 _TOKEN_REFRESH_BUFFER 秒视为过期
        return time.time() >= (self._token_expires_at - _TOKEN_REFRESH_BUFFER)

    def _refresh_token_if_needed(self) -> None:
        """检查 token 是否过期，过期时自动刷新。"""
        if self.is_token_expired():
            logger.info("SpApiAuth: token expired or missing, refreshing...")
            self._do_refresh()

    def _do_refresh(self) -> None:
        """执行真实的 token 刷新请求（dry_run=False 时调用）。

        POST https://api.amazon.com/auth/o2/token
        grant_type=refresh_token
        """
        try:
            import urllib.request
            import urllib.parse
            import json

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
                "SpApiAuth: token refreshed successfully, expires_in={}s",
                expires_in,
            )

        except Exception as exc:
            logger.error("SpApiAuth: token refresh failed | error={}", exc)
            raise SpApiAuthError(f"Token refresh failed: {exc}") from exc

    def set_mock_token(self, token: str, expires_in: float = 3600.0) -> None:
        """手动设置 token（测试辅助方法）。

        Args:
            token:      access token 字符串
            expires_in: 有效期秒数
        """
        self._access_token = token
        self._token_expires_at = time.time() + expires_in
        logger.debug("SpApiAuth: mock token set, expires_in={}s", expires_in)
