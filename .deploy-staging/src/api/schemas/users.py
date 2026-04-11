"""用户管理相关的 Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  请求模型
# --------------------------------------------------------------------------- #

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="operator", pattern=r"^(boss|operator)$")
    display_name: Optional[str] = Field(default=None, max_length=128)


class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern=r"^(boss|operator)$")
    display_name: Optional[str] = Field(default=None, max_length=128)
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


# --------------------------------------------------------------------------- #
#  响应模型
# --------------------------------------------------------------------------- #

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    display_name: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
