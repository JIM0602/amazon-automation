"""JWT 认证中间件。

JWTAuthMiddleware：
- 从 Authorization: Bearer <token> 头提取 token
- 验证签名与过期时间
- 将用户信息注入 request.state.user
- 公开路径跳过认证
- 非公开路径无有效 token 时返回 401 JSON
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  公开路径配置
# --------------------------------------------------------------------------- #

# 精确匹配路径（不需要认证）
PUBLIC_PATHS_EXACT: frozenset[str] = frozenset({
    "/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
})

# 前缀匹配路径（不需要认证）
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/feishu/",
    "/api/ads-oauth/",
)


def _is_public_path(path: str) -> bool:
    """判断路径是否为公开路径（无需认证）。"""
    if path in PUBLIC_PATHS_EXACT:
        return True
    for prefix in PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _is_local_health_request(request: Request) -> bool:
    """仅允许本机或 Docker 内网访问 health 接口免 JWT。"""
    path = request.url.path
    client = request.client
    host = client.host if client is not None else ""
    if not path.startswith("/api/health/"):
        return False
    return host in {"127.0.0.1", "::1"} or host.startswith("172.")


# --------------------------------------------------------------------------- #
#  中间件
# --------------------------------------------------------------------------- #

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI JWT 认证中间件。

    验证成功后向 request.state.user 注入::

        {"username": "boss", "role": "boss"}

    公开路径直接放行，不设置 request.state.user。
    """

    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        super().__init__(app, **kwargs)
        # 延迟导入避免循环依赖
        from src.api.auth import JWT_ALGORITHM, JWT_SECRET  # noqa: PLC0415
        self._secret = JWT_SECRET
        self._algorithm = JWT_ALGORITHM

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        if _is_public_path(path):
            return await call_next(request)

        if _is_local_health_request(request):
            return await call_next(request)

        # 提取 token
        authorization: str = request.headers.get("Authorization", "")
        token: str | None = None
        if authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):]

        if not token:
            return _unauthorized_response("Not authenticated")

        # 验证 token
        user_info = self._verify_access_token(token)
        if user_info is None:
            return _unauthorized_response("Not authenticated")

        # 注入用户信息
        request.state.user = user_info
        return await call_next(request)

    def _verify_access_token(self, token: str) -> Dict[str, Any] | None:
        """验证 access token，返回用户信息 dict 或 None。"""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            logger.debug("JWT 验证失败: %s", exc)
            return None

        if payload.get("type") != "access":
            logger.debug("JWT type 错误: %s", payload.get("type"))
            return None

        username: str = payload.get("sub", "")
        role: str = payload.get("role", "")
        if not username:
            return None

        return {"username": username, "role": role}


def _unauthorized_response(detail: str) -> Response:
    """构造 401 JSON 响应。"""
    body = json.dumps({"detail": detail})
    return Response(
        content=body,
        status_code=401,
        media_type="application/json",
        headers={"WWW-Authenticate": "Bearer"},
    )
