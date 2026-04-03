"""JWT 认证测试夹具。

提供：
- client        — FastAPI TestClient
- boss_token    — boss 用户的 access_token
- operator_token— op1 用户的 access_token
- boss_headers  — boss 用户的 Authorization 请求头
- operator_headers — op1 用户的 Authorization 请求头
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db import Base


@pytest.fixture(scope="session", autouse=True)
def _init_db() -> None:
    """Create all DB tables once before the test session starts."""
    import src.config as _cfg
    from src.db import connection as _conn

    # Re-instantiate settings so it picks up test env vars
    _cfg.settings = _cfg.Settings()

    # Reset cached engine/session to use the new (test) DATABASE_URL
    _conn._engine = None
    _conn._SessionLocal = None
    engine = _conn.get_engine()
    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient，复用整个测试会话。"""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def boss_token(client: TestClient) -> str:
    """获取 boss 用户的 access_token。"""
    response = client.post(
        "/api/auth/login",
        json={"username": "boss", "password": "test123"},
    )
    assert response.status_code == 200, f"boss 登录失败: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def operator_token(client: TestClient) -> str:
    """获取 op1（operator 角色）用户的 access_token。"""
    response = client.post(
        "/api/auth/login",
        json={"username": "op1", "password": "test123"},
    )
    assert response.status_code == 200, f"op1 登录失败: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def boss_headers(boss_token: str) -> dict:
    """boss 用户的 Authorization Bearer 请求头。"""
    return {"Authorization": f"Bearer {boss_token}"}


@pytest.fixture(scope="session")
def operator_headers(operator_token: str) -> dict:
    """operator 用户的 Authorization Bearer 请求头。"""
    return {"Authorization": f"Bearer {operator_token}"}
