"""用户数据库操作函数。

提供 User 表的 CRUD 操作，密码哈希与验证。
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User


# --------------------------------------------------------------------------- #
#  密码工具
# --------------------------------------------------------------------------- #

def hash_password(plain: str) -> str:
    """将明文密码哈希为 bcrypt 格式。"""
    return bcrypt.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与 bcrypt 哈希是否匹配。"""
    return bcrypt.verify(plain, hashed)


# --------------------------------------------------------------------------- #
#  查询
# --------------------------------------------------------------------------- #

def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """根据 ID 获取用户。"""
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户。"""
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def list_users(db: Session) -> list[User]:
    """获取所有用户列表（包括已停用的）。"""
    return list(db.execute(select(User).order_by(User.created_at.desc())).scalars().all())


# --------------------------------------------------------------------------- #
#  创建
# --------------------------------------------------------------------------- #

def create_user(
    db: Session,
    username: str,
    password: str,
    role: str = "operator",
    display_name: Optional[str] = None,
) -> User:
    """创建新用户。密码会自动哈希。

    Raises:
        ValueError: 用户名已存在时抛出。
    """
    existing = get_user_by_username(db, username)
    if existing is not None:
        raise ValueError(f"用户名已存在: {username}")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name or username,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
#  更新
# --------------------------------------------------------------------------- #

def update_user(
    db: Session,
    user_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[User]:
    """更新用户信息。

    支持的字段: role, display_name, is_active
    如果传入 password，会自动哈希后写入 password_hash。

    Returns:
        更新后的 User，未找到时返回 None。
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    allowed_fields = {"role", "display_name", "is_active"}
    for key, value in kwargs.items():
        if key == "password":
            user.password_hash = hash_password(value)  # type: ignore[assignment]
        elif key in allowed_fields:
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
#  停用（软删除）
# --------------------------------------------------------------------------- #

def deactivate_user(db: Session, user_id: uuid.UUID) -> bool:
    """停用用户（设置 is_active=False）。

    Returns:
        True 停用成功, False 用户不存在。
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        return False
    user.is_active = False  # type: ignore[assignment]
    db.commit()
    return True
