from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import patch

import pytest


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Stub pgvector before importing ORM models.
if "pgvector" not in sys.modules:
    from sqlalchemy.types import UserDefinedType

    class _Vector(UserDefinedType[Any]):
        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw: Any):
            return f"vector({self.dim})"

        class comparator_factory(UserDefinedType.Comparator[Any]):
            pass

    pgvector_mod = types.ModuleType("pgvector")
    pgvector_sa_mod = types.ModuleType("pgvector.sqlalchemy")
    setattr(cast(Any, pgvector_sa_mod), "Vector", _Vector)
    setattr(cast(Any, pgvector_mod), "sqlalchemy", pgvector_sa_mod)
    sys.modules["pgvector"] = cast(Any, pgvector_mod)
    sys.modules["pgvector.sqlalchemy"] = cast(Any, pgvector_sa_mod)


from src.db.models import Base, AgentRun, ApprovalRequest
from src.services.approval import ApprovalService


@pytest.fixture()
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sqlite_session(sqlite_engine):
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


def _make_agent_run(session, agent_type: str = "listing"):
    run = AgentRun()
    run_any = cast(Any, run)
    run_any.agent_type = agent_type
    run_any.status = "success"
    run_any.input_summary = "in"
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def test_submit_for_review_creates_pending_record(sqlite_session):
    service = ApprovalService(sqlite_session)
    run = _make_agent_run(sqlite_session, "listing")

    with patch("src.services.approval.send_approval_request") as mock_notify:
        approval = service.submit_for_review(
            agent_type="listing",
            agent_run_id=str(run.id),
            action_type="create_report",
            payload={"foo": "bar"},
            summary="生成报表",
        )

    approval_any = cast(Any, approval)
    assert approval_any.status == "pending"
    assert approval_any.action_type == "create_report"
    assert approval_any.payload["summary"] == "生成报表"
    assert approval_any.payload["foo"] == "bar"
    mock_notify.assert_called_once()
    assert sqlite_session.query(ApprovalRequest).count() == 1


def test_list_pending_returns_correct_items_per_role(sqlite_session):
    service = ApprovalService(sqlite_session)
    listing_run = _make_agent_run(sqlite_session, "listing")
    auditor_run = _make_agent_run(sqlite_session, "auditor")
    boss_run = _make_agent_run(sqlite_session, "brand_planning")

    sqlite_session.add_all(
        [
            ApprovalRequest(agent_run_id=listing_run.id, action_type="a", payload={}, status="pending"),
            ApprovalRequest(agent_run_id=auditor_run.id, action_type="b", payload={}, status="pending"),
            ApprovalRequest(agent_run_id=boss_run.id, action_type="c", payload={}, status="pending"),
        ]
    )
    sqlite_session.commit()

    boss_items = service.list_pending("boss-1", "boss")
    operator_items = service.list_pending("op-1", "operator")

    assert len(boss_items) == 3
    assert {item.action_type for item in operator_items} == {"a"}


def test_approve_changes_status_to_approved(sqlite_session):
    service = ApprovalService(sqlite_session)
    run = _make_agent_run(sqlite_session, "listing")
    approval = ApprovalRequest()
    approval_any = cast(Any, approval)
    approval_any.agent_run_id = run.id
    approval_any.action_type = "x"
    approval_any.payload = {}
    approval_any.status = "pending"
    sqlite_session.add(approval)
    sqlite_session.commit()
    sqlite_session.refresh(approval)

    assert service.approve(str(approval.id), "boss-1", "boss", "ok") is True
    refreshed = sqlite_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).first()
    assert refreshed is not None
    assert refreshed.status == "approved"
    assert refreshed.approved_by == "boss-1"
    assert refreshed.payload["review_comment"] == "ok"


def test_reject_changes_status_to_rejected_with_comment(sqlite_session):
    service = ApprovalService(sqlite_session)
    run = _make_agent_run(sqlite_session, "listing")
    approval = ApprovalRequest()
    approval_any = cast(Any, approval)
    approval_any.agent_run_id = run.id
    approval_any.action_type = "x"
    approval_any.payload = {}
    approval_any.status = "pending"
    sqlite_session.add(approval)
    sqlite_session.commit()
    sqlite_session.refresh(approval)

    assert service.reject(str(approval.id), "boss-1", "boss", "not now") is True
    refreshed = sqlite_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).first()
    assert refreshed is not None
    assert refreshed.status == "rejected"
    assert refreshed.approved_by == "boss-1"
    assert refreshed.payload["review_comment"] == "not now"


def test_operator_cannot_approve_auditor_or_brand_planning(sqlite_session):
    service = ApprovalService(sqlite_session)
    run = _make_agent_run(sqlite_session, "auditor")
    approval = ApprovalRequest()
    approval_any = cast(Any, approval)
    approval_any.agent_run_id = run.id
    approval_any.action_type = "x"
    approval_any.payload = {}
    approval_any.status = "pending"
    sqlite_session.add(approval)
    sqlite_session.commit()
    sqlite_session.refresh(approval)

    with pytest.raises(PermissionError):
        service.approve(str(approval.id), "op-1", "operator")
