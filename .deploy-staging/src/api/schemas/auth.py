"""Pydantic models for authentication."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """POST /api/auth/login 请求体。"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """认证成功后返回的 Token 响应。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """POST /api/auth/refresh 请求体。"""
    refresh_token: str


class UserInfo(BaseModel):
    """当前认证用户信息。"""
    username: str
    role: Literal["boss", "operator"]
