"""add users table

Revision ID: 005_add_users_table
Revises: 004_add_phase4
Create Date: 2026-04-10

"""

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false

import uuid
from datetime import datetime, timezone

from alembic import op
from passlib.hash import bcrypt
from sqlalchemy import Boolean, Column, DateTime, String, inspect, text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "005_add_users_table"
down_revision = "004_add_phase4"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid_type():
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return String(36)


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if _has_table("users"):
        return

    op.create_table(
        "users",
        Column("id", _uuid_type(), primary_key=True, default=uuid.uuid4),
        Column("username", String(64), nullable=False, unique=True, index=True),
        Column("password_hash", String(256), nullable=False),
        Column("role", String(32), nullable=False, server_default="operator"),
        Column("display_name", String(128), nullable=True),
        Column("is_active", Boolean(), nullable=False, server_default=text("true")),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    )

    conn = op.get_bind()
    rows = [
        {
            "id": str(uuid.uuid4()),
            "username": "boss",
            "password_hash": bcrypt.hash("test123"),
            "role": "boss",
            "display_name": "Boss",
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        },
        {
            "id": str(uuid.uuid4()),
            "username": "op1",
            "password_hash": bcrypt.hash("test123"),
            "role": "operator",
            "display_name": "Operator 1",
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        },
        {
            "id": str(uuid.uuid4()),
            "username": "op2",
            "password_hash": bcrypt.hash("test123"),
            "role": "operator",
            "display_name": "Operator 2",
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        },
    ]
    conn.execute(
        text(
            """
            INSERT INTO users (id, username, password_hash, role, display_name, is_active, created_at, updated_at)
            VALUES (:id, :username, :password_hash, :role, :display_name, :is_active, :created_at, :updated_at)
            """
        ),
        rows,
    )


def downgrade() -> None:
    op.drop_table("users")
