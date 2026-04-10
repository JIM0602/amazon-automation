"""Agent RBAC enforcement tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from src.api.auth import JWT_ALGORITHM, JWT_SECRET, create_access_token
from src.db.connection import get_db


@dataclass
class _FakeRun:
    agent_type: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "success"
    input_summary: str | None = None
    output_summary: str | None = None
    cost_usd: float | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    result_json: dict[str, Any] | None = None


@dataclass
class _FakeQuery:
    runs: list[_FakeRun] = field(default_factory=list)
    exclude_auditor: bool = False

    def filter(self, *criteria: Any) -> "_FakeQuery":
        if criteria:
            self.exclude_auditor = True
        return self

    def order_by(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def offset(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def count(self) -> int:
        return len(self.all())

    def all(self) -> list[_FakeRun]:
        if self.exclude_auditor:
            return [run for run in self.runs if run.agent_type != "auditor"]
        return list(self.runs)

    def first(self) -> None:
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.runs: list[_FakeRun] = []

    def query(self, model: Any) -> _FakeQuery:
        return _FakeQuery(self.runs)

    def add(self, obj: Any) -> None:
        self.runs.append(_FakeRun(agent_type=getattr(obj, "agent_type", "")))

    def commit(self) -> None:
        return None

    def refresh(self, obj: Any) -> None:
        return None

    def close(self) -> None:
        return None


@pytest.fixture()
def fake_session() -> _FakeSession:
    return _FakeSession()


@pytest.fixture()
def client(fake_session: _FakeSession) -> Generator[TestClient, None, None]:
    from src.api.main import app

    def _override_get_db() -> Generator[_FakeSession, None, None]:
        yield fake_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def boss_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token('boss', 'boss')}"}


@pytest.fixture()
def operator_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token('op1', 'operator')}"}


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token_without_role() -> str:
    return jwt.encode(
        {"sub": "ghost", "type": "access"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _token_with_invalid_role() -> str:
    return jwt.encode(
        {"sub": "guest", "role": "guest", "type": "access"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture(autouse=True)
def _disable_agent_background(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.api.agents as agents_module

    monkeypatch.setattr(agents_module, "_run_agent_background", lambda *args, **kwargs: None)


def test_boss_can_run_core_management(client: TestClient, boss_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/agents/core_management/run",
        json={"dry_run": True, "params": {"report_type": "daily"}},
        headers=boss_headers,
    )
    assert response.status_code != 403


def test_operator_can_run_core_management(client: TestClient, operator_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/agents/core_management/run",
        json={"dry_run": True, "params": {"report_type": "daily"}},
        headers=operator_headers,
    )
    assert response.status_code != 403


def test_operator_cannot_run_auditor(client: TestClient, operator_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/agents/auditor/run",
        json={"dry_run": True, "params": {}},
        headers=operator_headers,
    )
    assert response.status_code == 403


def test_boss_can_run_auditor(client: TestClient, boss_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/agents/auditor/run",
        json={"dry_run": True, "params": {}},
        headers=boss_headers,
    )
    assert response.status_code != 403


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/agents/core_management/run",
        json={"dry_run": True, "params": {"report_type": "daily"}},
    )
    assert response.status_code == 401


def test_missing_role_token_returns_403(client: TestClient) -> None:
    response = client.post(
        "/api/agents/core_management/run",
        json={"dry_run": True, "params": {"report_type": "daily"}},
        headers=_auth_headers(_token_without_role()),
    )
    assert response.status_code == 403


def test_invalid_role_token_returns_403(client: TestClient) -> None:
    response = client.post(
        "/api/agents/core_management/run",
        json={"dry_run": True, "params": {"report_type": "daily"}},
        headers=_auth_headers(_token_with_invalid_role()),
    )
    assert response.status_code == 403


def test_operator_does_not_see_auditor_runs_in_list(client: TestClient, boss_headers: dict[str, str], operator_headers: dict[str, str]) -> None:
    boss_response = client.post(
        "/api/agents/auditor/run",
        json={"dry_run": True, "params": {}},
        headers=boss_headers,
    )
    assert boss_response.status_code != 403

    response = client.get("/api/agents/runs", headers=operator_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(run["agent_type"] != "auditor" for run in data["runs"])
