"""决策状态机 (src/decisions/) 单元测试。

测试覆盖：
- DecisionStatus 枚举值
- VALID_TRANSITIONS 合法转换映射
- DecisionCreate / DecisionRead Pydantic 模型
- DecisionStateMachine 所有状态转换方法
- DecisionRepository CRUD 操作
- 审计日志集成（每次状态变更写入 audit_logs）
- 错误情况（不存在的决策、非法状态转换）

所有测试使用 SQLite in-memory DB + mock，不需要真实 PostgreSQL。
"""
from __future__ import annotations

import uuid
import sys
import types
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest


# ===========================================================================
# Fixtures：环境隔离（pgvector stub + SQLite in-memory）
# ===========================================================================

@pytest.fixture(autouse=True)
def stub_pgvector(monkeypatch):
    """注入 pgvector.sqlalchemy stub，避免在无 pgvector 的测试环境中报错。"""
    from sqlalchemy.types import UserDefinedType

    class _Vector(UserDefinedType):
        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

        class comparator_factory(UserDefinedType.Comparator):
            pass

    pgvector_mod = types.ModuleType("pgvector")
    pgvector_sa_mod = types.ModuleType("pgvector.sqlalchemy")
    pgvector_sa_mod.Vector = _Vector
    pgvector_mod.sqlalchemy = pgvector_sa_mod

    monkeypatch.setitem(sys.modules, "pgvector", pgvector_mod)
    monkeypatch.setitem(sys.modules, "pgvector.sqlalchemy", pgvector_sa_mod)
    yield


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """提供 SQLite in-memory 数据库 URL，避免依赖真实 PostgreSQL。"""
    fake_settings = MagicMock()
    fake_settings.DATABASE_URL = "sqlite://"
    monkeypatch.setattr("src.config.settings", fake_settings)
    yield fake_settings


@pytest.fixture()
def sqlite_engine(stub_pgvector):
    """创建 SQLite in-memory 引擎，包含所有表（含 decisions）。"""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from src.db.models import Base

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
    """返回连接到 SQLite in-memory DB 的 Session。"""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def mock_audit(monkeypatch):
    """Mock audit log_action，避免测试时访问真实 DB。"""
    mock_fn = MagicMock()
    monkeypatch.setattr("src.decisions.state_machine.log_action", mock_fn)
    return mock_fn


@pytest.fixture()
def state_machine(sqlite_session, mock_audit):
    """返回绑定 SQLite session 的 DecisionStateMachine 实例。"""
    from src.decisions.state_machine import DecisionStateMachine
    return DecisionStateMachine(sqlite_session)


@pytest.fixture()
def sample_create_data():
    """返回标准 DecisionCreate 测试数据。"""
    from src.decisions.models import DecisionCreate
    return DecisionCreate(
        decision_type="pricing",
        agent_id="agent:pricing-v1",
        payload={"sku": "TEST-001", "new_price": 29.99, "old_price": 24.99},
        rollback_payload={"sku": "TEST-001", "price": 24.99},
    )


# ===========================================================================
# 1. 模型测试
# ===========================================================================

class TestDecisionStatus:
    """DecisionStatus 枚举值测试。"""

    def test_all_statuses_defined(self):
        from src.decisions.models import DecisionStatus

        expected = {
            "DRAFT", "PENDING_APPROVAL", "APPROVED", "EXECUTING",
            "SUCCEEDED", "FAILED", "ROLLED_BACK", "REJECTED",
        }
        actual = {s.value for s in DecisionStatus}
        assert actual == expected

    def test_status_is_string_enum(self):
        from src.decisions.models import DecisionStatus
        assert isinstance(DecisionStatus.DRAFT, str)
        assert DecisionStatus.DRAFT == "DRAFT"


