"""用户管理 CRUD REST API。

端点：
- GET    /api/users                — 用户列表（boss only）
- POST   /api/users                — 创建用户（boss only）
- PUT    /api/users/{user_id}      — 更新用户（boss only）
- DELETE /api/users/{user_id}      — 停用用户（boss only，不能停用自己）
- PUT    /api/users/me/password    — 修改自己密码（all roles）
"""
from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import require_role, get_current_user
from src.api.schemas.users import (
    ChangePasswordRequest,
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from src.db import get_db
from src.db.users import (
    create_user,
    deactivate_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
    update_user,
    verify_password,
)

router = APIRouter(prefix="/api/users", tags=["users"])


# --------------------------------------------------------------------------- #
#  Helper
# --------------------------------------------------------------------------- #

def _user_to_response(user: Any) -> UserResponse:
    """将 ORM User 对象转为响应模型。"""
    return UserResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )


# --------------------------------------------------------------------------- #
#  GET /api/users — 用户列表（boss only）
# --------------------------------------------------------------------------- #

@router.get("", response_model=UserListResponse)
async def api_list_users(
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """返回所有用户列表（含已停用）。仅 boss 可访问。"""
    users = list_users(db)
    return UserListResponse(
        users=[_user_to_response(u) for u in users],
        total=len(users),
    )


# --------------------------------------------------------------------------- #
#  POST /api/users — 创建用户（boss only）
# --------------------------------------------------------------------------- #

@router.post("", response_model=UserResponse, status_code=201)
async def api_create_user(
    body: CreateUserRequest,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """创建新用户。仅 boss 可操作。"""
    try:
        user = create_user(
            db,
            username=body.username,
            password=body.password,
            role=body.role,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _user_to_response(user)


# --------------------------------------------------------------------------- #
#  PUT /api/users/me/password — 修改自己密码（all roles）
#  注意：此路由必须在 /{user_id} 之前注册，否则 "me" 会被当作 user_id
# --------------------------------------------------------------------------- #

@router.put("/me/password", response_model=dict[str, bool])
async def api_change_my_password(
    body: ChangePasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """修改当前用户自己的密码。所有角色可用。"""
    user = get_user_by_username(db, current_user["username"])
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_any = cast(Any, user)
    if not verify_password(body.old_password, user_any.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    update_user(db, user_any.id, password=body.new_password)
    return {"success": True}


# --------------------------------------------------------------------------- #
#  PUT /api/users/{user_id} — 更新用户（boss only）
# --------------------------------------------------------------------------- #

@router.put("/{user_id}", response_model=UserResponse)
async def api_update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """更新指定用户信息。仅 boss 可操作。"""
    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效的用户 ID 格式") from exc

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    user = update_user(db, uid, **update_data)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _user_to_response(user)


# --------------------------------------------------------------------------- #
#  DELETE /api/users/{user_id} — 停用用户（boss only，不能停用自己）
# --------------------------------------------------------------------------- #

@router.delete("/{user_id}", response_model=dict[str, bool])
async def api_deactivate_user(
    user_id: str,
    current_user: dict[str, Any] = Depends(require_role("boss")),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """停用指定用户（软删除）。仅 boss 可操作，不能停用自己。"""
    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效的用户 ID 格式") from exc

    # 检查是否试图停用自己
    me = get_user_by_username(db, current_user["username"])
    me_any = cast(Any, me)
    if me is not None and str(me_any.id) == user_id:
        raise HTTPException(status_code=400, detail="不能停用自己的账号")

    success = deactivate_user(db, uid)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True}
