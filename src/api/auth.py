"""JWT 认证路由。

提供：
- POST /api/auth/login    — 用户名/密码登录，返回 access_token + refresh_token
- POST /api/auth/refresh  — 使用 refresh_token 换取新的 token 对
- GET  /api/auth/me       — 返回当前已认证用户信息
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.hash import bcrypt

from src.api.dependencies import get_current_user
from src.api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserInfo

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  配置
# --------------------------------------------------------------------------- #

JWT_SECRET: str = os.environ.get("JWT_SECRET", "") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_EXPIRE_MINUTES: int = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "480"))
JWT_REFRESH_EXPIRE_DAYS: int = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))


def _build_default_users() -> Dict[str, Dict[str, str]]:
    """构建默认测试用户（boss/test123, op1/test123, op2/test123）。"""
    users: Dict[str, Dict[str, str]] = {}
    defaults = [
        ("boss", "test123", "boss"),
        ("op1", "test123", "operator"),
        ("op2", "test123", "operator"),
    ]
    for username, password, role in defaults:
        users[username] = {
            "password_hash": bcrypt.hash(password),
            "role": role,
        }
    return users


def _parse_web_users(raw: str) -> Dict[str, Dict[str, str]]:
    """解析 WEB_USERS 环境变量。

    格式：username:bcrypt_hash:role,username2:bcrypt_hash2:role2
    """
    users: Dict[str, Dict[str, str]] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 2)
        if len(parts) != 3:
            logger.warning("WEB_USERS 格式错误，跳过: %r", entry)
            continue
        username, password_hash, role = parts
        users[username.strip()] = {
            "password_hash": password_hash.strip(),
            "role": role.strip(),
        }
    return users


# 模块加载时解析用户配置
_raw_web_users = os.environ.get("WEB_USERS", "").strip()
USERS: Dict[str, Dict[str, str]] = (
    _parse_web_users(_raw_web_users) if _raw_web_users else _build_default_users()
)

# --------------------------------------------------------------------------- #
#  Token 工具函数
# --------------------------------------------------------------------------- #

def _create_token(username: str, role: str, token_type: str, expire_delta: timedelta) -> str:
    """创建 JWT token。"""
    now = datetime.now(tz=timezone.utc)
    payload: Dict[str, Any] = {
        "sub": username,
        "role": role,
        "type": token_type,
        "exp": now + expire_delta,
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(username: str, role: str) -> str:
    """创建 access token（默认 480 分钟）。"""
    return _create_token(
        username=username,
        role=role,
        token_type="access",
        expire_delta=timedelta(minutes=JWT_ACCESS_EXPIRE_MINUTES),
    )


def create_refresh_token(username: str, role: str) -> str:
    """创建 refresh token（默认 7 天）。"""
    return _create_token(
        username=username,
        role=role,
        token_type="refresh",
        expire_delta=timedelta(days=JWT_REFRESH_EXPIRE_DAYS),
    )


def verify_token(token: str, expected_type: str) -> Dict[str, Any]:
    """验证 JWT token，返回 payload；失败时抛出 HTTPException 401。"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"token 类型错误，期望 {expected_type}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# --------------------------------------------------------------------------- #
#  路由
# --------------------------------------------------------------------------- #

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """用户名/密码登录。

    Request body::

        {"username": "boss", "password": "test123"}

    Returns access_token + refresh_token on success, 401 on failure.
    """
    user = USERS.get(body.username)
    if user is None or not bcrypt.verify(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = user["role"]
    access_token = create_access_token(body.username, role)
    refresh_token = create_refresh_token(body.username, role)

    logger.info("用户登录成功: username=%s role=%s", body.username, role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    """使用 refresh_token 换取新的 token 对。

    Request body::

        {"refresh_token": "<token>"}
    """
    payload = verify_token(body.refresh_token, expected_type="refresh")
    username: str = payload.get("sub", "")
    role: str = payload.get("role", "")

    # 确认用户仍然存在
    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(username, role)
    new_refresh_token = create_refresh_token(username, role)

    logger.info("Token 刷新成功: username=%s", username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserInfo)
async def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserInfo:
    """返回当前已认证用户信息。

    Requires valid Authorization: Bearer <access_token> header.
    """
    return UserInfo(
        username=current_user["username"],
        role=current_user["role"],
    )