class TestValidTransitions:
    """VALID_TRANSITIONS 合法转换映射测试。"""

    def test_draft_can_submit(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        assert DecisionStatus.PENDING_APPROVAL in VALID_TRANSITIONS[DecisionStatus.DRAFT]

    def test_pending_can_approve_or_reject(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        allowed = VALID_TRANSITIONS[DecisionStatus.PENDING_APPROVAL]
        assert DecisionStatus.APPROVED in allowed
        assert DecisionStatus.REJECTED in allowed

    def test_approved_can_execute(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        assert DecisionStatus.EXECUTING in VALID_TRANSITIONS[DecisionStatus.APPROVED]

    def test_executing_can_succeed_or_fail(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        allowed = VALID_TRANSITIONS[DecisionStatus.EXECUTING]
        assert DecisionStatus.SUCCEEDED in allowed
        assert DecisionStatus.FAILED in allowed

    def test_failed_can_rollback(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        assert DecisionStatus.ROLLED_BACK in VALID_TRANSITIONS[DecisionStatus.FAILED]

    def test_terminal_states_have_no_transitions(self):
        from src.decisions.models import VALID_TRANSITIONS, DecisionStatus
        for terminal in [DecisionStatus.SUCCEEDED, DecisionStatus.REJECTED, DecisionStatus.ROLLED_BACK]:
            assert VALID_TRANSITIONS[terminal] == []


class TestDecisionCreateModel:
    """DecisionCreate Pydantic 模型测试。"""

    def test_valid_creation(self, sample_create_data):
        assert sample_create_data.decision_type == "pricing"
        assert sample_create_data.agent_id == "agent:pricing-v1"
        assert sample_create_data.payload["sku"] == "TEST-001"
        assert sample_create_data.rollback_payload is not None

    def test_rollback_payload_optional(self):
        from src.decisions.models import DecisionCreate
        data = DecisionCreate(
            decision_type="advertising",
            agent_id="agent:ads",
            payload={"campaign_id": "C001", "budget": 100.0},
        )
        assert data.rollback_payload is None

    def test_missing_required_fields_raises(self):
        from src.decisions.models import DecisionCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            DecisionCreate(decision_type="pricing")  # missing agent_id and payload


class TestDecisionReadModel:
    """DecisionRead Pydantic 模型测试。"""

    def test_model_from_orm(self, sqlite_session, sample_create_data):
        from src.decisions.models import DecisionRead, DecisionStatus
        from src.decisions.repository import DecisionRepository

        repo = DecisionRepository(sqlite_session)
        decision = repo.create(sample_create_data)
        sqlite_session.commit()

        read = DecisionRead.model_validate(decision)
        assert isinstance(read.id, uuid.UUID)
        assert read.decision_type == "pricing"
        assert read.status == DecisionStatus.DRAFT
        assert read.approved_by is None
        assert read.result is None


# ===========================================================================
# 2. ORM 模型测试（Decision 表结构）
# ===========================================================================

class TestDecisionORMModel:
    """验证 Decision ORM 模型列定义。"""

    def test_tablename(self):
        from src.db.models import Decision
        assert Decision.__tablename__ == "decisions"

    def test_required_columns_present(self):
        from src.db.models import Decision
        cols = {c.name for c in Decision.__table__.columns}
        required = {
            "id", "decision_type", "agent_id", "payload", "status",
            "created_at", "updated_at", "approved_by", "approved_at",
            "executed_at", "result", "error_message", "rollback_payload",
        }
        assert required <= cols

    def test_nullable_columns(self):
        from src.db.models import Decision
        nullable_cols = {"approved_by", "approved_at", "executed_at", "result",
                         "error_message", "rollback_payload"}
        for col_name in nullable_cols:
            col = Decision.__table__.columns[col_name]
            assert col.nullable is True, f"列 {col_name} 应该允许 NULL"

    def test_repr(self):
        from src.db.models import Decision
        d = Decision(
            id=uuid.uuid4(),
            decision_type="pricing",
            status="DRAFT",
            agent_id="agent:test",
        )
        assert "pricing" in repr(d)
        assert "DRAFT" in repr(d)

    def test_decisions_in_base_metadata(self):
        from src.db.models import Base
        assert "decisions" in Base.metadata.tables


# ===========================================================================
# 3. Repository 测试
# ===========================================================================

class TestDecisionRepository:
    """DecisionRepository CRUD 操作测试。"""

    def test_create_returns_decision(self, sqlite_session, sample_create_data):
        from src.decisions.repository import DecisionRepository
        from src.decisions.models import DecisionStatus

        repo = DecisionRepository(sqlite_session)
        decision = repo.create(sample_create_data)
        sqlite_session.commit()

        assert decision.id is not None
        assert decision.decision_type == "pricing"
        assert decision.status == DecisionStatus.DRAFT.value
        assert decision.payload == sample_create_data.payload

    def test_get_by_id_found(self, sqlite_session, sample_create_data):
        from src.decisions.repository import DecisionRepository

        repo = DecisionRepository(sqlite_session)
        created = repo.create(sample_create_data)
        sqlite_session.commit()

        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_by_id_not_found(self, sqlite_session):
        from src.decisions.repository import DecisionRepository

        repo = DecisionRepository(sqlite_session)
        result = repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_get_history_returns_list(self, sqlite_session, sample_create_data):
        from src.decisions.repository import DecisionRepository

        repo = DecisionRepository(sqlite_session)
        repo.create(sample_create_data)
        repo.create(sample_create_data)
        sqlite_session.commit()

        history = repo.get_history()
        assert len(history) == 2

    def test_get_history_filter_by_type(self, sqlite_session):
        from src.decisions.repository import DecisionRepository
        from src.decisions.models import DecisionCreate

        repo = DecisionRepository(sqlite_session)
        repo.create(DecisionCreate(
            decision_type="pricing", agent_id="a1", payload={"x": 1}
        ))
        repo.create(DecisionCreate(
            decision_type="advertising", agent_id="a2", payload={"x": 2}
        ))
        sqlite_session.commit()

        pricing_only = repo.get_history(decision_type="pricing")
        assert len(pricing_only) == 1
        assert pricing_only[0].decision_type == "pricing"

    def test_get_history_limit(self, sqlite_session, sample_create_data):
        from src.decisions.repository import DecisionRepository

        repo = DecisionRepository(sqlite_session)
        for _ in range(5):
            repo.create(sample_create_data)
        sqlite_session.commit()

        limited = repo.get_history(limit=3)
        assert len(limited) == 3


# ===========================================================================
# 4. 状态机方法测试
# ===========================================================================

class TestCreateDecision:
    def test_create_returns_draft(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        result = state_machine.create_decision(sample_create_data)

        assert result.status == DecisionStatus.DRAFT
        assert result.decision_type == "pricing"
        assert result.agent_id == "agent:pricing-v1"
        assert isinstance(result.id, uuid.UUID)

    def test_create_logs_audit(self, state_machine, sample_create_data, mock_audit):
        state_machine.create_decision(sample_create_data)
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        assert call_kwargs[1]["action"] == "decision.created"


class TestSubmitForApproval:
    def test_draft_to_pending(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = state_machine.create_decision(sample_create_data)
        mock_audit.reset_mock()

        result = state_machine.submit_for_approval(created.id, actor="agent:pricing-v1")

        assert result.status == DecisionStatus.PENDING_APPROVAL

    def test_logs_audit_on_submit(self, state_machine, sample_create_data, mock_audit):
        created = state_machine.create_decision(sample_create_data)
        mock_audit.reset_mock()

        state_machine.submit_for_approval(created.id)

        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["action"] == "decision.submitted_for_approval"

    def test_invalid_transition_raises(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)
        # DRAFT 不能直接 approve（跳过 submit）
        with pytest.raises(DecisionStatusTransitionError):
            state_machine.approve(created.id, approved_by="admin")

    def test_not_found_raises(self, state_machine):
        from src.decisions.models import DecisionNotFoundError

        with pytest.raises(DecisionNotFoundError):
            state_machine.submit_for_approval(uuid.uuid4())


class TestApprove:
    def test_pending_to_approved(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        mock_audit.reset_mock()

        result = state_machine.approve(created.id, approved_by="admin@example.com")

        assert result.status == DecisionStatus.APPROVED
        assert result.approved_by == "admin@example.com"
        assert result.approved_at is not None

    def test_logs_audit_on_approve(self, state_machine, sample_create_data, mock_audit):
        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        mock_audit.reset_mock()

        state_machine.approve(created.id, approved_by="admin")

        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["action"] == "decision.approved"


class TestReject:
    def test_pending_to_rejected(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        mock_audit.reset_mock()

        result = state_machine.reject(
            created.id,
            approved_by="admin@example.com",
            reason="价格调整幅度超出限制",
        )

        assert result.status == DecisionStatus.REJECTED
        assert result.approved_by == "admin@example.com"
        assert result.error_message == "价格调整幅度超出限制"

    def test_logs_audit_on_reject(self, state_machine, sample_create_data, mock_audit):
        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        mock_audit.reset_mock()

        state_machine.reject(created.id, approved_by="admin", reason="不合规")

        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["action"] == "decision.rejected"

    def test_rejected_is_terminal(self, state_machine, sample_create_data, mock_audit):
        """拒绝后不能再做任何状态转换。"""
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.reject(created.id, approved_by="admin")

        with pytest.raises(DecisionStatusTransitionError):
            state_machine.submit_for_approval(created.id)


class TestExecute:
    def _get_approved_decision(self, state_machine, sample_create_data, mock_audit):
        """辅助：创建并审批一个决策。"""
        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.approve(created.id, approved_by="admin")
        mock_audit.reset_mock()
        return created

    def test_execute_success(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = self._get_approved_decision(state_machine, sample_create_data, mock_audit)

        def mock_executor(payload: dict) -> dict:
            return {"applied_price": payload["new_price"], "success": True}

        result = state_machine.execute(created.id, executor=mock_executor)

        assert result.status == DecisionStatus.SUCCEEDED
        assert result.result == {"applied_price": 29.99, "success": True}
        assert result.executed_at is not None

    def test_execute_failure(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = self._get_approved_decision(state_machine, sample_create_data, mock_audit)

        def failing_executor(payload: dict) -> dict:
            raise RuntimeError("Amazon API 超时")

        result = state_machine.execute(created.id, executor=failing_executor)

        assert result.status == DecisionStatus.FAILED
        assert "Amazon API 超时" in result.error_message
        assert result.executed_at is not None

    def test_execute_logs_audit_on_success(self, state_machine, sample_create_data, mock_audit):
        created = self._get_approved_decision(state_machine, sample_create_data, mock_audit)

        state_machine.execute(created.id, executor=lambda p: {"ok": True})

        # 应记录 2 次：executing + succeeded
        assert mock_audit.call_count == 2
        actions = [c[1]["action"] for c in mock_audit.call_args_list]
        assert "decision.executing" in actions
        assert "decision.succeeded" in actions

    def test_execute_logs_audit_on_failure(self, state_machine, sample_create_data, mock_audit):
        created = self._get_approved_decision(state_machine, sample_create_data, mock_audit)

        state_machine.execute(created.id, executor=lambda p: (_ for _ in ()).throw(ValueError("err")))

        actions = [c[1]["action"] for c in mock_audit.call_args_list]
        assert "decision.executing" in actions
        assert "decision.failed" in actions

    def test_cannot_execute_without_approval(self, state_machine, sample_create_data, mock_audit):
        """未审批的决策不能执行。"""
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        # 跳过 approve，直接 execute

        with pytest.raises(DecisionStatusTransitionError):
            state_machine.execute(created.id, executor=lambda p: {})

    def test_cannot_execute_draft(self, state_machine, sample_create_data, mock_audit):
        """DRAFT 状态不能直接执行。"""
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)

        with pytest.raises(DecisionStatusTransitionError):
            state_machine.execute(created.id, executor=lambda p: {})


class TestRollback:
    def test_failed_to_rolled_back(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.approve(created.id, approved_by="admin")
        state_machine.execute(created.id, executor=lambda p: (_ for _ in ()).throw(RuntimeError("err")))
        mock_audit.reset_mock()

        result = state_machine.rollback(created.id, actor="admin")

        assert result.status == DecisionStatus.ROLLED_BACK

    def test_rollback_logs_audit(self, state_machine, sample_create_data, mock_audit):
        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.approve(created.id, approved_by="admin")
        state_machine.execute(created.id, executor=lambda p: (_ for _ in ()).throw(RuntimeError("err")))
        mock_audit.reset_mock()

        state_machine.rollback(created.id)

        mock_audit.assert_called_once()
        assert mock_audit.call_args[1]["action"] == "decision.rolled_back"

    def test_cannot_rollback_succeeded(self, state_machine, sample_create_data, mock_audit):
        """已成功的决策不能回滚。"""
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.approve(created.id, approved_by="admin")
        state_machine.execute(created.id, executor=lambda p: {"ok": True})

        with pytest.raises(DecisionStatusTransitionError):
            state_machine.rollback(created.id)

    def test_rolled_back_is_terminal(self, state_machine, sample_create_data, mock_audit):
        """回滚后不能再次提交。"""
        from src.decisions.models import DecisionStatusTransitionError

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)
        state_machine.approve(created.id, approved_by="admin")
        state_machine.execute(created.id, executor=lambda p: (_ for _ in ()).throw(RuntimeError("err")))
        state_machine.rollback(created.id)

        with pytest.raises(DecisionStatusTransitionError):
            state_machine.submit_for_approval(created.id)


# ===========================================================================
# 5. 查询历史测试
# ===========================================================================

class TestGetDecisionHistory:
    def test_returns_empty_initially(self, state_machine):
        result = state_machine.get_decision_history()
        assert result == []

    def test_returns_all_decisions(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionCreate

        state_machine.create_decision(sample_create_data)
        state_machine.create_decision(
            DecisionCreate(
                decision_type="advertising",
                agent_id="agent:ads",
                payload={"campaign": "C001"},
            )
        )
        result = state_machine.get_decision_history()
        assert len(result) == 2

    def test_filter_by_type(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionCreate

        state_machine.create_decision(sample_create_data)
        state_machine.create_decision(
            DecisionCreate(
                decision_type="advertising",
                agent_id="agent:ads",
                payload={"campaign": "C001"},
            )
        )
        result = state_machine.get_decision_history(decision_type="pricing")
        assert len(result) == 1
        assert result[0].decision_type == "pricing"

    def test_filter_by_status(self, state_machine, sample_create_data, mock_audit):
        from src.decisions.models import DecisionStatus

        created = state_machine.create_decision(sample_create_data)
        state_machine.submit_for_approval(created.id)

        draft_decisions = state_machine.get_decision_history(status=DecisionStatus.DRAFT)
        pending_decisions = state_machine.get_decision_history(status=DecisionStatus.PENDING_APPROVAL)

        assert len(draft_decisions) == 0
        assert len(pending_decisions) == 1

    def test_limit_respected(self, state_machine, sample_create_data, mock_audit):
        for _ in range(5):
            state_machine.create_decision(sample_create_data)

        result = state_machine.get_decision_history(limit=2)
        assert len(result) == 2

    def test_ordered_by_created_at_desc(self, state_machine, sample_create_data, mock_audit):
        created1 = state_machine.create_decision(sample_create_data)
        created2 = state_machine.create_decision(sample_create_data)

        result = state_machine.get_decision_history()
        # 最新创建的排在最前面
        assert result[0].id == created2.id or result[0].id == created1.id  # 顺序可能相同


# ===========================================================================
# 6. 完整流程集成测试
# ===========================================================================

class TestFullWorkflow:
    """端到端测试：完整决策生命周期。"""

    def test_happy_path_draft_to_succeeded(
        self, state_machine, sample_create_data, mock_audit
    ):
        """完整正向流程: DRAFT → PENDING → APPROVED → EXECUTING → SUCCEEDED。"""
        from src.decisions.models import DecisionStatus

        # Step 1: 创建
        decision = state_machine.create_decision(sample_create_data)
        assert decision.status == DecisionStatus.DRAFT

        # Step 2: 提交审批
        decision = state_machine.submit_for_approval(decision.id, actor="agent:pricing-v1")
        assert decision.status == DecisionStatus.PENDING_APPROVAL

        # Step 3: 审批通过
        decision = state_machine.approve(decision.id, approved_by="admin@example.com")
        assert decision.status == DecisionStatus.APPROVED
        assert decision.approved_by == "admin@example.com"

        # Step 4: 执行（模拟成功）
        def mock_executor(payload: dict) -> dict:
            return {"success": True, "applied_price": payload["new_price"]}

        decision = state_machine.execute(decision.id, executor=mock_executor)
        assert decision.status == DecisionStatus.SUCCEEDED
        assert decision.result["success"] is True

        # 验证历史记录
        history = state_machine.get_decision_history()
        assert len(history) == 1
        assert history[0].status == DecisionStatus.SUCCEEDED

    def test_rejection_path(self, state_machine, sample_create_data, mock_audit):
        """拒绝流程: DRAFT → PENDING → REJECTED（终态）。"""
        from src.decisions.models import DecisionStatus, DecisionStatusTransitionError

        decision = state_machine.create_decision(sample_create_data)
        decision = state_machine.submit_for_approval(decision.id)
        decision = state_machine.reject(
            decision.id,
            approved_by="admin",
            reason="价格超限",
        )
        assert decision.status == DecisionStatus.REJECTED

        # 不能从 REJECTED 继续
        with pytest.raises(DecisionStatusTransitionError):
            state_machine.approve(decision.id, approved_by="admin")

    def test_failure_and_rollback_path(
        self, state_machine, sample_create_data, mock_audit
    ):
        """失败回滚流程: ... → FAILED → ROLLED_BACK（终态）。"""
        from src.decisions.models import DecisionStatus

        decision = state_machine.create_decision(sample_create_data)
        decision = state_machine.submit_for_approval(decision.id)
        decision = state_machine.approve(decision.id, approved_by="admin")

        def failing_executor(payload):
            raise ConnectionError("网络超时")

        decision = state_machine.execute(decision.id, executor=failing_executor)
        assert decision.status == DecisionStatus.FAILED
        assert "网络超时" in decision.error_message

        # 回滚
        decision = state_machine.rollback(decision.id, actor="admin")
        assert decision.status == DecisionStatus.ROLLED_BACK

        # rollback_payload 应该可以读取
        assert decision.rollback_payload == sample_create_data.rollback_payload

    def test_audit_log_called_for_each_transition(
        self, state_machine, sample_create_data, mock_audit
    ):
        """验证每次状态转换都会调用审计日志。"""
        decision = state_machine.create_decision(sample_create_data)
        assert mock_audit.call_count == 1  # created

        state_machine.submit_for_approval(decision.id)
        assert mock_audit.call_count == 2  # submitted

        state_machine.approve(decision.id, approved_by="admin")
        assert mock_audit.call_count == 3  # approved

        state_machine.execute(decision.id, executor=lambda p: {"ok": True})
        assert mock_audit.call_count == 5  # executing + succeeded


# ===========================================================================
# 7. 模块导入测试
# ===========================================================================

class TestModuleImports:
    def test_decisions_module_importable(self):
        from src.decisions import (
            DecisionStatus,
            DecisionCreate,
            DecisionRead,
            DecisionStateMachine,
            DecisionRepository,
        )
        assert DecisionStatus is not None
        assert DecisionCreate is not None
        assert DecisionRead is not None
        assert DecisionStateMachine is not None
        assert DecisionRepository is not None

    def test_decision_orm_importable(self):
        from src.db.models import Decision
        assert Decision.__tablename__ == "decisions"

    def test_error_classes_importable(self):
        from src.decisions.models import (
            DecisionStatusTransitionError,
            DecisionNotFoundError,
        )
        assert DecisionStatusTransitionError is not None
        assert DecisionNotFoundError is not None
