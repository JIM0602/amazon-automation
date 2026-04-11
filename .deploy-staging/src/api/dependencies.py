"""FastAPI 依赖注入工具。

提供：
- get_current_user  — 从 request.state.user 提取已认证用户，未认证时抛出 401
- require_role      — 角色守卫工厂，返回依赖检查用户是否属于允许的角色
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from fastapi import Depends, HTTPException, Request, status


def get_current_user(request: Request) -> Dict[str, Any]:
    """从 request.state.user 中提取已认证用户信息。

    由 JWTAuthMiddleware 注入；如果中间件未注入（即未认证），抛出 401。
    """
    user: Dict[str, Any] | None = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str) -> Callable[..., Dict[str, Any]]:
    """角色守卫工厂函数。

    用法::

        @router.post("/stop")
        async def stop_system(
            body: StopRequest,
            current_user: dict = Depends(require_role("boss")),
        ):
            ...

    Args:
        *roles: 允许访问的角色列表，如 "boss" 或 "boss", "operator"

    Returns:
        FastAPI 依赖函数，检查通过后返回当前用户 dict；
        角色不匹配时抛出 403 Forbidden。
    """
    def _check_role(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色: {', '.join(roles)}",
            )
        return current_user

    return _check_role
