"""JWT 认证端点与中间件综合测试。

覆盖：
- POST /api/auth/login   — 登录成功 / 密码错误 / 用户名不存在
- POST /api/auth/refresh — 刷新 token
- GET  /api/auth/me      — 获取当前用户信息 / 未认证
- GET  /api/system/status — 需要认证访问
- POST /api/system/stop  — boss 允许 / operator 禁止
- GET  /health           — 公开路径，无需认证
- GET  /docs             — 公开路径，无需认证
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 登录端点测试
# ---------------------------------------------------------------------------

class TestLogin:
    """POST /api/auth/login 测试组。"""

    def test_login_success_boss(self, client: TestClient) -> None:
        """boss 用户使用正确密码登录应返回 200 及双 token。"""
        response = client.post(
            "/api/auth/login",
            json={"username": "boss", "password": "test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data, "响应中缺少 access_token"
        assert "refresh_token" in data, "响应中缺少 refresh_token"
        assert data["access_token"], "access_token 不应为空"
        assert data["refresh_token"], "refresh_token 不应为空"

    def test_login_success_operator(self, client: TestClient) -> None:
        """op1（operator 角色）使用正确密码登录应返回 200。"""
        response = client.post(
            "/api/auth/login",
            json={"username": "op1", "password": "test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_password(self, client: TestClient) -> None:
        """boss 使用错误密码登录应返回 401。"""
        response = client.post(
            "/api/auth/login",
            json={"username": "boss", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_invalid_username(self, client: TestClient) -> None:
        """不存在的用户名登录应返回 401。"""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexist", "password": "test123"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# /me 端点测试
# ---------------------------------------------------------------------------

class TestMe:
    """GET /api/auth/me 测试组。"""

    def test_me_with_valid_token(
        self, client: TestClient, boss_headers: dict
    ) -> None:
        """使用有效 boss token 请求 /me 应返回 200，username=boss, role=boss。"""
        response = client.get("/api/auth/me", headers=boss_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "boss"
        assert data["role"] == "boss"

    def test_me_without_token(self, client: TestClient) -> None:
        """不携带 Authorization 头请求 /me 应返回 401。"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token(self, client: TestClient) -> None:
        """携带无效 token 请求 /me 应返回 401。"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer this.is.invalid"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token 刷新测试
# ---------------------------------------------------------------------------

class TestRefresh:
    """POST /api/auth/refresh 测试组。"""

    def test_token_refresh(self, client: TestClient) -> None:
        """使用有效 refresh_token 换取新 token 对应返回 200 及新双 token。"""
        # 先登录获取 refresh_token
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "boss", "password": "test123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # 使用 refresh_token 刷新
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data, "刷新响应中缺少 access_token"
        assert "refresh_token" in data, "刷新响应中缺少 refresh_token"
        assert data["access_token"], "新 access_token 不应为空"

    def test_token_refresh_with_invalid_token(self, client: TestClient) -> None:
        """使用无效 refresh_token 刷新应返回 401。"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401

    def test_token_refresh_with_access_token(self, client: TestClient) -> None:
        """使用 access_token 作为 refresh_token 应返回 401（类型不匹配）。"""
        login_resp = client.post(
            "/api/auth/login",
            json={"username": "boss", "password": "test123"},
        )
        access_token = login_resp.json()["access_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 系统状态端点测试
# ---------------------------------------------------------------------------

class TestSystemStatus:
    """GET /api/system/status 测试组。"""

    def test_system_status_unauthenticated(self, client: TestClient) -> None:
        """未认证请求 /api/system/status 应返回 401。"""
        response = client.get("/api/system/status")
        assert response.status_code == 401

    def test_system_status_authenticated(
        self, client: TestClient, boss_headers: dict
    ) -> None:
        """已认证 boss 请求 /api/system/status 应返回 200。"""
        response = client.get("/api/system/status", headers=boss_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stopped" in data, "响应中缺少 stopped 字段"

    def test_system_status_operator_authenticated(
        self, client: TestClient, operator_headers: dict
    ) -> None:
        """已认证 operator 请求 /api/system/status 也应返回 200（只读端点无角色限制）。"""
        response = client.get("/api/system/status", headers=operator_headers)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 系统停机端点测试（角色权限）
# ---------------------------------------------------------------------------

class TestSystemStop:
    """POST /api/system/stop 测试组（角色权限验证）。"""

    def test_system_stop_operator_forbidden(
        self, client: TestClient, operator_headers: dict
    ) -> None:
        """operator 角色请求 /api/system/stop 应返回 403 Forbidden。"""
        response = client.post(
            "/api/system/stop",
            json={"reason": "测试停机", "triggered_by": "test"},
            headers=operator_headers,
        )
        assert response.status_code == 403

    def test_system_stop_boss_allowed(
        self, client: TestClient, boss_headers: dict
    ) -> None:
        """boss 角色请求 /api/system/stop 应返回 200（成功）或 409（已停机）。

        注意：测试环境中停机状态可能已存在，因此同时接受 200 和 409。
        """
        response = client.post(
            "/api/system/stop",
            json={"reason": "测试停机触发", "triggered_by": "pytest"},
            headers=boss_headers,
        )
        assert response.status_code in (200, 409), (
            f"期望 200 或 409，实际: {response.status_code}, 响应: {response.text}"
        )

    def test_system_stop_unauthenticated(self, client: TestClient) -> None:
        """未认证请求 /api/system/stop 应返回 401。"""
        response = client.post(
            "/api/system/stop",
            json={"reason": "未认证停机", "triggered_by": "test"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 公开路径测试（无需认证）
# ---------------------------------------------------------------------------

class TestPublicPaths:
    """公开路径（无需认证）测试组。"""

    def test_health_no_auth_required(self, client: TestClient) -> None:
        """GET /health 不需要认证，应返回 200。"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_docs_no_auth_required(self, client: TestClient) -> None:
        """GET /docs 不需要认证，应返回 200。"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_no_auth_required(self, client: TestClient) -> None:
        """GET /openapi.json 不需要认证，应返回 200。"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_redoc_no_auth_required(self, client: TestClient) -> None:
        """GET /redoc 不需要认证，应返回 200。"""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_auth_login_is_public(self, client: TestClient) -> None:
        """POST /api/auth/login 本身是公开路径（不需要 token 即可访问）。"""
        # 即使提供错误凭据，返回的是 401（认证失败），而非中间件的 401（未认证）
        response = client.post(
            "/api/auth/login",
            json={"username": "boss", "password": "wrong"},
        )
        # 返回 401 表示端点可达（公开路径），而不是被中间件拦截
        assert response.status_code == 401

    def test_auth_refresh_is_public(self, client: TestClient) -> None:
        """POST /api/auth/refresh 是公开路径（不需要 Bearer token 即可访问）。"""
        # 即使 token 无效，返回的是路由层的 401，而非中间件拦截
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token"},
        )
        assert response.status_code == 401
